# Relatório de Revisão e Resumo Geral da Implementação
## Plataforma de Hospedagem (Airbnb Clone) — ERS v1.2 (IEEE 830)
**Disciplina:** Engenharia de Requisitos (INF1377) — Rodada 2  
**Escopo:** Fluxo de Reserva, Pagamento e Confirmação em 3 Telas (Seção 3.1)

---

## 1. Visão Geral e Conformidade com a ERS v1.2

A implementação desenvolvida cobre o ciclo ponta a ponta do fluxo de contratação de uma estadia na plataforma, iniciando no momento em que o hóspede (já autenticado) escolhe uma acomodação, suas datas e o número de hóspedes, e concluindo na emissão do comprovante na tela de confirmação.

O sistema atende rigorosamente a todas as restrições da especificação:
- **Exatamente três telas web:** (1) Resumo da Estadia, (2) Pagamento e (3) Confirmação, sem telas intermediárias (Seção 3.1).
- **Stack obrigatória:** Python 3 + Flask, SQLite automático via script (`init_db`), HTML5 semântico, CSS3 e JavaScript puro sem frameworks.
- **Portabilidade:** Execução local através de `pip install -r requirements.txt` e `python app.py`.

---

## 2. Estrutura de Arquivos e Componentes

```
rodada2/
├── app.py                      # Servidor Flask, rotas web das 3 telas, endpoints REST e webhooks
├── database.py                 # Conexão SQLite, schema do Apêndice B.4 e carga de dados de teste (seed)
├── models.py                   # Regras de negócio, cálculos de taxas, validações e auditoria
├── services/
│   ├── payment_gateway.py      # Gateway simulado (Cartão síncrono e PIX assíncrono com txid único)
│   └── email_service.py        # Serviço de e-mail simulado com log e consulta de envios
├── templates/
│   ├── base.html               # Layout base acessível (WCAG 2.1 AA) com botão de ajuda e seletor de usuário
│   ├── resumo.html             # Tela 1: Resumo da estadia e discriminação financeira
│   ├── pagamento.html          # Tela 2: Pagamento (Cartão e PIX) com timer de 30 min (RN-04)
│   └── confirmacao.html        # Tela 3: Comprovante de confirmação com endereço completo liberado
├── static/
│   ├── css/style.css           # Estilos responsivos (360px a 1920px - RNF-16) e acessíveis (RNF-14)
│   └── js/
│       ├── resumo.js           # Validação interativa de datas e cálculo em tempo real
│       └── pagamento.js        # Timer de 30 min, polling de webhook do PIX e tratamento de erros
├── tests/
│   └── test_fluxo_reserva.py   # 15 testes automatizados pytest com 100% de sucesso
├── requirements.txt            # Dependências (Flask, pytest)
├── README.md                   # Documentação detalhada e guia de teste de cenários
└── RESUMO_GERAL.md             # Este documento de revisão executiva
```

---

## 3. Revisão do Fluxo em 3 Telas

### Tela 1: Resumo da Estadia (`/resumo`) — Caso de Uso UC10
- **Entrada:** Hóspede seleciona a acomodação, período e número de hóspedes.
- **Segurança Física (RNF-05\*):** Exibição estritamente restrita a **bairro, cidade e estado**. Os campos `rua`, `numero` e `cep` são ocultados no back-end.
- **Identificação de Superhost:** Apresenta o selo Superhost quando o anfitrião possui o status (**RN-07**).
- **Validações de Regras de Negócio:**
  - **RN-01:** Check-out obrigatoriamente posterior ao check-in por pelo menos 1 noite.
  - **RN-02:** Quantidade de hóspedes \(\le\) `capacidadeMaxima` da acomodação.
  - **RF-19:** Impedimento de reservas com datas sobrepostas a reservas ativas (`CONFIRMADA` ou `PENDENTE`).
- **Discriminação Financeira Transparente:**
  - Subtotal das diárias: \(\text{noites} \times \text{precoNoite}\).
  - Taxa de serviço base de 14% (**RN-03**).
  - Desconto de 10% sobre a taxa de serviço caso o anfitrião seja Superhost, gerando taxa efetiva de 12,6% (**RN-07** e **RF-18**).
  - Valor total calculado.
- **Ação:** Botão *"Confirmar e ir para pagamento"* cria a reserva com status `PENDENTE` no SQLite e redireciona para a Tela 2.

### Tela 2: Pagamento (`/pagamento/<reserva_id>`) — Caso de Uso UC16
- **Controle de Expiração (RN-04):** Temporizador regressivo visual de **30 minutos** a partir da criação da reserva. Caso o tempo se esgote sem pagamento aprovado, o status transita para `CANCELADA` e os formulários são desativados.
- **Métodos de Pagamento Suportados (RF-23):**
  1. **Cartão de Crédito (Síncrono):**
     - O hóspede preenche dados do cartão.
     - **Segurança da Informação (RNF-08):** O servidor **nunca armazena número completo nem CVV** no banco de dados; apenas o token retornado pelo gateway (`tok_...`) e o código de autorização (`AUTH-...`).
     - **Aprovação:** A reserva transita automaticamente para `CONFIRMADA` (**RF-20 / TBD-03**), e-mails são disparados (**RF-28**) e a página redireciona para a Tela 3.
     - **Recusa (RF-26):** O sistema exibe mensagem amigável de erro, registra a tentativa como `RECUSADO` e permite nova tentativa imediata com outro cartão ou PIX sem perder a reserva.
  2. **PIX (Assíncrono):**
     - Gera cobrança com identificador único `txid` vinculado à reserva.
     - Exibe QR Code vetorial (SVG) e código Copia e Cola válidos por 30 minutos.
     - O front-end realiza polling a cada 3 segundos em `/api/reservas/<id>/status`.
     - Inclui botão de teste *"⚡ Simular Confirmação do Banco (Webhook)"* que aciona `/api/webhook/pix`, confirmando a reserva e redirecionando para a Tela 3.

### Tela 3: Confirmação e Comprovante (`/confirmacao/<reserva_id>`)
- **Acesso Condicional:** Bloqueada caso a reserva não esteja com status `CONFIRMADA`.
- **Revelação do Endereço Completo (RNF-05\*):** Com o pagamento aprovado, o sistema libera os dados completos do imóvel: Logradouro, Número, Bairro, Cidade, Estado e CEP.
- **Dados do Comprovante (RF-24):** Código da reserva, datas, número de hóspedes, contato do anfitrião (e-mail e telefone), método de pagamento, `txid`, código de autorização e discriminativo financeiro.
- **Notificação:** Confirmação de envio do comprovante ao e-mail do hóspede (**RF-28**).
- **Ações:** Botão para imprimir comprovante (`window.print()`) e botão para iniciar nova reserva.

---

## 4. Tabela de Rastreabilidade de Requisitos

| ID | Descrição | Onde foi Implementado | Evidência de Teste |
|---|---|---|---|
| **RF-17** | Criar reserva com check-in, check-out e número de hóspedes. | `app.py` (`view_resumo`), `models.py` (`criar_reserva`) | Teste automatizado `test_rf20_rf23_rf24_rf25_pagamento_cartao_aprovado` |
| **RF-18** | Cálculo do valor total: noites &times; diárias + taxa (com desconto superhost). | `models.py` (`calcular_valores_estadia`), `resumo.js` | Teste `test_rn03_rn07_rf18_calculo_taxa_servico_e_superhost` |
| **RF-19** | Impedir reservas sobrepostas para a mesma acomodação. | `models.py` (`validar_disponibilidade_e_regras`) | Teste `test_rf19_impedir_reservas_sobrepostas` |
| **RF-20** | Mudança automática de PENDENTE para CONFIRMADA após aprovação. | `models.py` (`confirmar_reserva_apos_pagamento`) | Teste `test_rf20_rf23_rf24_rf25_pagamento_cartao_aprovado` |
| **RF-23** | Aceitar cartão de crédito (síncrono) e PIX (assíncrono com txid). | `payment_gateway.py`, `app.py` | Testes de Cartão e PIX aprovados |
| **RF-24** | Registrar valor, código de autorização, txid e data/hora. | `database.py` (tabela `pagamento`), `models.py` | Testes `test_rf20_...` e `test_rf23_...` |
| **RF-25** | Controlar status: PROCESSANDO, APROVADO, RECUSADO. | `models.py` (`registrar_tentativa_pagamento`) | Testes `test_rf26_...` e `test_rf23_...` |
| **RF-26** | Permitir nova tentativa de pagamento quando anterior for recusado. | `app.py` (`api_pagar_cartao`), `pagamento.js` | Teste `test_rf26_pagamento_cartao_recusado_permite_nova_tentativa` |
| **RF-28** | Emitir comprovante de pagamento ao hóspede por e-mail. | `email_service.py` (`send_reservation_confirmed`) | Teste `test_rf20_rf23_rf24_rf25_pagamento_cartao_aprovado` |
| **RN-01** | Check-out posterior ao check-in com mínimo de 1 noite. | `models.py` (`calcular_valores_estadia`) | Teste `test_rn01_checkout_posterior_checkin_minimo_uma_noite` |
| **RN-02** | Número de hóspedes \(\le\) capacidade máxima. | `models.py` (`validar_disponibilidade_e_regras`) | Teste `test_rn02_capacidade_maxima` |
| **RN-03** | Taxa de serviço de 14% sobre as diárias. | `models.py` (`calcular_valores_estadia`) | Teste `test_rn03_rn07_rf18_calculo_taxa_servico_e_superhost` |
| **RN-04** | Reserva PENDENTE cancelada após 30 min sem aprovação. | `models.py` (`expirar_reservas_pendentes`), `pagamento.js` | Teste `test_rn04_expiracao_30_minutos_reserva_pendente` |
| **RN-07** | Superhost: 10% de desconto sobre a taxa (taxa efetiva 12,6%). | `models.py` (`calcular_valores_estadia`) | Teste `test_rn03_rn07_rf18_calculo_taxa_servico_e_superhost` |
| **RNF-05\*** | Endereço exato oculto até CONFIRMADA (mostra apenas bairro). | `models.py` (`obter_reserva_completa`), `confirmacao.html` | Teste `test_rnf05_seguranca_fisica_endereco_apenas_apos_confirmacao` |
| **RNF-08** | Não armazenar número completo nem CVV de cartões. | `database.py`, `payment_gateway.py` | Teste `test_rnf08_seguranca_informacao_nao_armazena_numero_completo_nem_cvv` |
| **RNF-11** | Apenas hóspede dono pode acessar os dados da reserva. | `app.py` (`login_required`, checagem de `hospede_id`) | Teste `test_rnf11_e_login_requerido` |
| **RNF-14** | Acessibilidade WCAG 2.1 nível AA e botão de ajuda. | `base.html`, `style.css` | Navegação por teclado, contraste e modal de ajuda |
| **RNF-16** | Portabilidade web de 360 px a 1920 px de largura. | `style.css` (media queries e layout flexível) | Teste de responsividade via navegador/DevTools |
| **RNF-22** | Auditoria de mudanças de status com data/hora e responsável. | `database.py` (`historico_status_*`), `models.py` | Teste `test_rn04_expiracao_30_minutos_reserva_pendente` |
| **UC10** | Solicitar reserva. | `resumo.html`, `app.py` | Fluxo da Tela 1 |
| **UC16** | Efetuar pagamento da reserva. | `pagamento.html`, `app.py` | Fluxo da Tela 2 |
| **Seção 3.1** | Fluxo de reserva em no máximo 3 telas. | `templates/` (resumo, pagamento, confirmacao) | Navegação direta entre as 3 telas |

---

## 5. Ambiguidades da ERS v1.2 e Decisões Adotadas

1. **Momento da Persistência da Reserva `PENDENTE`:**  
   *Decisão:* Criada no clique de confirmação do resumo para evitar lixo no banco e bloqueio de calendário (**RN-04**) por simples navegação casual.
2. **Arredondamento do Benefício Superhost (RN-07):**  
   *Decisão:* Cálculo em duas etapas discriminadas: `taxa = round(diarias * 0.14, 2)` e `desconto = round(taxa * 0.10, 2)`, exibindo ambas ao usuário com taxa efetiva de 12,6%.
3. **Mecanismo de Expiração de 30 Minutos (RN-04):**  
   *Decisão:* Verificação ativa sob demanda (*lazy cancellation*) em consultas, pagamentos e polling, além de timer visual no front-end, garantindo portabilidade em qualquer ambiente sem necessidade de configurar cron jobs no SO.
4. **Proteção do Endereço (RNF-05\*):**  
   *Decisão:* Filtragem estrita no back-end (campos `rua`, `numero` e `cep` são omitidos das respostas até que o status seja `CONFIRMADA`).
5. **Múltiplas Tentativas de Pagamento após Recusa (RF-26):**  
   *Decisão:* A reserva permanece `PENDENTE` durante os 30 minutos; cada tentativa gera um novo registro na tabela `pagamento` com seu próprio `txid`, preservando o histórico de recusas para auditoria.

---

## 6. Resultados dos Testes Automatizados (pytest)

Comando executado:
```bash
pytest tests/test_fluxo_reserva.py -v
```

Resultado obtido:
```
tests/test_fluxo_reserva.py::test_rn01_checkout_posterior_checkin_minimo_uma_noite PASSED [  6%]
tests/test_fluxo_reserva.py::test_rn02_capacidade_maxima PASSED                         [ 13%]
tests/test_fluxo_reserva.py::test_rn03_rn07_rf18_calculo_taxa_servico_e_superhost PASSED [ 20%]
tests/test_fluxo_reserva.py::test_rf19_impedir_reservas_sobrepostas PASSED                [ 26%]
tests/test_fluxo_reserva.py::test_validar_acomodacao_inativa PASSED                     [ 33%]
tests/test_fluxo_reserva.py::test_rn04_expiracao_30_minutos_reserva_pendente PASSED     [ 40%]
tests/test_fluxo_reserva.py::test_rf20_rf23_rf24_rf25_pagamento_cartao_aprovado PASSED [ 46%]
tests/test_fluxo_reserva.py::test_rf26_pagamento_cartao_recusado_permite_nova_tentativa PASSED [ 53%]
tests/test_fluxo_reserva.py::test_pagamento_cartao_erros_validacao_gateway PASSED       [ 60%]
tests/test_fluxo_reserva.py::test_rf23_rf24_pix_geracao_e_webhook_confirmacao PASSED    [ 66%]
tests/test_fluxo_reserva.py::test_webhook_pix_cenarios_de_erro PASSED                   [ 73%]
tests/test_fluxo_reserva.py::test_rnf05_seguranca_fisica_endereco_apenas_apos_confirmacao PASSED [ 80%]
tests/test_fluxo_reserva.py::test_rnf08_seguranca_informacao_nao_armazena_numero_completo_nem_cvv PASSED [ 86%]
tests/test_fluxo_reserva.py::test_rnf11_e_login_requerido PASSED                        [ 93%]
tests/test_fluxo_reserva.py::test_navegacao_telas_e_bloqueio_tela_confirmacao_reserva_pendente PASSED [100%]

============================= 15 passed in 17.38s =============================
```

---

## 7. Como Demonstrar a Aplicação

1. Execute:
   ```bash
   python app.py
   ```
2. Abra `http://127.0.0.1:5000` no navegador.
3. Alterne entre acomodações (Comum vs Superhost vs Datas Ocupadas) usando o seletor no topo da Tela 1.
4. Teste a aprovação do Cartão (final `4000`) e a recusa com nova tentativa (final `0002`).
5. Teste o PIX clicando no botão de simulação do webhook.
6. Verifique o desbloqueio do endereço exato na Tela 3.
