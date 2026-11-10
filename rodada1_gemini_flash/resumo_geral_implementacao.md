# Resumo Geral da Implementação — Fluxo de Reserva, Pagamento e Confirmação

**Disciplina:** INF1377 — Engenharia de Requisitos  
**Projeto:** Plataforma de Hospedagem (Baseada no Airbnb)  
**Especificação:** ERS v1.1 / v1.2 (Padrão IEEE 830)  
**Diretório do Projeto:** `C:\Users\Davi Rangel\Documents\INF1377`  
**Data:** 10 de Novembro de 2026  

---

## 1. Objetivo do Projeto

Implementar o **fluxo transacional essencial de reserva, pagamento e confirmação** em **no máximo três telas**, conforme definido na **Seção 3.1** da ERS e no documento de entrega:
1. **Tela 1 — Resumo da Estadia (`/reservas/resumo`)**: Conferência de datas, noites, capacidade de hóspedes, discriminação do subtotal, taxa de serviço de 14% (RN-03) e desconto de 10% na taxa para Superhost (RN-07 / RF-18 / RF-33). Endereço protegido (RNF-05: apenas bairro e cidade).
2. **Tela 2 — Pagamento (`/reservas/<id>/pagamento`)**: Apresentação dos métodos de pagamento (Cartão de Crédito síncrono e PIX assíncrono com QR Code). Controle do timeout de 30 minutos da reserva (RN-04) e não armazenamento de dados sensíveis de cartão (RNF-08). Permite nova tentativa em caso de recusa (RF-26).
3. **Tela 3 — Confirmação (`/reservas/<id>/confirmacao`)**: Acessível apenas com a reserva em status `CONFIRMADA`. Exibe código de autorização, método, valor, comprovante de e-mail enviado (RF-28) e **revela o endereço físico completo** (rua, número e CEP), em observância ao **RNF-05**.

---

## 2. Estrutura de Arquivos Criada e Organizada

```text
C:\Users\Davi Rangel\Documents\INF1377\
│
├── app.py                      # Aplicação Flask principal e controladores de rotas
├── database.py                 # Conexão SQLite (com chaves estrangeiras ativas), DDL e seed
├── models.py                   # Regras de negócio, cálculos financeiros, disponibilidade e auditoria
├── requirements.txt            # Dependências obrigatórias: Flask>=3.0.0 e pytest>=7.4.3
├── README.md                   # Documentação detalhada, rastreabilidade, decisões e manual de uso
├── resumo_geral_implementacao.md # Este documento de resumo executivo da entrega
├── .gitignore                  # Exclusão de venv, bancos de dados temporários e cache
│
├── services/                   # Módulos isolados de serviços externos simulados
│   ├── __init__.py
│   ├── payment_gateway.py      # Gateway simulado (Cartão com recusa/aprovação e PIX com QR code)
│   └── email_service.py        # Serviço simulado de envio de e-mail de confirmação
│
├── templates/                  # Camada de apresentação (Jinja2 / HTML5 puro)
│   ├── base.html               # Layout base com navbar, usuário autenticado e botão de Ajuda
│   ├── index.html              # Listagem inicial para escolha de imóvel e período
│   ├── resumo.html             # Tela 1: Resumo e discriminação de valores
│   ├── pagamento.html          # Tela 2: Abas de pagamento (Cartão e PIX com simulação de webhook)
│   └── confirmacao.html        # Tela 3: Sucesso, código de autorização e endereço completo
│
├── static/                     # Assets front-end (sem frameworks externos)
│   ├── style.css               # Estilização moderna e responsiva inspirada no Airbnb
│   └── app.js                  # Lógica assíncrona, polling de status e disparo de webhook
│
└── tests/                      # Bateria de testes automatizados com pytest
    ├── __init__.py
    └── test_fluxo.py           # 10 testes automatizados cobrindo todas as RNs, RFs e RNFs
```

---

## 3. Matriz de Rastreabilidade e Cobertura de Requisitos

| ID ERS | Tipo | Descrição Sumária | Onde foi Implementado | Evidência de Validação |
| :--- | :--- | :--- | :--- | :--- |
| **RF-17** | Funcional | Criação de reserva com check-in, check-out e número de hóspedes | `app.py: criar_reserva()`, `templates/resumo.html` | Criada reserva via POST `/api/reservas`. |
| **RF-18** | Funcional | Cálculo de total: subtotal + taxa 14% - desconto Superhost | `models.py: calcular_valores()` | `test_rf18_rn07_desconto_superhost` (PASSED). |
| **RF-19** | Funcional | Bloqueio de reservas sobrepostas no mesmo imóvel | `models.py: validar_disponibilidade()` | `test_rf19_impedir_sobreposicao` (PASSED). |
| **RF-20** | Funcional | Controle do ciclo de vida da reserva (`PENDENTE`, `CONFIRMADA`, `CANCELADA`) | `database.py: reserva`, `app.py` | Transições de status conferidas nas rotas e no banco. |
| **RF-23** | Funcional | Pagamento via Cartão (síncrono) e PIX (assíncrono com txid único) | `services/payment_gateway.py`, `app.py` | `test_fluxo_pix_assincrono` (PASSED). |
| **RF-24** | Funcional | Registro de valor, código de autorização, txid e data/hora | `database.py: pagamento`, `app.py` | Registros gerados e verificados na tabela `pagamento`. |
| **RF-25** | Funcional | Status do pagamento: `PROCESSANDO`, `APROVADO`, `RECUSADO` | `database.py: pagamento` | Cartão com final 0000 recusa; cartão normal aprova. |
| **RF-26** | Funcional | Nova tentativa de pagamento após recusa | `app.py: pagar_cartao()`, `templates/pagamento.html` | `test_fluxo_cartao_recusa_e_aprovacao` (PASSED). |
| **RF-28** | Funcional | Envio de comprovante por e-mail após aprovação | `services/email_service.py` | Chamado em aprovação por cartão e webhook PIX. |
| **RN-01** | Negócio | Check-out posterior ao check-in (mínimo 1 noite) | `models.py`, `app.py: tela_resumo` | `test_rn01_estadia_minima` (PASSED). |
| **RN-02** | Negócio | Quantidade de hóspedes não pode exceder capacidade | `models.py`, `app.py: tela_resumo` | `test_rn02_capacidade_maxima` (PASSED). |
| **RN-03** | Negócio | Taxa de serviço de 14% sobre as diárias | `models.py: calcular_valores()` | Calculada no backend e discriminada na Tela 1. |
| **RN-04** | Negócio | Cancelamento automático após 30 min sem pagamento | `models.py: verificar_expiracao_reserva()` | `test_rn04_expiracao_reserva_timeout` (PASSED). |
| **RN-07 / RF-33** | Negócio / Funcional | Desconto de 10% sobre a taxa de serviço para Superhost | `models.py: calcular_valores()` | Linha destacada em verde na Tela 1 e validada em teste. |
| **RNF-02** | Não Funcional | Confirmação de cartão de crédito imediata (<10s) | `app.py: pagar_cartao()` | Processamento síncrono e instantâneo. |
| **RNF-05** | Não Funcional | Ocultação do endereço físico exato até a confirmação | `app.py`, `resumo.html`, `confirmacao.html` | `test_rnf05_ocultacao_endereco_antes_confirmacao` (PASSED). |
| **RNF-08** | Não Funcional | Não armazenamento de número completo e CVV do cartão | `database.py: pagamento`, `app.py` | `test_rnf08_nao_armazenar_cartao_sensivel` (PASSED). |
| **RNF-22** | Não Funcional | Auditoria de mudanças de status com data, hora e responsável | `database.py: auditoria`, `models.py` | `test_rnf22_auditoria_mudanca_status` (PASSED). |

---

## 4. Registro de Decisões de Projeto e Ambiguidades

1. **Benefício do Superhost (RN-07 / RF-33):**
   - *Decisão:* Adotou-se o atributo booleano `ehSuperhost` consolidado no banco para anfitriões/acomodações, aplicando 10% de abatimento sobre a taxa de serviço de 14% ($0.14 \times \text{subtotal} \times 0.10$).
   - *Alternativa descartada:* Cálculo em tempo de execução via histórico anual de conversas e notas, inviável e fora do escopo do fluxo de 3 telas.

2. **Ocultação de Endereço Físico (RNF-05):**
   - *Decisão:* A rota `/reservas/resumo` (Tela 1) projeta no SQL estritamente `bairro`, `cidade` e `estado`. Rua, número e CEP são consultados e renderizados apenas na rota `/reservas/<id>/confirmacao` (Tela 3) após validação de `status == 'CONFIRMADA'`.
   - *Alternativa descartada:* Ocultação no front-end por CSS/JS, o que violaria o requisito de segurança.

3. **Cancelamento por Timeout de 30 minutos (RN-04):**
   - *Decisão:* Implementação de checagem ativa preguiçosa (`verificar_expiracao_reserva`), calculando a diferença entre `criadoEm` e a hora UTC atual a cada interação com a reserva. Ao ultrapassar 1800s, o status transiciona para `CANCELADA` e é auditado.
   - *Alternativa descartada:* Uso de agendadores pesados em background (Celery, Redis), desnecessários para a escala do protótipo.

4. **Aprovação da Reserva (TBD-03):**
   - *Decisão:* Aprovado o pagamento (síncrono ou assíncrono via webhook), a reserva torna-se imediatamente `CONFIRMADA` (modelo Instant Booking).
   - *Alternativa descartada:* Bloquear o fluxo exigindo login de outro ator (anfitrião).

---

## 5. Resultado dos Testes Automatizados

O ambiente virtual `venv` foi configurado e a suite completa do `pytest` foi executada:

```text
tests/test_fluxo.py::test_rn01_estadia_minima PASSED                     [ 10%]
tests/test_fluxo.py::test_rn02_capacidade_maxima PASSED                  [ 20%]
tests/test_fluxo.py::test_rf18_rn07_desconto_superhost PASSED            [ 30%]
tests/test_fluxo.py::test_rf19_impedir_sobreposicao PASSED               [ 40%]
tests/test_fluxo.py::test_rn04_expiracao_reserva_timeout PASSED          [ 50%]
tests/test_fluxo.py::test_fluxo_cartao_recusa_e_aprovacao PASSED         [ 60%]
tests/test_fluxo.py::test_fluxo_pix_assincrono PASSED                    [ 70%]
tests/test_fluxo.py::test_rnf05_ocultacao_endereco_antes_confirmacao PASSED [ 80%]
tests/test_fluxo.py::test_rnf08_nao_armazenar_cartao_sensivel PASSED     [ 90%]
tests/test_fluxo.py::test_rnf22_auditoria_mudanca_status PASSED          [100%]

============================= 10 passed in 0.58s ==============================
```

---

## 6. Instruções Rápidas de Operação

### Executar a Aplicação Web
```powershell
cd "C:\Users\Davi Rangel\Documents\INF1377"
.\venv\Scripts\Activate.ps1
python app.py
```
Acesse no navegador: **http://localhost:5000**

### Executar os Testes Automatizados
```powershell
cd "C:\Users\Davi Rangel\Documents\INF1377"
.\venv\Scripts\Activate.ps1
pytest -v
```

### Cenários de Demonstração
1. **Caminho Feliz (Cartão):** Iniciar reserva no "Apartamento Vista Mar" $\rightarrow$ Conferir diárias na Tela 1 $\rightarrow$ Pagar com qualquer cartão na Tela 2 $\rightarrow$ Visualizar autorização e endereço completo na Tela 3.
2. **Recusa e Nova Tentativa (RF-26):** Na Tela 2, usar cartão terminado em `0000` para ver a mensagem de recusa sem cancelamento; em seguida, usar outro final para aprovar.
3. **PIX com Liquidação Webhook (RF-23):** Na Tela 2, aba PIX $\rightarrow$ Gerar PIX $\rightarrow$ Clicar no botão azul "Disparar Webhook de Liquidação" $\rightarrow$ Redirecionamento automático para Tela 3 via polling.
4. **Benefício Superhost (RN-07):** Iniciar reserva no "Studio Luxo Superhost" e conferir o abatimento de 10% sobre a taxa de serviço na Tela 1.
