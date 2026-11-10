# Plataforma de Hospedagem (Airbnb Clone) — ERS v1.2 (IEEE 830)
## Implementação do Fluxo de Reserva, Pagamento e Confirmação (INF1377 - Engenharia de Requisitos)

Este projeto implementa o fluxo completo de **reserva, pagamento e confirmação** especificado na **Especificação de Requisitos de Software (ERS v1.2)**, estruturado em **no máximo três telas**, conforme estipulado na **Seção 3.1** do documento:
1. **Tela 1: Resumo da Estadia** (`/resumo`)
2. **Tela 2: Pagamento** (`/pagamento/<reserva_id>`)
3. **Tela 3: Confirmação e Comprovante** (`/confirmacao/<reserva_id>`)

---

## 1. Tecnologias Utilizadas

- **Back-end:** Python 3 + Flask.
- **Banco de Dados:** SQLite (`hospedagem.db`), criado e populado automaticamente na primeira execução com o schema do Apêndice B.4 e dados de teste.
- **Front-end:** HTML5 semântico, CSS3 responsivo (de 360 px a 1920 px — RNF-16, com contraste WCAG 2.1 nível AA — RNF-14) e JavaScript puro (vanilla JS, sem frameworks externos).
- **Testes Automatizados:** `pytest` com 100% de aprovação e cobertura completa das regras de negócio.

---

## 2. Como Rodar Localmente

### Pré-requisitos
- Python 3.10 ou superior instalado.

### Passo a Passo

1. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Executar a aplicação:**
   ```bash
   python app.py
   ```

3. **Acessar no navegador:**
   Abra [http://127.0.0.1:5000](http://127.0.0.1:5000) no seu navegador. O banco SQLite será criado e populado automaticamente na inicialização.

---

## 3. Como Executar os Testes Automatizados

O projeto conta com uma suíte de 15 testes automatizados com `pytest` cobrindo todas as regras de negócio do fluxo:

```bash
pytest tests/test_fluxo_reserva.py -v
```

Todos os testes validam isolamento em banco fresco, asserções de cálculos, recusas, webhooks assíncronos, proteção de endereço e regras de permissão.

---

## 4. Como Testar Cada Cenário (Caminho Feliz e Erros)

Na barra superior de todas as telas existe um **seletor de usuário de teste** e um **botão de ajuda** (Seção 3.1). Na Tela 1, há um **seletor rápido de acomodações** para alternar facilmente entre cenários.

### Cenário 1: Caminho Feliz com Cartão de Crédito (Síncrono)
1. Acesse [http://127.0.0.1:5000](http://127.0.0.1:5000). A Tela 1 abrirá com a acomodação `#1 - Apartamento Aconchegante Copacabana`.
2. Observe que o endereço exibe **apenas o bairro (Copacabana)** em respeito ao requisito **RNF-05\***.
3. Escolha as datas (ex: 3 noites) e 2 hóspedes. O discriminativo mostrará o subtotal, a taxa de 14% (**RN-03**) e o total.
4. Clique em **"Confirmar e ir para pagamento"**. A reserva será criada como `PENDENTE` no SQLite e você irá para a Tela 2.
5. Na Tela 2, veja o **temporizador regressivo de 30 minutos** (**RN-04**).
6. Na aba **Cartão de Crédito**, mantenha os dados preenchidos (cartão terminado em `4000`) e clique em **"Pagar no Cartão"**.
7. O pagamento será aprovado instantaneamente de forma síncrona (**RF-23, RF-24**), a reserva transitará para `CONFIRMADA` (**RF-20**) e a Tela 3 abrirá.
8. Na Tela 3 (Confirmação):
   - O **endereço completo é agora revelado** (**RNF-05\***): *Avenida Atlântica, 1500, apto 402 - CEP 22021-001*.
   - Exibe código de autorização, comprovante discriminado e dados de contato do anfitrião.
   - O comprovante foi disparado para o e-mail do hóspede (**RF-28**).

### Cenário 2: Caminho Feliz com PIX (Assíncrono via Webhook)
1. Na Tela 1, confirme uma reserva.
2. Na Tela 2, clique na aba **"💠 PIX Instantâneo"**.
3. O sistema gerará a cobrança no gateway simulado, exibindo o **QR Code SVG** e o código **Copia e Cola** com identificador único `txid` (**RF-23**). O pagamento ficará com status `PROCESSANDO` e o front-end iniciará o polling automático.
4. Para simular a aprovação bancária assíncrona, clique no botão:
   `⚡ Simular Confirmação do Banco (Webhook)`
5. O gateway acionará o endpoint `/api/webhook/pix`, validando o `txid` e o valor pago (**Seção 3.4 e 4.5.2**). A reserva será confirmada e a página redirecionará automaticamente para a Tela 3.

### Cenário 3: Desconto Superhost (RN-07 e RF-18)
1. Na Tela 1, use o seletor no topo e escolha `#2 - Loft Moderno em Ipanema (Superhost ⭐)`.
2. Observe o badge **★ SUPERHOST**.
3. O discriminativo de preços destacará a linha verde:
   `Desconto Superhost (10% sobre a taxa - RN-07)`.
4. Exemplo para 2 diárias de R$ 400,00 (Total de diárias: R$ 800,00):
   - Taxa base (14%): R$ 112,00.
   - Desconto Superhost (10% de R$ 112,00): - R$ 11,20.
   - Taxa final: R$ 100,80 (equivalente a 12,6% sobre o valor das diárias).
   - Valor Total: R$ 900,80.

### Cenário 4 (Erro): Recusa de Cartão de Crédito e Nova Tentativa (RF-26)
1. Na Tela 2, altere o número do cartão para um número terminado em `0002` (ou altere o nome do titular para `RECUSADO`).
2. Clique em **"Pagar no Cartão"**.
3. O gateway simulado retornará recusa ("saldo insuficiente ou bloqueio").
4. A tela exibirá o alerta em vermelho em linguagem simples, **mantendo a reserva com status PENDENTE** e permitindo tentar novamente.
5. Altere o cartão de volta para final `4000` e submeta: a transação será aprovada com sucesso. No banco de dados, o histórico registrará tanto a tentativa recusada quanto a aprovada.

### Cenário 5 (Erro): Datas Inválidas / Check-out Anterior ao Check-in (RN-01)
1. Na Tela 1, escolha um check-out igual ou anterior ao check-in.
2. A tela bloqueará o botão e exibirá: *"A data de check-out deve ser posterior ao check-in em pelo menos 1 noite (RN-01)"*.
3. O servidor também rejeita qualquer tentativa via POST com erro 400.

### Cenário 6 (Erro): Capacidade Máxima Excedida (RN-02)
1. Na Tela 1, selecione a acomodação `#2` (capacidade máxima: 2 pessoas).
2. Tente informar `3` ou mais hóspedes.
3. A interface alertará sobre a ultrapassagem da capacidade máxima permitida (**RN-02**).

### Cenário 7 (Erro): Conflito de Reservas Sobrepostas (RF-19)
1. No seletor de acomodações da Tela 1, escolha a acomodação `#3 - Chalé Rústico na Serra`.
2. Esta acomodação possui uma reserva pré-existente confirmada entre `D+20` e `D+25` (onde D é hoje).
3. Selecione qualquer período que colida com esse intervalo (ex: de hoje+21 até hoje+24).
4. Ao submeter, o sistema impedirá a reserva informando: *"A acomodação já está reservada ou possui solicitação em andamento no período selecionado (RF-19)"*.

### Cenário 8 (Erro): Expiração de 30 Minutos (RN-04)
1. Na Tela 2, o timer exibe o tempo restante a partir da criação da reserva.
2. Quando o tempo atinge `00:00`, a reserva é marcada como `CANCELADA` no SQLite com registro de auditoria (**RNF-22**), e os botões de pagamento são desativados.
3. Tentativas de submissão de pagamento para reservas com mais de 30 minutos são rejeitadas pelo back-end com mensagem apropriada.

---

## 5. Simulação de Sistemas Externos

Conforme orientações da tarefa, os serviços externos foram implementados em módulos desacoplados:

### Gateway de Pagamento (`services/payment_gateway.py`)
Possui a mesma assinatura que um gateway de produção (como Stripe, Pagar.me ou Asaas):
- `authorize_credit_card(card_holder, card_number, expiration, cvv, amount, reservation_id)`:
  - **Aprovação:** Qualquer cartão válido terminado diferente de `0002`. Retorna `status="APROVADO"`, `codigoAutorizacao="AUTH-..."` e token de segurança `tokenCartao="tok_..."`.
  - **Recusa (RF-26):** Cartão terminado em `0002` ou titular com texto `RECUSADO`. Retorna `status="RECUSADO"`.
  - **Erros de Validação:** Cartão vencido (validade no passado) ou CVV com tamanho incorreto.
  - **Conformidade RNF-08:** O sistema **nunca armazena o número completo nem o CVV do cartão**. Apenas o token do gateway e o código de autorização são gravados no banco SQLite.
- `create_pix_charge(amount, reservation_id)`:
  - Gera `txid` único vinculado à reserva (`PIX-<id>-<hash>`).
  - Gera payload do PIX Copia e Cola e QR Code vetorial em SVG.
- `simulate_pix_webhook(txid, amount)`:
  - Disparado pelo botão da interface ou por POST em `/api/webhook/pix` simulando o aviso de liquidação do Banco Central / Gateway.

### Serviço de E-mail (`services/email_service.py`)
- `send_reservation_confirmed(...)`:
  - Envia e-mail ao hóspede contendo o comprovante detalhado (**RF-28**), regras da casa e o endereço completo desbloqueado (**RNF-05\***).
  - Envia notificação ao anfitrião sobre a nova reserva.
- Para inspecionar os e-mails enviados em tempo real durante testes manuais, acesse a rota:
  [http://127.0.0.1:5000/api/dev/emails](http://127.0.0.1:5000/api/dev/emails).

---

## 6. Tabela de Rastreabilidade

Abaixo está o mapeamento detalhado de todos os requisitos, regras de negócio e passos de casos de uso da ERS v1.2 considerados para o fluxo:

| ID | Tipo | Descrição Resumida | Onde foi Implementado | Como Testar |
|---|---|---|---|---|
| **RF-17** | Requisito Funcional | Criar reserva informando check-in, check-out e número de hóspedes. | `app.py` (`view_resumo`), `models.py` (`criar_reserva`), `templates/resumo.html` | Preencher datas e hóspedes na Tela 1 e clicar em confirmar; teste `test_rf20_rf23_rf24_rf25_pagamento_cartao_aprovado`. |
| **RF-18** | Requisito Funcional | Cálculo do valor total: noites &times; diária + taxa de serviço, com desconto Superhost. | `models.py` (`calcular_valores_estadia`), `static/js/resumo.js` | Testes automatizados `test_rn03_rn07_rf18_calculo_taxa_servico_e_superhost` e discriminação dinâmica na Tela 1. |
| **RF-19** | Requisito Funcional | Impedir reservas sobrepostas para a mesma acomodação. | `models.py` (`validar_disponibilidade_e_regras`) | Teste `test_rf19_impedir_reservas_sobrepostas` ou selecionar a Acomodação 3 com datas ocupadas na Tela 1. |
| **RF-20** | Requisito Funcional | Controle de status: PENDENTE para CONFIRMADA automaticamente após aprovação de pagamento sem anfitrião (TBD-03). | `models.py` (`confirmar_reserva_apos_pagamento`), `app.py` (`api_pagar_cartao`, `api_webhook_pix`) | Teste `test_rf20_rf23_rf24_rf25_pagamento_cartao_aprovado` e pagamento na Tela 2. |
| **RF-23** | Requisito Funcional | Aceitar pagamento por cartão de crédito (síncrono) e PIX (assíncrono) com txid único. | `services/payment_gateway.py`, `app.py` (`api_pagar_cartao`, `api_gerar_pix`, `api_webhook_pix`) | Testes `test_rf20_rf23_rf24_rf25_pagamento_cartao_aprovado` e `test_rf23_rf24_pix_geracao_e_webhook_confirmacao`. |
| **RF-24** | Requisito Funcional | Registrar valor, código de autorização, txid e data/hora do pagamento. | `database.py` (tabela `pagamento`), `models.py` (`registrar_tentativa_pagamento`), `templates/confirmacao.html` | Inspecionar a tabela `pagamento` no SQLite ou visualizar o comprovante na Tela 3. |
| **RF-25** | Requisito Funcional | Controlar status do pagamento: PROCESSANDO, APROVADO, RECUSADO. | `models.py` (`registrar_tentativa_pagamento`, `atualizar_status_pagamento`) | Testes `test_rf26_pagamento_cartao_recusado_permite_nova_tentativa` e `test_rf23_rf24_pix_geracao_e_webhook_confirmacao`. |
| **RF-26** | Requisito Funcional | Permitir nova tentativa de pagamento quando anterior for recusado. | `app.py` (`api_pagar_cartao`), `static/js/pagamento.js` | Teste `test_rf26_pagamento_cartao_recusado_permite_nova_tentativa` ou usar cartão final `0002` na Tela 2. |
| **RF-28** | Requisito Funcional | Emitir comprovante de pagamento ao hóspede por e-mail. | `services/email_service.py` (`send_reservation_confirmed`), `app.py` | Teste `test_rf20_rf23_rf24_rf25_pagamento_cartao_aprovado` e conferir endpoint `/api/dev/emails`. |
| **RN-01** | Regra de Negócio | Check-out posterior ao check-in com estadia mínima de 1 noite. | `models.py` (`calcular_valores_estadia`, `validar_disponibilidade_e_regras`), `static/js/resumo.js` | Teste `test_rn01_checkout_posterior_checkin_minimo_uma_noite` e validação interativa na Tela 1. |
| **RN-02** | Regra de Negócio | Número de hóspedes não pode ultrapassar a capacidadeMaxima. | `models.py` (`validar_disponibilidade_e_regras`), `static/js/resumo.js` | Teste `test_rn02_capacidade_maxima` e validação na Tela 1. |
| **RN-03** | Regra de Negócio | Taxa de serviço da plataforma de 14% sobre as diárias. | `models.py` (`calcular_valores_estadia`), `static/js/resumo.js` | Teste `test_rn03_rn07_rf18_calculo_taxa_servico_e_superhost`. |
| **RN-04** | Regra de Negócio | Reserva PENDENTE cancelada automaticamente se não paga em 30 minutos. | `models.py` (`expirar_reservas_pendentes`), `static/js/pagamento.js` | Teste `test_rn04_expiracao_30_minutos_reserva_pendente` e timer visível na Tela 2. |
| **RN-07** | Regra de Negócio | Benefício Superhost: desconto de 10% sobre o valor da taxa de serviço (taxa efetiva 12,6%). | `models.py` (`calcular_valores_estadia`), `templates/resumo.html` | Teste `test_rn03_rn07_rf18_calculo_taxa_servico_e_superhost` e seleção da Acomodação 2 na Tela 1. |
| **RNF-05\*** | RNF (Safety) | Endereço exato só deve ser exibido após confirmação; antes mostra-se apenas bairro e cidade. | `models.py` (`obter_acomodacao_detalhe`, `obter_reserva_completa`), `templates/resumo.html`, `templates/confirmacao.html` | Teste `test_rnf05_seguranca_fisica_endereco_apenas_apos_confirmacao` (verifica que `rua/numero/cep` são omitidos na Tela 1 e liberados na Tela 3). |
| **RNF-08** | RNF (Segurança) | Não armazenar número completo nem CVV de cartões; apenas o token retornado pelo gateway. | `database.py` (schema), `services/payment_gateway.py`, `models.py` | Teste `test_rnf08_seguranca_informacao_nao_armazena_numero_completo_nem_cvv`. |
| **RNF-11** | RNF (Autorização) | Apenas hóspede dono pode acessar os dados de sua reserva. | `app.py` (`view_pagamento`, `view_confirmacao`, `api_pagar_cartao`) | Teste `test_rnf11_e_login_requerido` e troca de usuário no seletor do cabeçalho. |
| **RNF-14** | RNF (Acessibilidade)| Atendimento a WCAG 2.1 nível AA, contraste visual, ARIA roles, tags semânticas e botão de ajuda. | `templates/base.html`, `static/css/style.css` | Navegação por teclado, leitor de tela e verificação do modal de ajuda em todas as telas. |
| **RNF-16** | RNF (Portabilidade) | Interface funcional em telas de 360 px a 1920 px de largura. | `static/css/style.css` (`@media (min-width: 840px)`, viewport meta tag) | Redimensionamento da janela do navegador ou simulação mobile nos DevTools. |
| **RNF-22** | RNF (Auditoria) | Toda mudança de status de reserva e pagamento registrada com data, hora e responsável. | `database.py` (`historico_status_reserva`, `historico_status_pagamento`), `models.py` | Teste `test_rn04_expiracao_30_minutos_reserva_pendente` e inspeção das tabelas de histórico no SQLite. |
| **UC10** | Caso de Uso | Solicitar reserva (passos 1 a 5: escolha, verificação, cálculo e confirmação). | `app.py` (`view_resumo`), `templates/resumo.html` | Fluxo completo da Tela 1. |
| **UC16** | Caso de Uso | Efetuar pagamento da reserva (cartão síncrono e PIX assíncrono). | `app.py` (`view_pagamento`), `templates/pagamento.html` | Fluxo completo da Tela 2. |
| **Seção 3.1** | Interface | Fluxo de reserva em no máximo três telas: resumo da estadia, pagamento e confirmação. | `templates/resumo.html`, `templates/pagamento.html`, `templates/confirmacao.html` | Navegação das 3 telas consecutivas sem telas intermediárias. |

---

### Requisitos da ERS Fora do Escopo Desta Entrega
Conforme explicitamente autorizado na especificação da tarefa (*"Funcionalidades fora do fluxo (cadastro, busca, avaliação, denúncias, cancelamento pelo usuário) não precisam ser implementadas"*):
- **RF-01 a RF-06 / UC01 a UC04:** Cadastro, recuperação de senha e edição de perfil (o fluxo inicia com o hóspede já autenticado; a regra de login é verificada no servidor via sessão).
- **RF-07 a RF-11 / UC05 a UC07:** Cadastro e edição de anúncios por anfitriões (os dados já são criados e disponibilizados via seed no SQLite).
- **RF-12 a RF-16 / UC08:** Mecanismo de busca geográfica com autocomplete e filtros amplos (o fluxo se inicia na escolha da acomodação pelo hóspede).
- **RF-21, RF-27 / UC12:** Cancelamento manual e política de reembolso a pedido do usuário (embora o cancelamento automático por expiração da RN-04 esteja implementado).
- **RF-29 a RF-33 / UC18, UC19, UC20:** Sistema de avaliações pós-estadia e concessão dinâmica de selo superhost (o selo superhost já consta no modelo e no cálculo do benefício da RN-07).
- **RF-34 a RF-36 / UC21, UC22:** Moderação e denúncias.

---

## 7. Lista de Ambiguidades e Decisões

Durante a análise integral da ERS v1.2, foram encontradas 5 ambiguidades. Segue o registro formal de cada uma, com a interpretação adotada e a alternativa descartada:

### Amb-01: Momento Exato da Persistência da Reserva com Status PENDENTE
- **Trecho da ERS:** UC10 passo 2 ("hóspede seleciona 'Reservar' -> sistema calcula valorTotal e cria a reserva com status PENDENTE") versus passo 5 ("hóspede confirma e segue para o pagamento UC16").
- **Ambiguidade:** A reserva `PENDENTE` deve ser salva no banco já ao carregar a página de resumo ou apenas quando o usuário confirma e avança para pagar?
- **Interpretação Adotada:** Na Tela 1 (Resumo), o sistema apenas simula e exibe os cálculos e verifica a disponibilidade. A criação do registro no banco SQLite com status `PENDENTE` ocorre quando o usuário submete o formulário ("Confirmar e ir para pagamento"), dando início à contagem dos 30 minutos da RN-04.
- **Alternativa Descartada:** Gravar a reserva no banco na primeira visualização do resumo. Descartada porque qualquer consulta casual de visitante bloquearia o calendário da acomodação por 30 minutos para outros hóspedes.

### Amb-02: Arredondamento e Base de Cálculo do Desconto de Superhost
- **Trecho da ERS:** RN-07: *"Como benefício, as reservas das acomodações de um superhost têm desconto de 10% sobre o valor da taxa de serviço. Com a taxa de 14% (RN-03), a taxa efetiva fica em 12,6% do valor das diárias."*
- **Ambiguidade:** Deve-se calcular primeiro a taxa de 14%, arredondar e deduzir 10%, ou aplicar 12,6% diretamente sobre as diárias?
- **Interpretação Adotada:** Calcular `taxa_base = round(diarias * 0.14, 2)`, calcular o desconto `desconto = round(taxa_base * 0.10, 2)` e subtrair `taxa_final = taxa_base - desconto`. Isso permite discriminar com transparência para o hóspede a taxa e o desconto concedido, batendo com a taxa efetiva de 12,6%.
- **Alternativa Descartada:** Multiplicar diretamente por `0.126` em uma linha só sem discriminar a taxa de serviço cheia e o desconto de superhost ao usuário.

### Amb-03: Mecanismo de Cancelamento por Timeout de 30 Minutos (RN-04)
- **Trecho da ERS:** RN-04: *"Uma reserva PENDENTE é cancelada automaticamente se o pagamento não for aprovado em 30 minutos."*
- **Ambiguidade:** A ERS não define se o cancelamento exige um processo em background do SO (daemon/cron) ou verificação sob demanda (*lazy cancellation*).
- **Interpretação Adotada:** Implementou-se avaliação ativa sob demanda no servidor (`models.expirar_reservas_pendentes()`) sempre que uma reserva ou conflito de datas é consultado, antes de processar qualquer pagamento e no polling de status, além de um timer em JavaScript no front-end da Tela 2. Ao estourar 30 minutos, a reserva transita para `CANCELADA` no SQLite com registro em `historico_status_reserva`.
- **Alternativa Descartada:** Depender de cron jobs externos do sistema operacional, o que impediria a aplicação de ser 100% portável e executada simplesmente com `python app.py`.

### Amb-04: Ocultação do Endereço Exato Antes da Confirmação (RNF-05\*)
- **Trecho da ERS:** RNF-05\*: *"O endereço exato da acomodação só deve ser exibido ao hóspede após a reserva ser CONFIRMADA; antes disso, mostra-se apenas o bairro."*
- **Ambiguidade:** A especificação menciona apenas "bairro", mas a busca e resumo necessitam da cidade e estado para fazer sentido geográfico. Além disso, se os dados fossem enviados ao front-end e ocultados via CSS/JS, haveria vazamento de dados confidenciais.
- **Interpretação Adotada:** As funções `models.obter_acomodacao_detalhe` e `models.obter_reserva_completa` eliminam no back-end os campos `rua`, `numero` e `cep` sempre que a reserva não estiver `CONFIRMADA`. Apenas `bairro`, `cidade` e `estado` são trafegados. Na Tela 3 (Confirmação), o endereço completo é entregue.
- **Alternativa Descartada:** Enviar todos os dados no payload HTML/JSON e ocultar campos com CSS (`display: none`), o que violaria o princípio de segurança física e segurança da informação.

### Amb-05: Múltiplas Tentativas de Pagamento após Recusa (RF-26 e Seção 4.5.1)
- **Trecho da ERS:** RF-26: *"O sistema deve permitir nova tentativa de pagamento quando o anterior for recusado."* e Seção 4.5.1: *"Uma reserva pode ter um ou mais pagamentos (relação Reserva 1 -> 1..* Pagamento)"*.
- **Ambiguidade:** Um pagamento recusado invalida a reserva imediatamente ou a reserva continua PENDENTE até o fim dos 30 minutos?
- **Interpretação Adotada:** A reserva permanece `PENDENTE` durante a janela dos 30 minutos. Cada tentativa de pagamento (seja no cartão ou PIX) cria uma nova linha na tabela `pagamento` com seu próprio `txid`, preservando as tentativas anteriores com status `RECUSADO` e registrando o histórico de auditoria (**RNF-22**). O hóspede pode trocar de cartão ou migrar para o PIX sem perder a reserva.
- **Alternativa Descartada:** Sobrescrever o registro de pagamento ou cancelar a reserva imediatamente no primeiro cartão recusado.
