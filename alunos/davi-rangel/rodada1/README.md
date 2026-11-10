# Documentação Técnica e Código-Fonte: Fluxo de Reserva, Pagamento e Confirmação
**Referência:** Especificação de Requisitos de Software (ERS v1.1 / v1.2 — Padrão IEEE 830)  
**Stack Tecnológica:** Python 3 + Flask, SQLite, HTML5 / CSS3 / JavaScript Vanilla, Pytest.

---

## 1. Visão Geral da Arquitetura

O sistema atende integralmente ao fluxo de 3 telas estipulado na **Seção 3.1** da ERS:
- **Tela 1 — Resumo da Estadia (`/reservas/resumo`)**: Cálculo discriminado das diárias, aplicação da taxa de serviço de 14% (RN-03), verificação dinâmica de elegibilidade do Superhost para abatimento de 10% sobre a taxa (RN-07 / RF-18), e validações de negócio (RN-01, RN-02, RF-19). Em observância a **RNF-05**, apenas bairro, cidade e estado são informados.
- **Tela 2 — Pagamento (`/reservas/<id>/pagamento`)**: Apresenta suporte síncrono para Cartão de Crédito e suporte assíncrono para PIX via webhook (RF-23). Controla o tempo de expiração de 30 minutos (RN-04) e não armazena dados sensíveis de pagamento (RNF-08). Permite nova tentativa em caso de recusa (RF-26).
- **Tela 3 — Confirmação (`/reservas/<id>/confirmacao`)**: Renderizada estritamente após a transição da reserva para `CONFIRMADA`. Revela os dados de autorização, comprovante de envio de e-mail (RF-28) e **o endereço completo da acomodação** (rua, número e CEP) em cumprimento a **RNF-05**.

---

## 2. Tabela de Rastreabilidade

| ID ERS | Tipo | Descrição Sumária | Onde foi Implementado | Como Testar / Validar |
| :--- | :--- | :--- | :--- | :--- |
| **RF-17** | Funcional | Criação de reserva com check-in, check-out e hóspedes | `app.py: criar_reserva()`, `templates/resumo.html` | Acessar a tela inicial, selecionar período e submeter formulário. |
| **RF-18** | Funcional | Cálculo de total: noites $\times$ preço + taxa 14% - desconto Superhost | `models.py: calcular_valores()` | Executar `pytest tests/test_fluxo.py -k test_rf18_rn07_desconto_superhost`. |
| **RF-19** | Funcional | Impedir reservas sobrepostas para o mesmo imóvel | `models.py: validar_disponibilidade()` | Executar `pytest tests/test_fluxo.py -k test_rf19_impedir_sobreposicao`. |
| **RF-20** | Funcional | Controle dos estados da reserva: `PENDENTE`, `CONFIRMADA`, `CANCELADA` | `database.py: reserva`, `app.py` | Conferir transições no banco ao pagar ou expirar reserva. |
| **RF-23** | Funcional | Pagamento via Cartão (síncrono) e PIX (assíncrono com txid único) | `services/payment_gateway.py`, `app.py: pagar_cartao, webhook_pix` | Executar `pytest tests/test_fluxo.py -k test_fluxo_pix_assincrono`. |
| **RF-24** | Funcional | Registro de valor, autorização, txid e data/hora | `database.py: tabela pagamento`, `app.py` | Checar registros gerados na tabela `pagamento`. |
| **RF-25** | Funcional | Controle de status do pagamento: `PROCESSANDO`, `APROVADO`, `RECUSADO` | `database.py: tabela pagamento` | Simular pagamento com cartão final `0000` (recusa) e final padrão (aprovação). |
| **RF-26** | Funcional | Permitir nova tentativa após recusa | `app.py: pagar_cartao()`, `templates/pagamento.html` | Executar `pytest tests/test_fluxo.py -k test_fluxo_cartao_recusa_e_aprovacao`. |
| **RF-28** | Funcional | Emissão de comprovante por e-mail | `services/email_service.py` | Conferir log do serviço `EmailServiceSimulado` após aprovação. |
| **RN-01** | Negócio | Check-out posterior ao check-in (mínimo 1 noite) | `models.py`, `app.py: tela_resumo` | Executar `pytest tests/test_fluxo.py -k test_rn01_estadia_minima`. |
| **RN-02** | Negócio | Hóspedes $\le$ capacidade máxima | `models.py`, `app.py: tela_resumo` | Executar `pytest tests/test_fluxo.py -k test_rn02_capacidade_maxima`. |
| **RN-03** | Negócio | Taxa de serviço de 14% sobre as diárias | `models.py: calcular_valores()` | Conferir discriminação detalhada na Tela 1. |
| **RN-04** | Negócio | Cancelamento automático após 30 min sem pagamento | `models.py: verificar_expiracao_reserva()` | Executar `pytest tests/test_fluxo.py -k test_rn04_expiracao_reserva_timeout`. |
| **RN-07 / RF-33** | Negócio / Funcional | Desconto de 10% sobre a taxa de serviço para anfitrião Superhost | `models.py: calcular_valores()` | Executar `pytest tests/test_fluxo.py -k test_rf18_rn07_desconto_superhost`. |
| **RNF-02** | Não Funcional | Confirmação de cartão exibida rapidamente (<10s) | `app.py: pagar_cartao()` | Processamento imediato em rota síncrona. |
| **RNF-05** | Não Funcional / Segurança | Endereço exato ocultado antes da confirmação | `templates/resumo.html`, `templates/confirmacao.html` | Executar `pytest tests/test_fluxo.py -k test_rnf05_ocultacao_endereco_antes_confirmacao`. |
| **RNF-08** | Não Funcional / Segurança | Não armazenar número completo e CVV do cartão | `database.py: pagamento` | Executar `pytest tests/test_fluxo.py -k test_rnf08_nao_armazenar_cartao_sensivel`. |
| **RNF-22** | Não Funcional | Auditoria de mudanças de status com data, hora e autor | `database.py: auditoria`, `models.py: registrar_auditoria()` | Executar `pytest tests/test_fluxo.py -k test_rnf22_auditoria_mudanca_status`. |

### Requisitos Fora do Escopo Implementado e Justificativa
- **RF-01 a RF-06 (Cadastro e Gestão de Usuários):** Não pertencem ao fluxo de contratação; supridos via autenticação mockada em sessão.
- **RF-07 a RF-11 (Cadastro e Gestão de Imóveis):** Supridos via script de inicialização (`seed_db`).
- **RF-12 a RF-16 (Busca com Filtros Avançados e Ordenação):** Simplificados para uma listagem direta que dispara o fluxo de 3 telas.
- **RF-21, RF-27 e RN-05 (Cancelamento e Reembolso pelo Usuário):** Conforme seção "Simplificações permitidas" do enunciado, operações pós-contratação não fazem parte deste fluxo.
- **RF-29 a RF-32 e RN-06 (Avaliações mútuas):** Ocorrem apenas após a conclusão física da viagem (`CONCLUIDA`), fora da contratação imediata.
- **RF-34 a RF-36 e RNF-06 (Denúncias e Moderação):** Funcionalidade administrativa independente.

---

## 3. Registro de Ambiguidades e Decisões de Projeto

### Decisão 1: Qualificação e Aplicação do Selo Superhost (RN-07 e RF-33)
- **Trecho da ERS:** *"O anfitrião recebe o selo superhost quando, nos últimos 12 meses, tem nota média de pelo menos 4,8, taxa de resposta de pelo menos 90% e ao menos 10 reservas concluídas. Como benefício, as reservas das acomodações de um superhost têm desconto de 10% na taxa de serviço."*
- **Ambiguidade:** A ERS não define se a verificação dos 3 parâmetros (taxa de resposta, média, histórico anual) deve ser recalculada em tempo de execução a cada reserva ou se decorre de uma flag consolidada na acomodação/anfitrião.
- **Decisão Adotada:** Criou-se a coluna booleana `ehSuperhost` na acomodação/anfitrião (populada no banco com base nas métricas consolidadas). No cálculo da reserva, se `ehSuperhost == 1`, aplica-se o desconto: $\text{desconto} = \text{taxaServico} \times 0.10$.
- **Alternativa Descartada:** Tentar montar um subsistema completo de mensageria para inferir taxa de resposta em tempo real, o que extrapola o escopo de 3 telas.

### Decisão 2: Ocultação do Endereço Físico (RNF-05)
- **Trecho da ERS:** *"O endereço exato da acomodação só deve ser exibido ao hóspede após a reserva ser CONFIRMADA; antes disso, mostra-se apenas o bairro."*
- **Ambiguidade:** A especificação não deixa explícito se a proteção deve ser estritamente no back-end (projeção no SQL) ou via camada de apresentação front-end.
- **Decisão Adotada:** A rota de resumo (`/reservas/resumo`) sequer envia os dados `rua` e `cep` no template. A rota de confirmação (`/reservas/<id>/confirmacao`) valida se `status == 'CONFIRMADA'` antes de projetar `rua`, `numero` e `cep`.
- **Alternativa Descartada:** Enviar os dados completos no HTML da Tela 1 ocultando-os via CSS/JavaScript, o que violaria o princípio de segurança e o RNF-05.

### Decisão 3: Cancelamento de Reserva Pendente por Timeout (RN-04)
- **Trecho da ERS:** *"Uma reserva PENDENTE é cancelada automaticamente se o pagamento não for aprovado em 30 minutos."*
- **Ambiguidade:** Como garantir o cancelamento em uma arquitetura Flask + SQLite básica sem introduzir daemons externos complexos (ex.: Celery, Redis ou cron)?
- **Decisão Adotada:** Implementada checagem preguiçosa ativa (`verificar_expiracao_reserva`): qualquer requisição referente à reserva (consulta de tela, tentativa de pagamento ou chamada de webhook) calcula o delta entre `criadoEm` e o horário atual. Se exceder 1800 segundos (30 minutos), a reserva é transacionada para `CANCELADA` e auditada.
- **Alternativa Descartada:** Adicionar dependências pesadas de fila e cache ao projeto.

### Decisão 4: Modelo de Aprovação de Reserva (TBD-03)
- **Trecho da ERS (Apêndice C):** *"TBD-03: Se o anfitrião poderá aprovar manualmente cada reserva ou se toda reserva paga será confirmada automaticamente."*
- **Ambiguidade:** O item estava listado em aberto na ERS.
- **Decisão Adotada:** Adotou-se o modelo de "Reserva Instantânea". A aprovação do pagamento pelo gateway (seja cartão síncrono ou PIX assíncrono via webhook) transiciona a reserva para `CONFIRMADA` sem travar o usuário.
- **Alternativa Descartada:** Interromper o fluxo na Tela 2 exigindo login de outro ator para liberação manual.

---

## 4. Estrutura de Arquivos

```text
INF1377/
├── app.py                      # Aplicação Flask e rotas do fluxo
├── database.py                 # Conexão SQLite, DDL e carga de sementes (seed)
├── models.py                   # Regras de negócio, cálculos, validações e auditoria
├── requirements.txt            # Dependências Python (Flask, Pytest)
├── README.md                   # Documentação completa e guia
├── services/
│   ├── __init__.py
│   ├── payment_gateway.py      # Gateway simulado (Cartão e PIX com QR Code)
│   └── email_service.py        # Serviço simulado de envio de e-mail
├── templates/
│   ├── base.html               # Template base com navbar e ajuda
│   ├── index.html              # Catálogo inicial de acomodações
│   ├── resumo.html             # Tela 1: Resumo da Estadia
│   ├── pagamento.html          # Tela 2: Pagamento (Cartão e PIX)
│   └── confirmacao.html        # Tela 3: Confirmação e revelação de endereço
├── static/
│   ├── style.css               # Estilos da aplicação
│   └── app.js                  # Lógica de interface, polling e webhook
└── tests/
    ├── __init__.py
    └── test_fluxo.py           # Bateria de testes automatizados pytest
```

---

## 5. Manual de Execução e Guia de Testes

### Pré-requisitos
- Python 3.9 ou superior instalado.

### Passo a Passo de Instalação e Execução
1. Abra um terminal na pasta do projeto e crie o ambiente virtual:
   ```bash
   python -m venv venv
   ```
2. Ative o ambiente virtual:
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     source venv/bin/activate
     ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Inicie o servidor:
   ```bash
   python app.py
   ```
5. Abra o navegador no endereço: [http://localhost:5000](http://localhost:5000)

---

### Como Testar Todos os Cenários Manualmente

1. **Caminho Feliz com Cartão de Crédito:**
   - Na página inicial, selecione "Apartamento Vista Mar" e clique em **Iniciar Reserva**.
   - Na **Tela 1 (Resumo)**, confira as diárias e a taxa de 14%. Clique em **Confirmar e Ir para Pagamento**.
   - Na **Tela 2 (Pagamento)**, informe qualquer número de cartão (ex.: `4111 2222 3333 4444`) e clique em **Pagar com Cartão**.
   - O sistema aprova e redireciona síncronamente para a **Tela 3 (Confirmação)**, exibindo o código de autorização e o endereço físico desmascarado (Rua e CEP).

2. **Cenário de Recusa e Retentativa com Cartão (RF-26):**
   - Na Tela 2, preencha o número do cartão terminado em `0000` (ex.: `4111 2222 3333 0000`).
   - A transação é recusada pela simulação do gateway e uma mensagem em vermelho orienta o usuário a tentar novamente.
   - Substitua o final do número (ex.: por `1234`) e clique em pagar novamente para aprovar.

3. **Cenário PIX Assíncrono com Webhook (RF-23):**
   - Na Tela 2, clique na aba **PIX**.
   - Clique em **Gerar Código PIX**. O sistema exibirá o QR Code, a chave copia e cola com o `txid` único vinculado à reserva, e iniciará o polling assíncrono.
   - Clique no botão azul **Disparar Webhook de Liquidação**.
   - O webhook simula a liquidação bancária e o frontend detecta automaticamente a confirmação via polling, redirecionando para a Tela 3.

4. **Cenário do Benefício Superhost (RN-07 / RF-33):**
   - Na tela inicial, selecione a acomodação "Studio Luxo Superhost".
   - Na Tela 1, observe o destaque em verde informando o abatimento de 10% sobre a taxa de serviço de 14%.

5. **Execução da Bateria Automatizada de Testes:**
   ```bash
   pytest -v
   ```
