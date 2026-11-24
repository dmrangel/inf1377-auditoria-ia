# Plataforma de Hospedagem (Airbnb Clone) — ERS v1.2 (IEEE 830)
## Implementação do Fluxo de Reserva, Pagamento e Confirmação (INF1377 - Engenharia de Requisitos)

Este projeto implementa o fluxo completo de **reserva, pagamento e confirmação** especificado na **Especificação de Requisitos de Software (ERS v1.2)**, estruturado em **no máximo três telas**, conforme estipulado na **Seção 3.1** do documento:
1. **Tela 1: Resumo da Estadia** (`/resumo`)
2. **Tela 2: Pagamento** (`/pagamento/<reserva_id>`)
3. **Tela 3: Confirmação e Comprovante** (`/confirmacao/<reserva_id>`)

A esse fluxo foi acrescentada a **Avaliação de Estadia** (ERS seção 4.6, RF-29 a RF-32, RN-06, UC18 e UC19). Ela começa quando a reserva passa para `CONCLUIDA` e o sistema convida hóspede e anfitrião a avaliar, e termina quando as avaliações são publicadas e a nota média da acomodação é atualizada. O selo superhost (RF-33, RN-07) continua fora do escopo. Veja a [seção 5](#5-avaliação-de-estadia-uc18-e-uc19).

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

São duas suítes `pytest`, cada teste com banco recriado do zero:

- `tests/test_fluxo_reserva.py`: 15 testes do fluxo de reserva, pagamento e confirmação (originais, sem alteração).
- `tests/test_avaliacao.py`: 36 testes da avaliação de estadia (conclusão automática, convite, publicação, nota média, RF-29 a RF-31, RN-06, permissões, telas e a correção da Tela 3).

```bash
pytest -v
```

Para medir a cobertura (RNF-15 pede pelo menos 70%):

```bash
pytest --cov=. --cov-report=term
```

O arquivo `.coveragerc` exclui a pasta `tests/` da medição, para que o número reflita só o código da aplicação.

Na última execução: **51 testes aprovados e cobertura de 88% do código da aplicação** (918 linhas, 109 não executadas). Por módulo: `avaliacoes.py` 97%, `rotas_avaliacao.py` 97%, `models.py` 91%, `app.py` 65%. As linhas não cobertas do `app.py` são rotas do fluxo de reserva que os testes originais não executam.

> Os testes recriam o arquivo `hospedagem.db`. Depois de rodá-los, apague `hospedagem.db` antes de abrir a aplicação para ter os dados de exemplo intactos.

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

## 5. Avaliação de Estadia (UC18 e UC19)

### 5.1 Telas e rotas

| Tela / rota | O que faz |
|---|---|
| Link **Avaliações (n)** no cabeçalho | Aparece em todas as telas para quem está conectado. O número é o convite na interface: estadias que o usuário ainda pode avaliar. |
| `GET /avaliacoes` | **Minhas avaliações**: aguardando avaliação (com o prazo), avaliações que o usuário escreveu (publicada ou aguardando) e avaliações publicadas sobre ele. |
| `GET /reservas/<id>/avaliar` | **Avaliar**. Para o hóspede é o UC18 (avalia a acomodação); para o anfitrião é o UC19 (avalia o hóspede e vê a nota média dele como hóspede). Nota de 1 a 5 estrelas e comentário opcional. |
| `GET /acomodacoes/<id>/avaliacoes` | **Avaliações da acomodação** (RF-15): nota média e comentários publicados. Aberta também a visitantes. |
| Tela 1 (`/resumo`) | Ganhou uma linha com a nota média e o link "ver avaliações" (RF-15). |
| `POST /api/reservas/<id>/avaliacoes` | API JSON `{"nota": 1..5, "comentario": "opcional"}`. Respostas: **201** gravada; **400** nota ou comentário inválido, reserva não concluída, cancelada, prazo encerrado ou anfitrião hospedado na própria acomodação; **401** sem login; **403** não participa da reserva; **404** reserva inexistente; **409** já avaliou. |
| `GET /api/acomodacoes/<id>/avaliacoes` | API JSON com a nota média e as avaliações publicadas. |

### 5.2 Ciclo da avaliação

1. **Conclusão:** quando a data de hoje é posterior ao check-out, a reserva `CONFIRMADA` passa para `CONCLUIDA`. A verificação é feita sob demanda, no mesmo padrão da expiração de 30 minutos (RN-04): a cada tela aberta por um usuário conectado e em cada rota de avaliação. A mudança é gravada em `historico_status_reserva` com responsável nulo (RNF-22).
2. **Convite:** no mesmo passo, hóspede e anfitrião recebem um e-mail simulado com o prazo e o link, e o contador do cabeçalho aumenta.
3. **Avaliação:** cada participante envia nota (1 a 5, inteira) e comentário opcional até 14 dias após o check-out, inclusive (RN-06). Cada um avalia uma única vez (RF-31), e depois de enviada a avaliação não pode ser alterada.
4. **Publicação:** a avaliação fica oculta para a outra parte e para o público até as duas partes avaliarem ou o prazo terminar. Quem já avaliou vê "aguardando a outra parte ou o fim do prazo".
5. **Nota média:** considera só avaliações publicadas escritas por hóspedes e é calculada na consulta, então está sempre atualizada (RF-32).

### 5.3 Dados de exemplo

Criados por `seed_avaliacoes.py` na primeira execução, com datas relativas a hoje (D). Todos ficam no passado para não interferir no fluxo de reserva. Usuários: **Lucas** (hóspede, id 1), **Ana** (hóspede, id 2), **Carlos** (anfitrião de Copacabana e do Chalé, id 3) e **Mariana** (superhost de Ipanema, id 4).

| Cenário | Reserva | Situação inicial |
|---|---|---|
| A | Lucas em Copacabana, check-out D−2 | `CONFIRMADA`; vira `CONCLUIDA` no primeiro acesso |
| B | Lucas em Ipanema, check-out D−5 | `CONCLUIDA`; Mariana já avaliou Lucas (oculta) |
| C | Lucas no Chalé, check-out D−14 | `CONCLUIDA`; hoje é o último dia do prazo |
| D | Lucas no Chalé, check-out D−20 | `CONCLUIDA`; só Lucas avaliou (nota 4); prazo encerrado, avaliação publicada |
| E | Lucas em Copacabana, D−12 a D−10 | `CANCELADA` |
| F | Ana em Copacabana (D−30) e em Ipanema (D−38) | `CONCLUIDAS`; as duas partes avaliaram (base das notas médias) |
| G | Carlos hospedado na própria acomodação (Copacabana), check-out D−7 | `CONCLUIDA` |
| — | Reserva #1 do seed original: Ana no Chalé, D+20 a D+25 | `CONFIRMADA` (ainda não terminou) |

Notas médias iniciais: Copacabana **5,0** (1 avaliação), Ipanema **4,0** (1), Chalé **4,0** (1).

> Se você já tinha um `hospedagem.db` de antes desta funcionalidade, os cenários são acrescentados a ele na próxima execução (só quando a tabela `avaliacao` está vazia). Para recomeçar do zero, apague `hospedagem.db`.

### 5.4 Como testar cada cenário

Use o seletor de usuário do cabeçalho para trocar de perfil. Os ids das reservas abaixo valem para um banco novo (apague `hospedagem.db` antes).

**Caminho feliz: as duas partes avaliam (cenário A, reserva #2)**
1. Como **Lucas**, abra [/avaliacoes](http://127.0.0.1:5000/avaliacoes). Aparecem 3 estadias aguardando avaliação (A, B e C) e o contador **3** no cabeçalho.
2. Em [/api/dev/emails](http://127.0.0.1:5000/api/dev/emails) estão os dois convites (`CONVITE_AVALIACAO`) da reserva #2, para Lucas e para Carlos.
3. Clique em **Avaliar estadia** na reserva #2, escolha 4 estrelas, escreva um comentário e envie. A tela mostra "Avaliação enviada. Ela será publicada quando a outra parte avaliar…" e o selo **Aguardando**.
4. Abra [/acomodacoes/1/avaliacoes](http://127.0.0.1:5000/acomodacoes/1/avaliacoes): a média continua **5,0** e o comentário de Lucas não aparece (está oculto).
5. Troque para **Carlos** e abra `/reservas/2/avaliar`. O título é "Como foi receber Lucas Hóspede?", e a tela avisa que Lucas já avaliou, sem mostrar o conteúdo. Avalie Lucas.
6. A tela mostra "Avaliação enviada e publicada" e, abaixo, a avaliação de Lucas. Em `/acomodacoes/1/avaliacoes` a média passa a ser **4,5** (5 e 4) com 2 avaliações.

**Publicação no segundo voto (cenário B, reserva #3)**
1. Como **Lucas**, em `/avaliacoes`, a seção "Avaliações sobre você" está vazia: a nota de Mariana está oculta.
2. Avalie a reserva #3. A avaliação é publicada na hora, e a de Mariana (5 estrelas) aparece na tela e em "Avaliações sobre você".
3. A média de Ipanema (Tela 1 com a acomodação #2, ou `/acomodacoes/2/avaliacoes`) é recalculada a partir de 4,0.

**Último dia do prazo (cenário C, reserva #4):** como **Lucas**, `/reservas/4/avaliar` mostra "Hoje é o último dia para avaliar" e aceita a avaliação.

**Erro: prazo encerrado, RN-06 (cenário D, reserva #5):** como **Carlos**, abra `/reservas/5/avaliar`. Não há formulário e a mensagem diz "O prazo para avaliar terminou em …". A avaliação de Lucas aparece, porque o fim do prazo a publicou. Pela API a resposta é **400**.

**Erro: reserva cancelada, RF-30 (cenário E, reserva #6):** como **Lucas**, `/reservas/6/avaliar` mostra "Reservas canceladas não podem ser avaliadas (RF-30)".

**Erro: estadia que ainda não terminou, RF-30 (reserva #1):** como **Ana**, `/reservas/1/avaliar` mostra "Esta estadia ainda não terminou…".

**Erro: avaliar duas vezes, RF-31 (cenário B):** como **Mariana**, `/reservas/3/avaliar` mostra a avaliação dela, sem formulário. Pela API, no console do navegador (F12) já logado como Mariana, a resposta é **409**:
```js
fetch("/api/reservas/3/avaliacoes", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({nota: 4})}).then(r => r.status)
```

**Erro: quem não participa da reserva (403):** como **Ana**, abra `/reservas/2/avaliar`. Você volta para `/avaliacoes` com "Você não participa desta reserva…". Pelo console, o mesmo `fetch` para `/api/reservas/2/avaliacoes` retorna **403**.

**Erro: anfitrião hospedado na própria acomodação (cenário G, reserva #9):** como **Carlos**, `/reservas/9/avaliar` mostra "Você é o anfitrião desta acomodação e também o hóspede desta reserva…". A reserva não aparece entre as pendentes e não gerou convite.

**Erro: nota inválida, RF-29:** no formulário, envie sem escolher estrelas: aparece "Escolha uma nota de 1 a 5 estrelas…". Pelo console, `nota: 0`, `6`, `4.5` ou `"abc"` retornam **400**, e um comentário com mais de 1000 caracteres também.

**Erro: sem login (401):** escolha "[Deslogado / Não Autenticado]" no seletor. O link Avaliações some, `/avaliacoes` mostra "Entre para continuar" (HTTP 401) e a API responde **401**. A página pública [/acomodacoes/1/avaliacoes](http://127.0.0.1:5000/acomodacoes/1/avaliacoes) continua acessível ao visitante.

**Tela 3 com reserva concluída:** como **Lucas**, abra [/confirmacao/2](http://127.0.0.1:5000/confirmacao/2). Ela mostra "Esta estadia já terminou", o botão **Avaliar esta estadia** e o endereço completo (Avenida Atlântica, 1500, apto 402). Antes desta alteração, a página redirecionava para o pagamento (veja a seção 9).

**Simular a passagem do tempo:** a aplicação usa a data real. Para ver uma reserva nova virar `CONCLUIDA`, ou um prazo terminar, os testes automatizados substituem `avaliacoes.hoje()` com `monkeypatch` (veja `test_conclusao_so_depois_do_dia_do_checkout` e `test_publicacao_pelo_fim_do_prazo`). Manualmente, você pode alterar as datas da reserva no SQLite, por exemplo `UPDATE reserva SET checkOut = date('now','-1 day') WHERE id = <id>;`.

---

## 6. Simulação de Sistemas Externos

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
- `send_review_invitation(destinatario_email, destinatario_nome, papel, reserva_id, acomodacao_titulo, outra_parte_nome, prazo_final, link)`:
  - Convida hóspede (`papel="HOSPEDE"`, UC18) ou anfitrião (`papel="ANFITRIAO"`, UC19) a avaliar, com o prazo da RN-06 e o link da tela de avaliação. Tipo `CONVITE_AVALIACAO`.
  - Não há resposta a simular: o envio sempre funciona. É disparado quando a reserva passa para `CONCLUIDA`, exceto se o prazo já terminou ou se o hóspede é o próprio anfitrião.
  - O link usa a variável de ambiente `BASE_URL` (padrão `http://127.0.0.1:5000`).
- Os e-mails ficam só em memória e se perdem quando o servidor reinicia.
- Para inspecionar os e-mails enviados em tempo real durante testes manuais, acesse a rota:
  [http://127.0.0.1:5000/api/dev/emails](http://127.0.0.1:5000/api/dev/emails).

---

## 7. Tabela de Rastreabilidade

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

**Avaliação de estadia** (testes em `tests/test_avaliacao.py`):

| ID | Tipo | Descrição Resumida | Onde foi Implementado | Como Testar |
|---|---|---|---|---|
| **4.4.2 passo 3** | Sequência | A data de check-out passa e a reserva vira CONCLUIDA. | `avaliacoes.py` (`concluir_reservas_encerradas`) | `test_conclusao_automatica_apos_checkout_com_convite_e_auditoria`, `test_conclusao_so_depois_do_dia_do_checkout`, `test_pendente_e_cancelada_nunca_viram_concluida`; cenário A. |
| **4.6.2 passo 1** | Sequência | Convite a hóspede e anfitrião. | `avaliacoes.py`, `services/email_service.py` (`send_review_invitation`), `templates/base.html` (link Avaliações), `templates/avaliacoes_pendentes.html` | `test_conclusao_automatica_apos_checkout_com_convite_e_auditoria`, `test_sem_convite_se_o_prazo_ja_terminou_quando_a_reserva_e_concluida`; `/api/dev/emails`. |
| **4.6.2 passo 3** | Sequência | Publicação quando ambos avaliam ou o prazo termina. | `avaliacoes.py` (`_SQL_PUBLICADA`, `situacao_para_usuario`) | `test_publicacao_quando_a_segunda_parte_avalia`, `test_publicacao_pelo_fim_do_prazo`, `test_avaliacao_oculta_nao_aparece_na_pagina_publica`; cenários B e D. |
| **RF-15** | Requisito Funcional | Exibir nota média e comentários da acomodação. | `templates/avaliacoes_acomodacao.html`, `templates/resumo.html`, `rotas_avaliacao.py` | `test_tela_avaliacoes_da_acomodacao_e_tela_1`, `test_visitante_ve_pagina_publica_da_acomodacao`. |
| **RF-29** | Requisito Funcional | Nota de 1 a 5 e comentário opcional. | `avaliacoes.py` (`_validar_nota`, `_validar_comentario`), `database.py` (CHECK), `templates/avaliar.html`, `static/js/avaliacao.js` | `test_rf29_nota_invalida`, `test_rf29_nota_em_texto_e_comentario_vazio`, `test_rf29_comentario_longo_ou_invalido`, `test_check_da_nota_no_banco`. |
| **RF-30** | Requisito Funcional | Avaliar somente reservas CONCLUIDAS. | `avaliacoes.py` (`_bloqueio`) | `test_rf30_reserva_nao_concluida`, `test_rf30_reserva_cancelada`; cenário E e reserva #1. |
| **RF-31** | Requisito Funcional | Uma avaliação por participante em cada reserva. | `avaliacoes.py` (`_bloqueio`, tratamento de `IntegrityError`), `UNIQUE(reserva_id, autor_id)` | `test_rf31_uma_avaliacao_por_participante`; cenário B como Mariana. |
| **RF-32** | Requisito Funcional | Recalcular a nota média a cada nova avaliação. | `avaliacoes.py` (`resumo_notas_acomodacao`) | `test_caminho_feliz_hospede_e_anfitriao_avaliam`, `test_publicacao_quando_a_segunda_parte_avalia`. |
| **RN-06** | Regra de Negócio | Prazo de 14 dias após o check-out. | `avaliacoes.py` (`prazo_final`, `_bloqueio`) | `test_rn06_ultimo_dia_ainda_vale`, `test_rn06_prazo_encerrado`; cenários C e D. |
| **UC18** | Caso de Uso | Avaliar estadia (hóspede avalia a acomodação). | `rotas_avaliacao.py`, `templates/avaliar.html` | `test_caminho_feliz_hospede_e_anfitriao_avaliam`, `test_tela_avaliar_mostra_formulario_ou_bloqueio`. |
| **UC19** | Caso de Uso | Avaliar hóspede (anfitrião avalia o hóspede). | `rotas_avaliacao.py`, `templates/avaliar.html`, `avaliacoes.py` (`resumo_notas_hospede`) | `test_caminho_feliz_hospede_e_anfitriao_avaliam`, `test_nota_media_do_hospede_para_o_anfitriao`. |
| **RNF-11** (por analogia) | RNF (Autorização) | Só participantes da reserva avaliam; o servidor verifica. | `avaliacoes.py` (`papel_do_usuario`), `rotas_avaliacao.py` (`login_obrigatorio`) | `test_quem_nao_participa_nao_avalia`, `test_sem_login_e_reserva_inexistente`, `test_anfitriao_hospedado_na_propria_acomodacao`. |
| **RNF-05\*** | RNF (Safety) | Endereço completo também para reserva CONCLUIDA; telas de avaliação mostram só bairro e cidade. | `models.py` (`obter_reserva_completa`), `app.py` (`view_confirmacao`) | `test_confirmacao_aceita_reserva_concluida_com_endereco`. |
| **RNF-22** | RNF (Auditoria) | CONFIRMADA → CONCLUIDA registrada com responsável nulo. | `avaliacoes.py` (`concluir_reservas_encerradas`) | `test_conclusao_automatica_apos_checkout_com_convite_e_auditoria`. |

---

### Requisitos da ERS Fora do Escopo Desta Entrega
Conforme explicitamente autorizado na especificação da tarefa (*"Funcionalidades fora do fluxo (cadastro, busca, avaliação, denúncias, cancelamento pelo usuário) não precisam ser implementadas"*):
- **RF-01 a RF-06 / UC01 a UC04:** Cadastro, recuperação de senha e edição de perfil (o fluxo inicia com o hóspede já autenticado; a regra de login é verificada no servidor via sessão).
- **RF-07 a RF-11 / UC05 a UC07:** Cadastro e edição de anúncios por anfitriões (os dados já são criados e disponibilizados via seed no SQLite).
- **RF-12 a RF-16 / UC08:** Mecanismo de busca geográfica com autocomplete e filtros amplos (o fluxo se inicia na escolha da acomodação pelo hóspede).
- **RF-21, RF-27 / UC12:** Cancelamento manual e política de reembolso a pedido do usuário (embora o cancelamento automático por expiração da RN-04 esteja implementado).
- **RF-33 / UC20:** Concessão dinâmica do selo superhost (o selo já consta no modelo e no cálculo do benefício da RN-07). As avaliações (RF-29 a RF-32, UC18, UC19) foram implementadas; veja a seção 5.
- **TBD-05:** Resposta pública do hóspede à avaliação recebida. Também ficam de fora a edição e a exclusão de avaliações e a moderação de avaliações pelo administrador (seção 2.3).
- **RF-34 a RF-36 / UC21, UC22:** Moderação e denúncias.

---

## 8. Lista de Ambiguidades e Decisões

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

### Ambiguidades da Avaliação de Estadia (AV-01 a AV-17)

Encontradas ao implementar a seção 4.6, a RN-06 e os casos de uso UC18 e UC19. O [RELATORIO.md](RELATORIO.md) traz a mesma lista, com a alternativa descartada de cada item, e a tabela de rastreabilidade por arquivo e função.

**AV-01: Quando e como a reserva passa para CONCLUIDA**
- **Trecho da ERS:** 4.4.2, passo 3: *"A data de check-out passa → o sistema muda a reserva para CONCLUIDA."*
- **Ambiguidade:** a ERS não diz se a reserva conclui no dia do check-out ou depois dele, nem que mecanismo faz a mudança. Também não diz de quais status ela parte.
- **Interpretação adotada:** a reserva conclui quando a data de hoje é **posterior** ao check-out ("a data passa"). A verificação é sob demanda, no mesmo padrão da Amb-03 (RN-04), e só parte de `CONFIRMADA`. PENDENTE e CANCELADA nunca viram estadia.
- **Alternativas descartadas:** concluir no próprio dia do check-out, quando o hóspede ainda pode estar no imóvel até as 11h; e um agendador em segundo plano, que exigiria dependência nova e não deixaria controlar o tempo nos testes.

**AV-02: O que é "convidar" a avaliar**
- **Trecho da ERS:** 4.6.2, passo 1: *"o sistema convida hóspede e anfitrião a avaliar"*. A seção 3.4 diz que notificações vão por e-mail e por push no aplicativo móvel.
- **Interpretação adotada:** um e-mail simulado para cada parte, enviado uma única vez, no momento da conclusão, mais o contador no link "Avaliações" do cabeçalho.
- **Alternativa descartada:** push, porque não existe aplicativo móvel neste projeto.

**AV-03: Publicação das avaliações**
- **Trecho da ERS:** 4.6.2, passo 3: *"Ambos avaliam ou o prazo termina → o sistema publica as avaliações."* Nenhum RF trata disso, e a tabela `avaliacao` (B.4) não tem coluna de publicação.
- **Interpretação adotada:** a avaliação fica oculta para a outra parte e para o público até as duas partes avaliarem ou o prazo terminar. O estado "publicada" é calculado a partir dos dados (`_SQL_PUBLICADA`). O autor vê a própria avaliação como "aguardando", e a outra parte só sabe que ela existe.
- **Alternativa descartada:** criar a coluna `publicada`, que fugiria do projeto de tabelas do B.4.

**AV-04: RF-32 contra a publicação**
- **Trecho da ERS:** RF-32: *"recalcular a nota média da acomodação a cada nova avaliação"*.
- **Ambiguidade:** recalcular no envio coloca na média uma nota ainda oculta e permite deduzir o seu valor, o que contradiz o passo 3 da 4.6.2.
- **Interpretação adotada:** a média só considera avaliações publicadas e muda no momento em que cada uma é publicada.
- **Alternativa descartada:** a leitura literal do RF-32.

**AV-05: Onde fica a nota média**
- **Trecho da ERS:** RF-15 e RF-32 citam a nota média, mas a tabela `acomodacao` (B.4) não tem coluna para ela.
- **Interpretação adotada:** calcular com `AVG` na consulta, sem guardar. Assim ela está sempre recalculada.
- **Alternativa descartada:** criar a coluna `notaMedia`.

**AV-06: Qual nota média o UC19 atualiza**
- **Trecho da ERS:** pós-condição de UC18 e UC19: *"Avaliação registrada e nota média atualizada."* A ERS só define nota média da acomodação, e `usuario` não tem coluna de nota.
- **Interpretação adotada:** a média do hóspede (notas publicadas dadas por anfitriões) é calculada e mostrada ao anfitrião na tela "Avaliar hóspede".
- **Alternativa descartada:** não ter média para o hóspede.

**AV-07: Quem é avaliado, e o anfitrião hospedado na própria acomodação**
- **Trecho da ERS:** a tabela `avaliacao` não indica quem é avaliado. A seção 2.3 diz que um mesmo usuário pode ser hóspede e anfitrião, e o fluxo de reserva não impede o anfitrião de reservar a própria acomodação.
- **Interpretação adotada:** o avaliado é deduzido do autor. Se o autor é o hóspede da reserva, a avaliação é da acomodação (UC18); se é o anfitrião, é do hóspede (UC19). Quando hóspede e anfitrião são a mesma pessoa, a avaliação é recusada, ninguém recebe convite e a reserva não aparece entre as pendentes (cenário G).
- **Alternativa descartada:** criar a coluna `tipo` em `avaliacao`.

**AV-08: Comentário obrigatório ou opcional, e tamanho**
- **Trecho da ERS:** UC18/UC19, passo 2: *"informa a nota (1 a 5) e um comentário"*. RF-29: *"comentário opcional"*.
- **Interpretação adotada:** opcional, porque o RF prevalece sobre o passo do caso de uso. Texto só com espaços vira nulo. Limite de 1000 caracteres, que a ERS não define.

**AV-09: Nota inteira ou fracionada**
- **Trecho da ERS:** RF-29: *"nota de 1 a 5"*.
- **Interpretação adotada:** só inteiros de 1 a 5, verificados no servidor e por `CHECK` no banco.
- **Alternativa descartada:** meias estrelas.

**AV-10: Como contar os 14 dias**
- **Trecho da ERS:** RN-06: *"14 dias após o check-out"*. O check-out não tem hora.
- **Interpretação adotada:** a avaliação é aceita até o fim do dia `checkOut + 14`, inclusive (cenário C).
- **Alternativa descartada:** 14 × 24 horas a partir de um horário que a ERS não define.

**AV-11: O prazo termina com uma avaliação só**
- **Trecho da ERS:** 4.6.2, passo 3, não trata o caso.
- **Interpretação adotada:** a única avaliação existente é publicada e entra na média (cenário D).

**AV-12: Editar ou excluir avaliação**
- **Trecho da ERS:** não trata. RF-31 limita a uma avaliação por participante.
- **Interpretação adotada:** depois de enviada, a avaliação não pode ser alterada nem excluída. A resposta pública (TBD-05) e a moderação pelo administrador ficam fora do escopo.

**AV-13: Acomodação sem avaliações**
- **Interpretação adotada:** a tela mostra "Sem avaliações" em vez de nota 0. A média aparece com uma casa decimal e vírgula (4,5).

**AV-14: Formato da API**
- **Trecho da ERS:** seção 3.4: API REST com dados em JSON.
- **Interpretação adotada:** o envio é feito por `fetch` com JSON, como no pagamento. As respostas seguem o padrão existente `{"sucesso", "mensagem"}`, com 400 para regras de negócio (como o código existente) e 409 para avaliação repetida.

**AV-15: Endereço exato depois da estadia**
- **Trecho da ERS:** RNF-05\*: *"O endereço exato da acomodação só deve ser exibido ao hóspede após a reserva ser CONFIRMADA"*. A ERS não diz o que acontece depois de CONCLUIDA.
- **Interpretação adotada (decisão da equipe):** a reserva CONCLUIDA já foi confirmada, então a Tela 3 continua mostrando o endereço completo. As telas de avaliação mostram só bairro e cidade, porque não precisam do endereço.

**AV-16: Convite quando o prazo já terminou**
- **Ambiguidade:** como a conclusão é sob demanda, uma reserva pode ser concluída mais de 14 dias depois do check-out, se ninguém acessou o sistema nesse período.
- **Interpretação adotada:** a reserva é concluída, mas ninguém recebe convite, porque não há mais prazo para avaliar.

**AV-17: Auditoria das avaliações**
- **Trecho da ERS:** RNF-22: *"Toda mudança de status de reserva e de pagamento deve ser registrada com data, hora e responsável."* A regra não cita avaliações.
- **Interpretação adotada:** a mudança CONFIRMADA → CONCLUIDA é registrada em `historico_status_reserva`. A avaliação já guarda autor e data e hora, e não muda depois de gravada, então não há histórico separado.
- **Alternativa descartada:** criar uma tabela de histórico de avaliações, fora do projeto de tabelas do B.4.

---

## 9. Alterações no Fluxo de Reserva

A avaliação de estadia não muda o comportamento das reservas PENDENTE, CONFIRMADA e CANCELADA. As alterações abaixo são as únicas feitas em arquivos do fluxo de reserva. Os 15 testes originais (`tests/test_fluxo_reserva.py`) continuam passando sem alteração.

| Arquivo | Alteração | Motivo |
|---|---|---|
| `app.py` (`view_confirmacao`) | Aceita `CONCLUIDA` além de `CONFIRMADA`. | Antes, a Tela 3 de uma reserva concluída redirecionava para o pagamento. Pedido da equipe: a conclusão não pode quebrar a tela de confirmação. |
| `models.py` (`obter_reserva_completa`) | O endereço completo é liberado para `CONFIRMADA` e `CONCLUIDA` (RNF-05\*). | Faz parte da mesma correção: a Tela 3 da reserva concluída mostra o endereço como numa confirmada. |
| `app.py` (`view_pagamento`) | Reserva `CONCLUIDA` redireciona para a Tela 3, como já acontecia com `CONFIRMADA`. | **Mudança fora do plano aprovado.** Sem ela, `/pagamento/<id>` de uma reserva concluída mostraria a tela de pagamento de uma reserva já paga. |
| `templates/confirmacao.html` | Para `CONCLUIDA`: selo "ESTADIA CONCLUÍDA", título "Esta estadia já terminou" e botão "Avaliar esta estadia". O aviso do RNF-05\* mostra o status real. | Os textos fixos diziam "RESERVA CONFIRMADA". |
| `templates/base.html` | A barra de 3 passos só aparece quando a página define `step`; link "Avaliações (n)" no cabeçalho; seção 4 no modal de ajuda. | As telas de avaliação não fazem parte dos 3 passos. Sem a condição, o Jinja gera erro ao comparar `step > 1` sem `step`. As telas de reserva continuam iguais, porque todas definem `step`. |
| `templates/resumo.html` | Linha com a nota média e o link "ver avaliações" (RF-15). | Só exibe informação; o cálculo vem de uma função de template, sem mudar `view_resumo`. |
| `database.py` | `CHECK (nota BETWEEN 1 AND 5)` na tabela `avaliacao` e chamada a `seed_avaliacoes` em `init_db`. | RF-29 no banco e dados de exemplo. O `CHECK` só vale para bancos novos; um `hospedagem.db` antigo continua sem ele, e a validação no servidor é a garantia real. |
| `services/email_service.py` | Novo método `send_review_invitation`. | Convite da seção 4.6.2, passo 1. |
| `static/css/style.css` | Estilos das avaliações acrescentados no fim do arquivo. | Nenhuma regra existente foi alterada. |
| `requirements.txt` | `pytest-cov`. | Medir a cobertura de 70% do RNF-15. |

**Problema encontrado e não corrigido:** sem usuário conectado, `/resumo` redireciona para `/resumo` em laço (`login_required` aponta para a própria tela). O problema já existia no fluxo de reserva e corrigir mudaria esse fluxo, então ficou registrado aqui. As telas de avaliação não redirecionam para `/resumo`: respondem 401 com uma página explicativa.
