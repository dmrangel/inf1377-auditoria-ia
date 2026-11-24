# Ambiguidades e decisões

Cada item traz o trecho da ERS v1.2, a interpretação adotada e a alternativa descartada. A coluna "Onde" aponta o código afetado.

## A01 — UC06 e UC07 não estão descritos na ERS

- **Trecho:** B.3: "Os casos de uso que não estão detalhados aqui têm descrição no documento de Engenharia de Requisitos citado na Seção 1.5." A ERS detalha só o UC05. Os nomes **UC06 Alterar acomodação** e **UC07 Remover acomodação** aparecem apenas no diagrama de casos de uso (B.2, PlantUML embutido no PDF). Pelo diagrama, o UC06 usa o serviço de CEP e o armazenamento de arquivos.
- **Interpretação:** pela regra do repositório, o documento externo não foi lido. Os fluxos de UC06 e UC07 foram inferidos de RF-09 ("editar ou desativar"), do UC05 (mesmas validações) e das ligações do diagrama.
- **Alternativa descartada:** consultar o documento externo.
- **Onde:** `dominio/acomodacoes.py` (`atualizar_acomodacao`, `adicionar_fotos`, `remover_foto`, `desativar`).

## A02 — "Remover" (UC07, seção 2.2) × "desativar" (RF-09)

- **Trecho:** 2.2: "o anfitrião cadastra, edita, publica e **remove** anúncios"; UC07: "**Remover** acomodação"; RF-09: "editar ou **desativar** um anúncio"; B.4: coluna `ativo` em `acomodacao`.
- **Interpretação:** remover = **exclusão lógica** (`ativo = 0`). O anúncio sai da vitrine e das buscas e continua na lista do anfitrião, que pode reativá-lo.
- **Motivos:** reservas e pagamentos apontam para a acomodação (FK), e os registros de pagamento devem ser guardados por 5 anos (RNF-19). Uma exclusão física quebraria esse histórico.
- **Alternativa descartada:** `DELETE` físico, ou exclusão física só quando não há reservas.
- **Onde:** `desativar`, `reativar`.

## A03 — Desativar anúncio que tem reservas futuras

- **Trecho:** a ERS não diz o que acontece com reservas PENDENTE/CONFIRMADA de um anúncio desativado.
- **Interpretação:** a desativação é permitida, mas **as reservas existentes continuam valendo**. Se houver reservas futuras ativas, o servidor responde `409 CONFIRMACAO_NECESSARIA` com a lista. O anfitrião precisa confirmar (`confirmar: true`). Cancelar reservas é o UC12, com reembolso pela RN-05, e não é feito aqui.
- **Alternativas descartadas:** (a) impedir a desativação enquanto houver reservas; (b) cancelar todas automaticamente com reembolso integral (UC12, fluxo 2a). A (b) mistura duas funcionalidades e tem efeito financeiro difícil de desfazer.
- **Onde:** `desativar`, `_reservas_futuras_ativas`.

## A04 — Publicação imediata × rascunho

- **Trecho:** UC05 passo 6: "O sistema valida os dados e publica o anúncio"; 2.2 cita "publica" como ação separada; o B.4 só tem `ativo`.
- **Interpretação:** o anúncio é publicado (`ativo = 1`) no mesmo envio do cadastro. Não existe estado de rascunho, e "publicar de novo" corresponde a reativar.
- **Alternativa descartada:** um status RASCUNHO/PUBLICADO, que exigiria uma coluna fora do B.4.

## A05 — Fotos não têm tabela no B.4

- **Trecho:** RF-08 (5 a 30 fotos) e 3.3 (armazenamento de JPEG/PNG até 10 MB); o B.4 não lista onde guardar as fotos.
- **Interpretação:** criada a tabela `foto` (id, acomodacao_id, chave, tipoConteudo, tamanhoBytes, ordem, dataEnvio). O arquivo fica no serviço de armazenamento; o banco guarda só a chave. A primeira foto (menor `ordem`) é a capa.
- **Alternativa descartada:** coluna com lista de URLs em `acomodacao`, que não deixa validar a quantidade nem remover uma foto específica.
- **Onde:** `schema.sql`, `_gravar_fotos`.

## A06 — Bloqueio de datas (RF-10) não tem tabela nem caso de uso

- **Trecho:** RF-10: "bloqueie datas no calendário". Não há tabela no B.4 nem UC no diagrama.
- **Interpretação:** criada a tabela `bloqueio_data` com uma linha por noite e `UNIQUE(acomodacao_id, data)`. A interface aceita períodos (`inicio`, `fim`).
- **Alternativa descartada:** tabela de intervalos (inicio, fim), que complica a junção e a divisão de períodos ao desbloquear parte deles.

## A07 — Semântica de "data bloqueada" e conflitos

- **Trecho:** RF-10 não define se a data é noite ou dia, nem o que fazer com datas já reservadas.
- **Interpretação:**
  - A data **D** bloqueia a **noite** de D para D+1. Isso é coerente com a reserva, que ocupa as noites de `checkIn` até `checkOut - 1` (RN-01). Por isso o dia do check-out de uma reserva pode ser bloqueado.
  - Uma noite ocupada por reserva **PENDENTE ou CONFIRMADA** não pode ser bloqueada (409). Reservas CANCELADA e CONCLUIDA não impedem.
  - Não se bloqueiam nem desbloqueiam datas passadas.
  - O limite é de **366 noites por pedido**, para evitar pedidos gigantes. A ERS não fala nisso.
  - Bloquear uma noite já bloqueada não dá erro (operação idempotente).
- **Alternativa descartada:** bloquear "por cima" da reserva, ou cancelá-la, deixando hóspede e calendário em conflito.
- **Onde:** `bloquear_datas`, `validar_periodo_bloqueio`.

## A08 — Quem pode anunciar

- **Trecho:** UC05, pré-condição: "Anfitrião está logado"; RF-06: o hóspede ativa o papel de anfitrião; B.4: `usuario.ehAnfitriao`.
- **Interpretação:** só usuários com `ehAnfitriao = 1` anunciam, editam ou listam acomodações. Os demais recebem 403 com uma mensagem que aponta a ativação do papel (RF-06, fora desta tarefa).
- **Alternativa descartada:** ativar o papel automaticamente no primeiro anúncio, o que misturaria o RF-06 com o UC05.

## A09 — Resposta para quem não é dono (RNF-11)

- **Trecho:** RNF-11: "Apenas o anfitrião dono de uma acomodação pode editá-la ou ver as reservas dela." Não diz qual resposta dar.
- **Interpretação:** **403** para acomodação existente de outro anfitrião e **404** para id inexistente. O 403 dá uma mensagem clara ao testador.
- **Alternativa descartada:** 404 para os dois casos, o que esconde a existência do id. É mais conservador, mas como ids de anúncios ativos são públicos de qualquer forma (busca/UC09), não traz ganho real.
- **Também:** o dono é sempre o usuário da sessão. Um `anfitriao_id` enviado no formulário é ignorado.

## A10 — Validação do endereço pelo serviço de CEP

- **Trecho:** 3.3: serviço de CEP para "Preencher **e validar** o endereço"; UC05 fluxo 3a: "CEP não encontrado: o anfitrião preenche o endereço manualmente".
- **Interpretação:**
  - O servidor **consulta o CEP de novo** ao salvar e não confia no que o navegador preencheu. Se o CEP é encontrado, rua, bairro, cidade e UF do serviço **prevalecem** sobre o digitado. Na tela, esses campos ficam somente leitura.
  - CEP geral de município (o serviço devolve só cidade/UF): rua e bairro ficam com o que o anfitrião digitou.
  - CEP não encontrado: vale o endereço manual (fluxo 3a).
  - **Serviço fora do ar:** tratado como o fluxo 3a (endereço manual). A ERS não cobre esse caso; a alternativa descartada era impedir o cadastro até o serviço voltar.
  - O CEP precisa ter 8 dígitos em qualquer caso.
- **Alternativa descartada:** recusar o envio quando o endereço digitado difere do serviço.
- **Onde:** `resolver_endereco`.

## A11 — Limites dos campos (RF-07) não definidos

- **Trecho:** RF-07 lista os campos, mas não diz quais são obrigatórios nem os limites de cada um.
- **Interpretação:** todos os campos de RF-07 são obrigatórios. "Endereço completo" foi lido como CEP, rua, número, bairro, cidade e UF, as colunas do B.4. Não há complemento, porque o B.4 não tem essa coluna. Limites adotados:

| Campo | Regra adotada |
|---|---|
| título | 5 a 100 caracteres |
| descrição | 20 a 5000 caracteres |
| regras da casa | obrigatório, até 2000 (o anfitrião pode escrever "Sem regras específicas") |
| preço por noite | > 0 e ≤ R$ 100.000,00, até 2 casas decimais; aceita "350,00" e "1.234,56" |
| capacidade máxima | 1 a 50 |
| quartos | 0 a 50 (0 = estúdio) |
| banheiros | 1 a 50 |
| camas | 1 a 100 |
| número | 1 a 20 caracteres (aceita "s/n") |
| UF | uma das 27 siglas |

- **Alternativa descartada:** aceitar qualquer valor não vazio, o que permitiria preço zero ou capacidade negativa. Também foi descartado exigir camas ≥ capacidade, regra que a ERS não estabelece.
- **Onde:** `dominio/validacao.py`.

## A12 — Edição com reservas existentes

- **Trecho:** a ERS não diz como a edição afeta reservas já feitas.
- **Interpretação:**
  - **Preço:** o `valorTotal` fica gravado na reserva quando ela é criada (RF-18), então o novo preço só vale para reservas novas.
  - **Capacidade:** não pode ficar menor que o `numHospedes` de uma reserva PENDENTE/CONFIRMADA que ainda não terminou (409). Do contrário, a reserva passaria a violar a RN-02.
  - **Endereço:** pode ser alterado mesmo com reservas. Notificar hóspedes confirmados sobre a mudança fica como lacuna (ver rastreabilidade).
- **Alternativa descartada:** bloquear qualquer edição enquanto houver reserva ativa.

## A13 — Representação do preço

- **Trecho:** B.4 `precoNoite`, sem tipo definido.
- **Interpretação:** guardado em **centavos (inteiro)**, para evitar erro de arredondamento de ponto flutuante. A API devolve `precoNoite` como texto decimal ("450.00") e `precoNoiteCentavos`.
- **Alternativa descartada:** `REAL`.

## A14 — Reativação e mínimo de fotos em anúncio desativado

- **Trecho:** RF-09 fala em desativar, não em reativar.
- **Interpretação:** existe a ação **reativar**. O mínimo de 5 fotos vale também para anúncio desativado (não dá para remover a 5ª foto), para que ele sempre possa voltar a ser publicado. Anúncios desativados podem ser editados e ter datas bloqueadas.
- **Alternativa descartada:** desativação sem volta (o anfitrião teria de cadastrar tudo de novo).

## A15 — Quais reservas e quais dados do hóspede aparecem ao anfitrião (RF-11)

- **Trecho:** RF-11: "listar ao anfitrião todas as suas acomodações e reservas recebidas".
- **Interpretação:** todas as acomodações, ativas e desativadas, com as reservas em **todos os status**, cada uma identificada. Do hóspede aparece só o **nome**; e-mail e telefone não aparecem, por minimização (LGPD; RNF-17 trata do próprio titular). O contato entre as partes depende do TBD-04 (mensagens).
- **Alternativa descartada:** mostrar só reservas futuras, ou mostrar os contatos do hóspede.

## A16 — Tamanho e tipo de foto: onde validar

- **Trecho:** 3.3: "Imagens JPEG/PNG de até 10 MB" aparece na tabela do serviço externo, não como RF.
- **Interpretação:** a regra é aplicada em três camadas: na tela (para dar retorno rápido), no servidor pela **assinatura do arquivo** (sem confiar na extensão nem no Content-Type) e no próprio armazenamento simulado. O limite é ≤ 10 MB, com 10 MB = 10 × 1024 × 1024 bytes.
- **Alternativa descartada:** validar só pela extensão, o que deixaria passar um GIF renomeado para .png.

## A17 — Atomicidade do cadastro com fotos

- **Trecho:** UC05 passos 5 e 6 ("envia as fotos" e "valida e publica"), sem dizer o que acontece se o armazenamento falhar no meio.
- **Interpretação:** tudo ou nada. Se uma foto falha, a acomodação não é criada e as fotos já enviadas são apagadas do armazenamento. Na edição, adicionar ou remover foto é imediato, uma operação por vez.
- **Alternativa descartada:** salvar a acomodação e as fotos que deram certo, o que deixaria um anúncio publicado com menos de 5 fotos.

## A18 — Vitrine pública

- **Trecho:** pós-condição do UC05: "Acomodação publicada e visível nas buscas". A busca é o RF-12, fora desta tarefa.
- **Interpretação:** existe uma vitrine mínima (`/anuncios`, `/api/anuncios`) só para demonstrar o efeito de publicar e desativar. Ela mostra **apenas bairro e cidade** (RNF-05) e não filtra por data nem por capacidade.
- **Alternativa descartada:** não oferecer nada, deixando a pós-condição do UC05 sem como ser verificada.
