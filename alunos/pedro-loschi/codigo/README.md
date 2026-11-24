# Plataforma de Hospedagem (Airbnb Clone): ERS v1.2 (IEEE 830)
## Fluxo de Reserva, Pagamento e Confirmação + Cancelamento e Reembolso (INF1377 - Engenharia de Requisitos)

> **Cancelamento e reembolso (UC12):** acrescentados sobre o fluxo de reserva existente. Tudo sobre essa funcionalidade (telas, cenários de teste, rastreabilidade, requisitos não implementados e ambiguidades) está na [Seção 8](#8-cancelamento-de-reserva-e-reembolso-uc12). As seções 1 a 7 descrevem o fluxo de reserva, que não mudou de comportamento.

Este projeto implementa o fluxo completo de **reserva, pagamento e confirmação** especificado na **Especificação de Requisitos de Software (ERS v1.2)**, estruturado em **no máximo três telas**, conforme estipulado na **Seção 3.1** do documento:
1. **Tela 1: Resumo da Estadia** (`/resumo`)
2. **Tela 2: Pagamento** (`/pagamento/<reserva_id>`)
3. **Tela 3: Confirmação e Comprovante** (`/confirmacao/<reserva_id>`)

---

## 1. Tecnologias Utilizadas

- **Back-end:** Python 3 + Flask.
- **Banco de Dados:** SQLite (`hospedagem.db`), criado e populado automaticamente na primeira execução com o schema do Apêndice B.4 e dados de teste.
- **Front-end:** HTML5 semântico, CSS3 responsivo (de 360 px a 1920 px, RNF-16, com contraste WCAG 2.1 nível AA, RNF-14) e JavaScript puro (vanilla JS, sem frameworks externos).
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

A suíte tem 15 testes do fluxo de reserva (`tests/test_fluxo_reserva.py`) e 36 do cancelamento e reembolso (`tests/test_cancelamento.py`). Rode a partir desta pasta (`codigo/`):

```bash
pytest -v                               # suíte inteira
pytest tests/test_fluxo_reserva.py -v   # só o fluxo de reserva
pytest tests/test_cancelamento.py -v    # só o cancelamento e reembolso
```

Os testes usam um banco SQLite próprio, criado num diretório temporário por `tests/conftest.py` (variável `HOSPEDAGEM_DB_PATH`). Eles nunca tocam no `hospedagem.db` do app. Antes dessa mudança, os testes do fluxo de reserva apagavam e recriavam o banco do app a cada execução.

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
- **RF-21, RF-27 / UC12:** implementados depois, na funcionalidade de cancelamento e reembolso. Veja a [Seção 8](#8-cancelamento-de-reserva-e-reembolso-uc12).
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

---

## 8. Cancelamento de reserva e reembolso (UC12)

Funcionalidade acrescentada sobre o fluxo de reserva, conforme a ERS v1.2: **RF-21, RF-25, RF-27**, sequência 4 da **Seção 4.4.2**, **Seção 4.5.1** (o reembolso como pagamento da reserva), **RN-05** e **UC12 (Cancelar reserva)**. Ela usa o mesmo visual (`base.html` e `style.css`) e o mesmo banco SQLite, sem tabelas nem colunas novas.

O fluxo começa quando o hóspede ou o anfitrião, já logado, abre uma reserva PENDENTE ou CONFIRMADA e escolhe "Cancelar". Ele termina quando a reserva está CANCELADA, o reembolso devido foi solicitado ao gateway e registrado, e a outra parte foi notificada.

### 8.1 Arquivos criados e alterados

| Arquivo | O que mudou |
|---|---|
| `cancelamento.py` (novo) | Regras de negócio: política de reembolso (RN-05, UC12 2a), pré-condições e permissões, transação de cancelamento, reembolso como pagamento, histórico e notificação. |
| `templates/minhas_reservas.html` (novo) | Lista das reservas do usuário como hóspede e como anfitrião (UC12 passo 1). |
| `templates/reserva_detalhe.html` (novo) | Detalhe da reserva: pagamentos e reembolsos, histórico de status, botão "Cancelar reserva". |
| `templates/cancelar_reserva.html` (novo) | Confirmação: mostra o reembolso pela política e qual regra foi aplicada (passos 2 e 3). |
| `templates/_macros.html` (novo) | Selos de status e formatação de valores das telas novas. |
| `static/js/cancelamento.js` (novo) | Impede envio duplo e avisa se o prazo do reembolso integral vencer com a tela aberta. |
| `tests/test_cancelamento.py` (novo) | 36 testes do cancelamento e reembolso. |
| `tests/conftest.py` (novo) | Faz todos os testes usarem um banco temporário separado do banco do app. |
| `app.py` | Rotas novas (telas, API REST e simulação do gateway) e dois filtros de data. Nenhuma rota existente mudou. |
| `services/payment_gateway.py` | `process_refund` passou a simular recusa, indisponibilidade e idempotência. O método já existia e o fluxo de reserva não o usava. |
| `services/email_service.py` | Novo `send_reservation_cancelled`. |
| `database.py` | Caminho do banco configurável (`HOSPEDAGEM_DB_PATH`), duas acomodações e nove reservas de exemplo. Bancos antigos recebem esses dados uma única vez. |
| `templates/base.html` | Link "Minhas reservas", seção de ajuda sobre o cancelamento e barra de 3 passos só nas telas do fluxo de reserva. |
| `static/css/style.css` | Classes novas no fim do arquivo; nenhuma classe existente foi alterada. |

### 8.2 Telas e rotas

| Rota | Tipo | Passo do UC12 |
|---|---|---|
| `GET /reservas` | Tela | Passo 1: o usuário encontra a reserva (como hóspede ou como anfitrião). |
| `GET /reservas/<id>` | Tela | Passo 1: abre a reserva; o botão "Cancelar reserva" aparece só quando o cancelamento é permitido. |
| `GET /reservas/<id>/cancelar` | Tela | Passo 2: mostra o valor do reembolso pela política. |
| `POST /reservas/<id>/cancelar` | Formulário | Passos 3 a 5: confirma, cancela, reembolsa e notifica. Exige o token anti-CSRF da tela. |
| `GET /api/reservas/<id>/cancelamento` | API JSON | Passo 2 (prévia do reembolso). |
| `POST /api/reservas/<id>/cancelamento` | API JSON | Passos 3 a 5. Corpo opcional: `{"valor_exibido": 300.00}`. Exige `Content-Type: application/json`. |
| `GET/POST /api/dev/gateway-reembolso` | Simulação | Liga e desliga a indisponibilidade do gateway (`modo=INDISPONIVEL` ou `modo=NORMAL`). |

Respostas de erro da API: `404` reserva inexistente, `403` usuário sem permissão, `409` status não cancelável, estadia encerrada ou valor alterado, `502` gateway recusou o estorno, `503` gateway indisponível, `415` corpo que não é JSON, `401` sem login.

### 8.3 Como testar cada cenário

Rode `python app.py` e abra <http://127.0.0.1:5000/reservas> (ou clique em **Minhas reservas** no topo). Troque o usuário no seletor do cabeçalho. Os IDs abaixo valem para um banco recém-criado. Para recriar o banco do zero, rode `python database.py`, que **apaga** o `hospedagem.db` e o popula de novo.

Datas relativas ao dia em que o banco foi criado (D = hoje):

| Reserva | Acomodação | Período | Pagamento | Situação |
|---|---|---|---|---|
| #2 | #5 (Carlos, R$ 300) | D+30 a D+33 | Cartão, R$ 1.026,00 | CONFIRMADA, mais de 48 h antes do check-in |
| #3 | #5 (Carlos) | D+1 a D+3 | PIX, R$ 684,00 | CONFIRMADA, menos de 48 h antes |
| #4 | #6 (Mariana, superhost, R$ 400) | D+1 a D+3 | Cartão, R$ 900,80 | CONFIRMADA, menos de 48 h antes |
| #5 | #5 (Carlos) | D+40 a D+42 | Cartão com txid `FALHAESTORNO` | CONFIRMADA, o gateway recusa o estorno |
| #6 | #5 (Carlos) | D+50 a D+52 | nenhum | PENDENTE (expira 30 min depois da criação do banco, RN-04) |
| #7 | #5 (Carlos) | D+60 a D+62 | nenhum | CANCELADA |
| #8 | #5 (Carlos) | D-20 a D-17 | Cartão | CONCLUIDA |
| #9 | #5 (Carlos) | D-10 a D-7 | Cartão | CONFIRMADA com check-out já passado |
| #10 | #5 (Carlos) | D-2 a D+1 | Cartão, R$ 1.026,00 | CONFIRMADA, estadia em andamento |

**Caminho feliz**

| # | Cenário | Usuário | Como fazer | Resultado esperado |
|---|---|---|---|---|
| 1 | Hóspede cancela com 48 h ou mais de antecedência (RN-05) | Lucas | Minhas reservas, #2, Cancelar, Confirmar | Reembolso integral de R$ 1026.00. A reserva fica CANCELADA. Aparece uma linha "Reembolso" com status REEMBOLSADO e o pagamento original continua APROVADO. Carlos recebe o aviso e Lucas recebe o comprovante do reembolso. |
| 2 | Hóspede cancela com menos de 48 h (RN-05) | Lucas | #3, Cancelar | R$ 300.00 (50% de R$ 600 de diárias). Ficam retidos R$ 384.00 (a outra metade das diárias e a taxa de R$ 84). O reembolso sai pelo mesmo método do pagamento (PIX). |
| 3 | Anfitrião cancela (UC12 2a) | Carlos | Minhas reservas, "Reservas recebidas", #3, Cancelar | R$ 684.00, ou seja, tudo o que foi pago, mesmo faltando menos de 48 h. Lucas é notificado. Use o #3 no cenário 2 ou no 3, porque uma reserva só pode ser cancelada uma vez. |
| 4 | Anfitriã superhost cancela | Mariana | #4, Cancelar | R$ 900.80. Para comparar, se Lucas cancelar o #4, recebe R$ 400.00 (50% das diárias cheias; o desconto do superhost vale só sobre a taxa). |
| 5 | Cancelamento durante a estadia | Lucas | #10, Cancelar | R$ 450.00 (50% de R$ 900). Veja AMB-05. |
| 6 | Cancelar reserva PENDENTE | Lucas | #6, Cancelar (ou crie uma reserva nova na Tela 1, não pague e abra-a em Minhas reservas) | A tela informa que não há valor a reembolsar. O gateway não é chamado. Carlos é notificado. |

**Erros**

| # | Cenário | Como fazer | Resultado esperado |
|---|---|---|---|
| 7 | Gateway recusa o estorno | Lucas, #5, Cancelar, Confirmar | Mensagem "O serviço de pagamento recusou o reembolso...". A reserva continua CONFIRMADA, sem linha nova em pagamento, sem histórico novo e sem e-mail. |
| 8 | Gateway indisponível | Em Minhas reservas, clique em "Gateway indisponível". Depois Lucas, #2, Cancelar, Confirmar | Mensagem "O serviço de pagamento não respondeu...". Nada muda. Clique em "Gateway normal" e repita: agora funciona. |
| 9 | Reserva já CANCELADA ou CONCLUIDA | Lucas, #7 ou #8 | Não há botão "Cancelar". Abrindo `/reservas/7/cancelar` direto, aparece "Esta reserva está CANCELADA e não pode ser cancelada". |
| 10 | Check-out já passou | Lucas, #9 | "A estadia desta reserva já terminou...". |
| 11 | Usuário que não é parte da reserva (RNF-11) | Ana: `/reservas/2` ou `/reservas/2/cancelar`. Mariana: `/reservas/3/cancelar` | "Você não tem permissão..." e volta para Minhas reservas. A reserva não muda. |
| 12 | Sem login | Escolha "[Deslogado]" no seletor e abra `/reservas` | Volta para a Tela 1 com a mensagem de login. A API responde `401`. |
| 13 | Valor mudou entre a tela e a confirmação (AMB-12) | Logado como Lucas, envie `POST /api/reservas/3/cancelamento` com `{"valor_exibido": 684.00}` (exemplo abaixo) | `409 VALOR_ALTERADO` com o valor correto (R$ 300.00) em `dados`. Nada é cancelado. Na tela, se o prazo de 48 h vencer com a página aberta, o botão é desativado e aparece um aviso. |
| 14 | Formulário sem token ou de outro site | `POST /reservas/2/cancelar` sem `csrf_token`, ou `POST` na API com `Content-Type: text/plain` | Mensagem "A confirmação expirou..." ou `415`. A reserva não muda. |

Exemplo com `curl` (a primeira requisição já loga o Lucas, usuário padrão da sessão de teste):

```bash
curl -s -c cj.txt -b cj.txt http://127.0.0.1:5000/reservas > /dev/null
curl -s -c cj.txt -b cj.txt http://127.0.0.1:5000/api/reservas/3/cancelamento
curl -s -c cj.txt -b cj.txt -X POST -H "Content-Type: application/json" \
     -d '{"valor_exibido": 684.00}' http://127.0.0.1:5000/api/reservas/3/cancelamento
```

Os e-mails enviados aparecem em <http://127.0.0.1:5000/api/dev/emails>.

A reserva #1 (de Ana, criada pelo seed do fluxo de reserva) está CONFIRMADA sem nenhum pagamento registrado. Se ela for cancelada, o reembolso é R$ 0,00, porque o sistema só devolve o que foi efetivamente pago.

### 8.4 Sistemas externos simulados

**Gateway de pagamento** (`services/payment_gateway.py`, método `process_refund(txid, amount, reservation_id, idempotency_key)`):

| Situação | Como simular | Resposta |
|---|---|---|
| Estorno aprovado | Qualquer txid de pagamento aprovado | `sucesso=True`, `status="REEMBOLSADO"`, `refund_id="REF-<reserva>-..."` (vira o txid da linha de reembolso), `codigoAutorizacao="EST-..."` |
| Estorno recusado | txid com `FALHAESTORNO` (reserva #5 do seed) | `sucesso=False`, `status="RECUSADO"`, `motivo` |
| Valor inválido | `amount <= 0` | `sucesso=False`, `status="RECUSADO"` |
| Gateway fora do ar | `PaymentGateway.definir_modo_reembolso("INDISPONIVEL")`, botão em Minhas reservas ou `POST /api/dev/gateway-reembolso` com `modo=INDISPONIVEL` | levanta `GatewayIndisponivelError` |
| Repetição da mesma operação | mesma `idempotency_key` (o sistema usa `cancelamento-reserva-<id>`) | devolve o mesmo estorno, sem estornar de novo |

**Serviço de e-mail** (`services/email_service.py`, método `send_reservation_cancelled`): os e-mails ficam em memória e podem ser vistos em `/api/dev/emails`. Tipos: `CANCELAMENTO_RESERVA_ANFITRIAO` (o hóspede cancelou), `CANCELAMENTO_RESERVA_HOSPEDE` (o anfitrião cancelou, com os dados do reembolso) e `COMPROVANTE_REEMBOLSO_HOSPEDE` (o hóspede cancelou e houve reembolso).

### 8.5 Testes automatizados

`tests/test_cancelamento.py` tem 36 testes: 35 passam e 1 é `xfail` de propósito, documentando a lacuna AMB-06. Eles cobrem a política de reembolso (inclusive o limite exato de 48 h e o arredondamento), permissões, pré-condições, o fluxo completo com gravação em `pagamento` e nos dois históricos, notificações, falhas do gateway, cancelamento duplo, valor alterado, os dados de exemplo, as telas, a API, o login e o CSRF.

A RNF-15 pede cobertura de pelo menos 70%. Medida com `coverage` (que não entra no `requirements.txt`): **86% no total** e 99% em `cancelamento.py`. Para medir:

```bash
pip install coverage
coverage run --source=. --omit="tests/*" -m pytest && coverage report
```

### 8.6 Tabela de rastreabilidade (cancelamento e reembolso)

| ID | Onde foi implementado | Como testar |
|---|---|---|
| **RF-21** (cancelamento pelo hóspede ou pelo anfitrião) | `cancelamento.py`: `papel_do_usuario`, `verificar_pode_cancelar`, `cancelar_reserva`; `app.py`: `efetivar_cancelamento`, `api_cancelar_reserva` | Cenários 1 a 4 e 11; `test_uc12_hospede_cancela_com_antecedencia_reembolso_integral_registrado`, `test_uc12_2a_anfitriao_cancela_e_hospede_recebe_tudo_e_e_notificado`, `test_rf21_rnf11_quem_nao_e_parte_da_reserva_nao_cancela` |
| **RF-25** (status REEMBOLSADO) | `cancelamento.cancelar_reserva` (linha de reembolso com status `REEMBOLSADO`) | Cenário 1 (tabela de pagamentos da reserva); `test_uc12_hospede_cancela_com_antecedencia_reembolso_integral_registrado` |
| **RF-27** (processar o reembolso) | `cancelamento.calcular_reembolso`, `cancelamento.cancelar_reserva`, `PaymentGateway.process_refund` | Cenários 1 a 5, 7 e 8; `test_gateway_recusa_estorno_nada_e_alterado`, `test_gateway_indisponivel_nada_e_alterado_e_depois_funciona` |
| **Seção 4.4.2, seq. 4** (muda para CANCELADA e aplica a política) | `cancelamento.cancelar_reserva` | Cenários 1 a 6 |
| **Seção 4.5.1** (o reembolso é um pagamento da reserva) | `cancelamento.cancelar_reserva`: `INSERT` em `pagamento`, ligado à mesma reserva | `test_uc12_hospede_cancela_com_antecedencia_reembolso_integral_registrado` |
| **RN-05** (integral até 48 h; depois, 50% das diárias) | `cancelamento.calcular_reembolso` e as constantes `HORA_CHECKIN`, `ANTECEDENCIA_REEMBOLSO_INTEGRAL`, `PERCENTUAL_DIARIAS_CANCELAMENTO_TARDIO` | Cenários 1, 2, 4 e 5; `test_rn05_*`, `test_uc12_hospede_cancela_em_cima_da_hora_recebe_50_por_cento_das_diarias` |
| **UC12, pré-condição** (PENDENTE ou CONFIRMADA) | `cancelamento.verificar_pode_cancelar` | Cenários 9 e 10; `test_uc12_so_pendente_ou_confirmada_pode_ser_cancelada`, `test_reserva_com_checkout_passado_nao_pode_ser_cancelada` |
| **UC12, passo 1** (abrir a reserva e selecionar "Cancelar") | `app.view_minhas_reservas`, `app.view_reserva_detalhe`; `minhas_reservas.html`, `reserva_detalhe.html`; `cancelamento.listar_reservas_do_usuario` | `test_tela_fluxo_completo_do_uc12` |
| **UC12, passo 2** (exibir o reembolso) | `cancelamento.obter_previa_cancelamento`; `app.view_cancelar_reserva`, `app.api_previa_cancelamento`; `cancelar_reserva.html` | `test_tela_fluxo_completo_do_uc12`, `test_api_rest_previa_e_cancelamento` |
| **UC12, passo 3** (o usuário confirma) | Formulário de `cancelar_reserva.html`, `static/js/cancelamento.js`, conferência de `valor_exibido` em `cancelar_reserva` | Cenário 13; `test_valor_exibido_diferente_interrompe_sem_alterar_nada` |
| **UC12, passo 4** (CANCELADA e reembolso solicitado ao gateway) | `cancelamento.cancelar_reserva` | Cenários 1 a 8 |
| **UC12, passo 5** (notificar a outra parte) | `EmailService.send_reservation_cancelled`, chamado em `cancelar_reserva` | `/api/dev/emails`; testes do fluxo principal verificam os destinatários |
| **UC12, fluxo 2a** (anfitrião cancela: reembolso integral) | `cancelamento.calcular_reembolso` (regra `ANFITRIAO_INTEGRAL`) | Cenários 3 e 4; `test_uc12_2a_*` |
| **UC12, pós-condição** (CANCELADA e, quando cabível, REEMBOLSADO) | `cancelamento.cancelar_reserva` | `test_cancelar_pendente_nao_chama_o_gateway_e_nao_gera_reembolso` e os testes do fluxo principal |
| **RF-28** (comprovante por e-mail, estendido ao reembolso) | `EmailService.send_reservation_cancelled` (`COMPROVANTE_REEMBOLSO_HOSPEDE`) | Cenário 1; AMB-13 |
| **RN-04** (PENDENTE vencida já está cancelada) | `models.expirar_reservas_pendentes`, chamada antes de decidir em `obter_previa_cancelamento` e `cancelar_reserva` | `test_rn04_pendente_vencida_ja_foi_cancelada_e_nao_cancela_de_novo` |
| **RF-19** (datas liberadas após o cancelamento) | Herdado de `models.validar_disponibilidade_e_regras`, que ignora reservas CANCELADA | `test_cancelamento_libera_as_datas_e_esconde_o_endereco` |
| **RNF-05\*** (sem endereço exato fora de CONFIRMADA) | Herdado de `models.obter_reserva_completa`; o e-mail de cancelamento não leva o endereço | `test_cancelamento_libera_as_datas_e_esconde_o_endereco` |
| **RNF-08** (sem dados de cartão) | O estorno usa só o txid original; a linha de reembolso tem `tokenCartao` nulo | `test_uc12_hospede_cancela_com_antecedencia_reembolso_integral_registrado` |
| **RNF-11** (só as partes veem e mexem na reserva) | `cancelamento.papel_do_usuario`; `app.view_reserva_detalhe`; `listar_reservas_do_usuario` lista ao anfitrião só as reservas das acomodações dele | Cenário 11; `test_tela_terceiro_nao_ve_nem_cancela`, `test_tela_anfitriao_ve_reservas_recebidas_e_cancela` |
| **RNF-15** (cobertura de pelo menos 70%) | `tests/test_cancelamento.py` | Seção 8.5: 86% |
| **RNF-19** (guardar registros de pagamento) | Nada é apagado nem sobrescrito: o pagamento original continua APROVADO e o reembolso é uma linha nova | `test_uc12_hospede_cancela_com_antecedencia_reembolso_integral_registrado` |
| **RNF-22** (histórico com data, hora e responsável) | `cancelar_reserva` grava em `historico_status_reserva` e `historico_status_pagamento`; o detalhe da reserva mostra o histórico | `test_uc12_hospede_cancela_com_antecedencia_reembolso_integral_registrado` |
| **Seção 3.1** (ajuda em todas as telas, erros em linguagem simples) | `base.html` (seção 4 da ajuda); mensagens de `CancelamentoErro` | Telas dos cenários 7 a 12 |
| **Seção 3.4** (API REST com JSON) | `app.api_previa_cancelamento`, `app.api_cancelar_reserva` | `test_api_rest_previa_e_cancelamento` |
| **RNF-14, RNF-16** (WCAG 2.1 AA; 360 px a 1920 px) | Tabelas com `caption` e `scope`, `aria-label` nos botões, alertas com `role`, `.table-wrap` com rolagem horizontal | Manual: navegar pelo teclado e testar a 360 px de largura |
| **Isolamento dos testes** (pedido da tarefa) | `tests/conftest.py`, `database.DB_PATH` via `HOSPEDAGEM_DB_PATH` | O `hospedagem.db` do app não muda depois de `pytest` |

### 8.7 Requisitos relevantes que não foram implementados

| Item | Motivo |
|---|---|
| Notificação push (Seção 3.4: "por e-mail e por push no aplicativo móvel") | Não há aplicativo móvel neste projeto; só o e-mail foi simulado. |
| Guarda contra PIX pago depois do cancelamento (AMB-06) | Exigiria mudar o webhook do fluxo de reserva, o que a tarefa proíbe. Fica documentado no teste `xfail`. |
| Cancelar no gateway a cobrança PIX ainda aberta de uma reserva PENDENTE cancelada | A ERS não prevê essa operação e o RF-25 não tem status para cobrança cancelada (AMB-06). |
| Transição automática de CONFIRMADA para CONCLUIDA após o check-out (Seção 4.4.2, seq. 3) | Faz parte do ciclo da reserva, não do cancelamento. Em vez disso, o cancelamento é recusado depois do check-out (AMB-05). |
| Estorno do valor já repassado ao anfitrião (RN-08) | A ERS não define de onde sai o reembolso quando o repasse de 24 h após o check-in já aconteceu, e o repasse não existe neste código (AMB-05). |
| Reembolso de pagamentos aprovados em duplicidade (AMB-08) | Problema do fluxo de pagamento, que a ERS não trata. Só o pagamento que confirmou a reserva é estornado. |
| RF-22 (histórico do hóspede) e RF-11 (painel do anfitrião) completos | Foi feita só a lista mínima necessária para abrir a reserva (UC12 passo 1, UC15). Não há filtros, paginação nem painel. |
| UC17 (Processar reembolso) como caso de uso separado | Não tem descrição na B.3; o reembolso foi tratado dentro do UC12 (AMB-14). |
| Prazo real do estorno (TBD-01) | Depende do gateway, que ainda não foi definido. O estorno simulado é síncrono e o e-mail avisa que o prazo depende da instituição financeira. |
| Moderação de disputas pelo administrador (Seção 2.3) | Não há requisito funcional ou caso de uso para isso na ERS. |

### 8.8 Ambiguidades e decisões do cancelamento

Cada item traz o trecho da ERS, a interpretação adotada e a alternativa descartada. Os códigos AMB-xx aparecem nos comentários de `cancelamento.py` e nos testes.

**AMB-01: a que horas o check-in começa para contar as 48 horas**
- **Trecho:** RN-05: "Cancelamento pelo hóspede até 48 horas antes do check-in gera reembolso integral". Glossário: "Check-in / check-out: Data de entrada e data de saída do hóspede". A tabela `reserva` (B.4) guarda só a data.
- **Adotado:** o check-in começa às 14:00 do dia (`HORA_CHECKIN`), o mesmo horário que a tela de confirmação do fluxo de reserva já mostra ao hóspede ("a partir das 14:00"). O check-out termina às 11:00 (`HORA_CHECKOUT`), pelo mesmo motivo. O horário é o do servidor; a ERS não fala de fuso horário. Exatamente 48 h ainda dá reembolso integral ("até").
- **Descartado:** contar a partir de 00:00 do dia do check-in. Isso daria ao hóspede 14 horas a menos do que a própria interface sugere.

**AMB-02: o que entra no "reembolso integral" e nos "50% das diárias"**
- **Trecho:** RN-05: "reembolso integral; depois disso, reembolso de 50% das diárias". RN-03: a taxa de serviço é cobrada "sobre o valor das diárias".
- **Adotado:** integral = todo o valor pago (diárias + taxa de serviço). Tardio = 50% das diárias; a taxa de serviço não é devolvida. Para o superhost, as diárias são cheias, porque o desconto da RN-07 é só sobre a taxa. Os centavos são arredondados para cima a partir da metade.
- **Descartado:** (a) integral sem a taxa de serviço, já que a RN-05 não fala em "integral das diárias"; (b) 50% do valor total, porque a regra diz "das diárias".

**AMB-03: o reembolso é um pagamento novo ou uma mudança de status do pagamento original**
- **Trecho:** Seção 4.5.1: "Uma reserva pode ter um ou mais pagamentos (...), por exemplo uma tentativa recusada seguida de uma aprovada, ou um reembolso". RF-25: status "PROCESSANDO, APROVADO, RECUSADO e REEMBOLSADO". Pós-condição do UC12: "pagamento REEMBOLSADO".
- **Adotado:** o reembolso vira uma nova linha em `pagamento` da mesma reserva, com status REEMBOLSADO, o valor devolvido, o mesmo método do original, o `refund_id` do gateway como txid e o código de autorização do estorno. O pagamento original continua APROVADO.
- **Descartado:** mudar o pagamento original de APROVADO para REEMBOLSADO. Esse caminho apaga a informação no reembolso parcial (o registro diria "reembolsado", mas só parte foi devolvida) e contraria o exemplo da 4.5.1. Lacuna que fica: o B.4 não tem coluna que ligue o reembolso ao pagamento original. A ligação é feita pela reserva e pelo txid original enviado ao gateway e citado no comprovante.

**AMB-04: o que é cancelar "dentro da política"**
- **Trecho:** RF-27: "processar o reembolso quando uma reserva confirmada for cancelada dentro da política". A RN-05 não define nenhum caso "fora" da política: todo cancelamento do hóspede gera algum reembolso.
- **Adotado:** todo cancelamento permitido (reserva PENDENTE ou CONFIRMADA, antes do check-out) está dentro da política e recebe o valor definido pela RN-05 ou pelo UC12 2a. "Fora da política" é o cancelamento que não é permitido. Reserva PENDENTE não tem pagamento aprovado, então o valor é zero e o gateway não é chamado.
- **Descartado:** entender "fora da política" como cancelamento com menos de 48 h, sem reembolso nenhum, porque contradiz os 50% da RN-05.

**AMB-05: até quando a reserva pode ser cancelada**
- **Trecho:** pré-condição do UC12: "Reserva está PENDENTE ou CONFIRMADA" (sem limite de data). Seção 4.4.2, seq. 3: "A data de check-out passa → o sistema muda a reserva para CONCLUIDA". RN-08: o repasse ao anfitrião é liberado 24 h após o check-in.
- **Adotado:** pode cancelar até o check-out (11:00 do dia), inclusive durante a estadia. Nesse caso o hóspede recebe 50% das diárias, pela leitura literal da RN-05. Depois do check-out, o cancelamento é recusado mesmo que o status ainda seja CONFIRMADA, porque pela 4.4.2 a reserva já deveria estar CONCLUIDA (essa transição não existe no código do fluxo de reserva).
- **Descartado:** bloquear o cancelamento a partir do check-in. Seria uma regra mais restritiva que a ERS não escreveu. Lacuna que fica: devolver 50% de diárias já usadas é estranho, e a ERS não diz como estornar um valor que já foi repassado ao anfitrião (RN-08).

**AMB-06: PIX pago depois do cancelamento**
- **Trecho:** Seção 4.5.1: "o banco avisa o pagamento depois". RF-20: "A reserva passa de PENDENTE para CONFIRMADA automaticamente quando um pagamento é aprovado". A ERS não diz o que fazer com um pagamento recebido para reserva cancelada.
- **Situação no código:** se uma reserva PENDENTE com cobrança PIX aberta for cancelada (pelo usuário ou pela RN-04) e o banco avisar o pagamento depois, o webhook existente (`api_webhook_pix` e `models.confirmar_reserva_apos_pagamento`) reconfirma a reserva. As datas podem já ter sido reservadas por outra pessoa.
- **Adotado:** não mudar o fluxo de reserva, como a tarefa exige. A falha fica visível no teste `test_lacuna_pix_pago_depois_do_cancelamento_nao_deveria_reconfirmar`, marcado `xfail(strict=True)`: se alguém corrigir o webhook, o teste passa a avisar. A cobrança PIX aberta continua PROCESSANDO, porque o RF-25 não tem status de cobrança cancelada.
- **Descartado:** fazer o webhook recusar a confirmação de reserva CANCELADA e estornar automaticamente o PIX recebido. É a correção certa, mas muda o fluxo de reserva e depende de uma regra que a ERS não tem.

**AMB-07: o que fazer se o gateway recusar ou não responder**
- **Trecho:** UC12, passo 4: "O sistema muda a reserva para CANCELADA e solicita o reembolso ao gateway". O UC12 não tem fluxo alternativo para falha do gateway. TBD-01 deixa em aberto os prazos de reembolso do gateway.
- **Adotado:** tudo ou nada. Numa única transação (`BEGIN IMMEDIATE`), o sistema pede o estorno e só então grava a reserva CANCELADA, a linha de reembolso e os históricos. Se o gateway recusar (`502`) ou não responder (`503`), nada muda e o usuário pode tentar de novo. A chave de idempotência evita estorno em dobro se o banco local falhar depois do estorno.
- **Descartado:** cancelar mesmo assim e deixar o reembolso "pendente". Isso deixaria uma reserva CANCELADA sem o reembolso devido e exigiria um status de reembolso pendente que o RF-25 não tem.

**AMB-08: reserva com mais de um pagamento aprovado**
- **Trecho:** Seção 4.5.1 (uma reserva pode ter vários pagamentos). Nada impede, no fluxo de reserva, um cartão aprovado e um PIX pago depois para a mesma reserva.
- **Adotado:** estorna só o pagamento aprovado mais recente (o mesmo critério de `pagamento_aprovado` em `models.obter_reserva_completa`), aplicando a política sobre ele.
- **Descartado:** estornar todos os pagamentos aprovados. Seria tratar aqui um defeito do fluxo de pagamento, sem regra na ERS.

**AMB-09: de onde vem o valor das diárias**
- **Trecho:** RN-05 ("50% das diárias"). A tabela `reserva` do B.4 guarda só `valorTotal`.
- **Adotado:** diárias = noites x preço por noite atual da acomodação (`models.calcular_valores_estadia`, a mesma conta das telas do fluxo de reserva). O reembolso nunca passa do valor pago.
- **Descartado:** acrescentar uma coluna com o valor das diárias à tabela `reserva`, o que fugiria do projeto de tabelas. Lacuna que fica: se o anfitrião mudar o preço depois da reserva (RF-09, fora deste código), o valor dos 50% muda junto.

**AMB-10: quem é o responsável pela mudança de status do reembolso**
- **Trecho:** B.4, `historico_status_pagamento.responsavel_id`: "nulo quando a mudança vem do sistema ou do gateway". RNF-22: "data, hora e responsável".
- **Adotado:** o responsável é o usuário que pediu o cancelamento, que é quem desencadeou o estorno. É o mesmo critério que o código existente usa para o pagamento por cartão (o status APROVADO vem do gateway, mas o responsável é o hóspede).
- **Descartado:** responsável nulo. O histórico perderia quem pediu o estorno.

**AMB-11: a mesma pessoa é hóspede e anfitrião da reserva**
- **Trecho:** Seção 2.3: "Um mesmo usuário pode atuar como hóspede e como anfitrião". Nada impede alguém de reservar a própria acomodação.
- **Adotado:** vale o papel de hóspede (RN-05).
- **Descartado:** papel de anfitrião, que daria reembolso integral em qualquer momento.

**AMB-12: o valor mostrado no passo 2 pode mudar até o passo 4**
- **Trecho:** UC12, passos 2 e 3: "O sistema exibe o valor de reembolso conforme a política" e "O usuário confirma". A ERS não diz qual instante vale.
- **Adotado:** vale o instante da confirmação. A tela envia o valor que mostrou (`valor_exibido`). Se o servidor calcular outro valor (por exemplo, porque o prazo de 48 h venceu nesse meio-tempo), o cancelamento é interrompido e o novo valor é mostrado para o usuário confirmar de novo. O JavaScript também avisa se o prazo vencer com a tela aberta.
- **Descartado:** (a) respeitar o valor mostrado, o que permitiria reembolso integral depois do prazo; (b) aplicar o novo valor sem avisar, o que faria o usuário confirmar um valor que não viu.

**AMB-13: quem é notificado e por qual canal**
- **Trecho:** UC12, passo 5: "O sistema notifica a outra parte". Seção 3.4: "Notificações são enviadas por e-mail e por push no aplicativo móvel". RF-28: "comprovante do pagamento ao hóspede por e-mail".
- **Adotado:** e-mail para a outra parte (o anfitrião, se o hóspede cancelou; o hóspede, com os dados do reembolso, se o anfitrião cancelou). Além disso, quando o hóspede cancela e há reembolso, ele recebe o comprovante do reembolso, porque o reembolso é um pagamento da reserva (4.5.1) e o RF-28 pede comprovante de pagamento. Push não foi implementado.
- **Descartado:** notificar só a outra parte. O hóspede que cancelou ficaria sem nenhum registro do estorno.

**AMB-14: o UC17 (Processar reembolso) do diagrama**
- **Trecho:** o diagrama do B.2 tem o "UC17 Processar reembolso", ligado ao gateway e, por uma seta «extend», ao UC16 (Efetuar pagamento). A B.3 não descreve o UC17, e o passo 4 do UC12 é quem pede o reembolso.
- **Adotado:** o reembolso é processado dentro do UC12 (`cancelamento.cancelar_reserva`), seguindo a descrição textual e a tarefa.
- **Descartado:** modelar o reembolso como extensão do pagamento (UC16), como sugere o diagrama, sem descrição que diga quando ele seria acionado.
