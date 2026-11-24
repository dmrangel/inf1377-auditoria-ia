# Relatório: Avaliação de Estadia

Funcionalidade acrescentada ao fluxo de reserva, pagamento e confirmação da Plataforma de Hospedagem, a partir da ERS v1.2: seção 4.6 (RF-29 a RF-32), RN-06 e casos de uso UC18 (Avaliar estadia) e UC19 (Avaliar hóspede). Ela começa quando a reserva passa para `CONCLUIDA` e o sistema convida hóspede e anfitrião a avaliar, e termina quando as avaliações são publicadas e a nota média da acomodação é atualizada.

**Situação:** 51 testes automatizados aprovados (15 originais do fluxo de reserva, sem alteração, e 36 novos), com cobertura de 88% do código da aplicação. Como rodar e o roteiro manual de cada cenário estão no [README.md](README.md), seções 2, 3 e 5.

**Como ler a coluna "Como testar":**
- `test_...` é um teste de `tests/test_avaliacao.py`. Todos rodam com `pytest -v`.
- Os cenários **A a G** são os dados de exemplo criados por `seed_avaliacoes.py`, descritos no README, seção 5.3.
- Usuários de teste (seletor no topo da página): Lucas (hóspede), Ana (hóspede), Carlos (anfitrião de Copacabana e do Chalé) e Mariana (anfitriã de Ipanema).

---

## 1. Tabela de rastreabilidade

### 1.1 Implementados

| ID (ERS) | O que pede | Onde foi implementado | Como testar |
|---|---|---|---|
| **4.4.2, passo 3** | "A data de check-out passa → o sistema muda a reserva para CONCLUIDA." | `avaliacoes.py`: `concluir_reservas_encerradas()`. Chamada por `contar_pendentes()` (a cada tela, para o link do cabeçalho), `situacao_para_usuario()`, `registrar_avaliacao()`, `painel_do_usuario()` e `avaliacoes_publicadas_acomodacao()`. | `test_conclusao_automatica_apos_checkout_com_convite_e_auditoria`, `test_conclusao_so_depois_do_dia_do_checkout`, `test_pendente_e_cancelada_nunca_viram_concluida`. Manual: cenário A (reserva #2) vira CONCLUIDA no primeiro acesso. |
| **RF-20** (status CONCLUIDA) | Controlar o status PENDENTE, CONFIRMADA, CANCELADA e CONCLUIDA. | O status CONCLUIDA, que antes não era usado, agora é aplicado por `avaliacoes.py`: `concluir_reservas_encerradas()`. | Os mesmos testes da linha anterior. |
| **4.6.2, passo 1** / **UC18-UC19, passo 1** | O sistema convida hóspede e anfitrião a avaliar após o check-out. | `avaliacoes.py`: `concluir_reservas_encerradas()` envia o convite. `services/email_service.py`: `EmailService.send_review_invitation()`. `rotas_avaliacao.py`: `injetar_pendencias()` (contador do link "Avaliações" em `templates/base.html`). `templates/avaliacoes_pendentes.html`. | `test_conclusao_automatica_apos_checkout_com_convite_e_auditoria`, `test_tela_minhas_avaliacoes_lista_convites`. Manual: como Lucas, `/avaliacoes` e os e-mails `CONVITE_AVALIACAO` em `/api/dev/emails`. |
| **4.6.2, passo 2** / **UC18-UC19, passos 2 e 3** | O usuário envia nota e comentário; o sistema grava com `dataAvaliacao`. | `rotas_avaliacao.py`: `view_avaliar()` e `api_registrar_avaliacao()` (`POST /api/reservas/<id>/avaliacoes`). `avaliacoes.py`: `registrar_avaliacao()`. `templates/avaliar.html` e `static/js/avaliacao.js`. | `test_caminho_feliz_hospede_e_anfitriao_avaliam`. Manual: cenário A, Lucas e depois Carlos avaliam a reserva #2. |
| **4.6.2, passo 3** | Ambos avaliam ou o prazo termina → as avaliações são publicadas. | `avaliacoes.py`: condição `_SQL_PUBLICADA`, usada por `resumo_notas_acomodacao()`, `resumo_notas_hospede()`, `avaliacoes_publicadas_acomodacao()` e `painel_do_usuario()`; e `situacao_para_usuario()` (só mostra a avaliação da outra parte depois de publicada). | `test_publicacao_quando_a_segunda_parte_avalia`, `test_publicacao_pelo_fim_do_prazo`, `test_avaliacao_oculta_nao_aparece_na_pagina_publica`. Manual: cenários B e D. |
| **4.6.1** (Reserva 1 → 0..2 Avaliacao) | Até duas avaliações por reserva: hóspede sobre a acomodação e anfitrião sobre o hóspede. | `avaliacoes.py`: `papel_do_usuario()` define o papel pelo autor; `UNIQUE(reserva_id, autor_id)` na tabela `avaliacao` (`database.py`: `init_db()`). | `test_caminho_feliz_hospede_e_anfitriao_avaliam`, `test_rf31_uma_avaliacao_por_participante`. |
| **RF-29** | Nota de 1 a 5 e comentário opcional. | `avaliacoes.py`: `_validar_nota()` e `_validar_comentario()`. `database.py`: `CHECK (nota BETWEEN 1 AND 5)`. `static/js/avaliacao.js` (validação de conveniência na tela). | `test_rf29_nota_invalida` (0, 6, -1, 4.5, "abc", "", True, None, lista), `test_rf29_nota_em_texto_e_comentario_vazio`, `test_rf29_comentario_longo_ou_invalido`, `test_check_da_nota_no_banco`, `test_corpo_que_nao_e_json`. Manual: enviar o formulário sem escolher estrelas. |
| **RF-30** | Avaliar somente reservas com status CONCLUIDA. | `avaliacoes.py`: `_bloqueio()`. | `test_rf30_reserva_nao_concluida` (reserva #1, como Ana), `test_rf30_reserva_cancelada` (cenário E, reserva #6). |
| **RF-31** | Uma avaliação por participante em cada reserva. | `avaliacoes.py`: `_bloqueio()` e o tratamento de `sqlite3.IntegrityError` em `registrar_avaliacao()` (requisições simultâneas). Restrição `UNIQUE(reserva_id, autor_id)`. A API responde 409. | `test_rf31_uma_avaliacao_por_participante`. Manual: cenário B como Mariana (`/reservas/3/avaliar` não mostra o formulário). |
| **RF-32** | Recalcular a nota média da acomodação a cada nova avaliação. | `avaliacoes.py`: `resumo_notas_acomodacao()` (média calculada na consulta, só com avaliações publicadas); `registrar_avaliacao()` devolve a média atualizada. | `test_caminho_feliz_hospede_e_anfitriao_avaliam` (5,0 → 4,0), `test_publicacao_quando_a_segunda_parte_avalia` (4,0 → 4,5), `test_publicacao_pelo_fim_do_prazo`. |
| **RF-15** | Exibir a nota média e os comentários das avaliações de cada acomodação. | `rotas_avaliacao.py`: `view_avaliacoes_acomodacao()`, `api_avaliacoes_acomodacao()` e `resumo_notas_global()` (função de template usada na Tela 1). `avaliacoes.py`: `avaliacoes_publicadas_acomodacao()`. `templates/avaliacoes_acomodacao.html` e `templates/resumo.html`. | `test_tela_avaliacoes_da_acomodacao_e_tela_1`, `test_visitante_ve_pagina_publica_da_acomodacao`. Manual: `/acomodacoes/1/avaliacoes` e a linha "★ 4,0 · ver avaliações" na Tela 1. |
| **RN-06** / **UC18-UC19, fluxo alternativo 1a** | Prazo de 14 dias após o check-out; depois dele não se avalia mais. | `avaliacoes.py`: `prazo_final()`, `_bloqueio()`, `_SQL_PENDENTES` (some da lista quando vence); prazo e dias restantes em `templates/avaliar.html` e `templates/avaliacoes_pendentes.html`. | `test_rn06_ultimo_dia_ainda_vale` (cenário C), `test_rn06_prazo_encerrado` (cenário D como Carlos, e cenário C no dia seguinte). |
| **UC18** (Avaliar estadia) | O hóspede avalia a estadia. | `rotas_avaliacao.py`: `view_avaliar()`; `avaliacoes.py`: `situacao_para_usuario()` com papel `HOSPEDE`; `templates/avaliar.html`. | `test_caminho_feliz_hospede_e_anfitriao_avaliam`, `test_tela_avaliar_mostra_formulario_ou_bloqueio`. |
| **UC19** (Avaliar hóspede) | O anfitrião avalia o hóspede. | Mesmas funções, com papel `ANFITRIAO`; `avaliacoes.py`: `resumo_notas_hospede()` (nota média do hóspede mostrada ao anfitrião). | `test_caminho_feliz_hospede_e_anfitriao_avaliam`, `test_nota_media_do_hospede_para_o_anfitriao`. |
| **UC18-UC19, pré-condição** | "Reserva está CONCLUIDA e o usuário ainda não a avaliou." | `avaliacoes.py`: `_bloqueio()`. | Testes de RF-30 e RF-31. |
| **UC18-UC19, pós-condição** | "Avaliação registrada e nota média atualizada." | `avaliacoes.py`: `registrar_avaliacao()`. | `test_caminho_feliz_hospede_e_anfitriao_avaliam`. |
| **B.4: tabela `avaliacao`** | `id`, `reserva_id`, `autor_id` (único junto com `reserva_id`), `nota`, `comentario`, `dataAvaliacao`. | `database.py`: `init_db()`. A tabela já existia; só foi acrescentado o `CHECK` da nota. Nenhuma coluna nova. | `test_check_da_nota_no_banco`, `test_rf31_uma_avaliacao_por_participante`. |
| **RNF-22** | Mudança de status de reserva registrada com data, hora e responsável. | `avaliacoes.py`: `concluir_reservas_encerradas()` grava CONFIRMADA → CONCLUIDA em `historico_status_reserva` com `responsavel_id` nulo (mudança automática). | `test_conclusao_automatica_apos_checkout_com_convite_e_auditoria`. |
| **RNF-05\*** | Endereço exato só após a confirmação. | `models.py`: `obter_reserva_completa()` libera o endereço para CONFIRMADA e CONCLUIDA; `app.py`: `view_confirmacao()` aceita CONCLUIDA. As telas de avaliação mostram só bairro e cidade. | `test_confirmacao_aceita_reserva_concluida_com_endereco`, `test_confirmacao_continua_bloqueando_cancelada`. Manual: `/confirmacao/2` como Lucas. |
| **RNF-11** (por analogia) | Apenas o dono acessa os dados. Aplicado às avaliações: só os participantes da reserva veem a tela e avaliam, verificado no servidor. | `avaliacoes.py`: `papel_do_usuario()`, `situacao_para_usuario()` e `registrar_avaliacao()` (403); `rotas_avaliacao.py`: `login_obrigatorio()` (401). | `test_quem_nao_participa_nao_avalia`, `test_sem_login_e_reserva_inexistente`, `test_anfitriao_hospedado_na_propria_acomodacao`. |
| **Seção 3.4** | API REST com dados em JSON; notificações por e-mail. | `rotas_avaliacao.py`: `api_registrar_avaliacao()` e `api_avaliacoes_acomodacao()`; `static/js/avaliacao.js` usa `fetch`. | `test_rf29_*`, `test_sem_login_e_reserva_inexistente`, `test_tela_avaliacoes_da_acomodacao_e_tela_1`. |
| **Seção 3.1** | Botão de ajuda em todas as telas e mensagens de erro em linguagem simples. | `templates/base.html` (seção 4 do modal de ajuda); mensagens em `avaliacoes.py`: `_bloqueio()`, `_validar_nota()`, `_validar_comentario()`. | Manual: botão "Ajuda" em `/avaliacoes`; mensagens nos cenários de erro. |
| **2.3** (visitante vê anúncios) | Pessoa não cadastrada pode ver anúncios. | `rotas_avaliacao.py`: `view_avaliacoes_acomodacao()` não exige login. | `test_visitante_ve_pagina_publica_da_acomodacao`. |
| **RNF-14** | WCAG 2.1 nível AA. | Nota em botões de rádio com rótulo de texto, foco visível e mensagens com `aria-live`/`role="alert"` em `templates/avaliar.html`; cores com contraste mínimo de 4,5:1 nos estilos acrescentados a `static/css/style.css`. | Manual: escolher a nota só com o teclado (Tab e setas). Não houve auditoria com ferramenta (veja 1.2). |
| **RNF-16** | Interface de 360 px a 1920 px. | `static/css/style.css` (estilos das avaliações, com `@media (min-width: 600px)`). | Verificado no navegador a 360 px, sem rolagem horizontal, em `/avaliacoes` e `/acomodacoes/1/avaliacoes`. |
| **RNF-15** | Cobertura de testes automatizados de pelo menos 70%. | `tests/test_avaliacao.py`, `.coveragerc`. | `pytest --cov=. --cov-report=term`: 88% do código da aplicação. |

### 1.2 Relevantes e não implementados

| ID (ERS) | Motivo |
|---|---|
| **RF-33 / RN-07** (selo superhost) | Fora do escopo desta tarefa, por definição do enunciado. A nota média (RF-32) que o selo usaria já está disponível em `resumo_notas_acomodacao()`. |
| **TBD-05** (resposta pública à avaliação) | Item em aberto na própria ERS. |
| **Seção 2.3** (administrador modera avaliações) | A ERS não especifica nenhum requisito de moderação de avaliações; os RF-34 a RF-36 tratam de denúncias de anúncios e usuários. |
| **Seção 3.4** (notificação por push) | Não existe aplicativo móvel no projeto; o convite é feito por e-mail simulado e pelo contador no cabeçalho (AV-02). |
| **Seção 3.1 / RF-11** (painel do anfitrião com anúncios, reservas e avaliações) | O painel completo do anfitrião é de outra funcionalidade. A parte de avaliações está em `/avaliacoes`, que mostra ao anfitrião os convites, as avaliações que ele escreveu e as que recebeu. |
| **RF-16** (ordenar resultados por nota) | Depende da busca (seção 4.3), que não existe neste projeto. |
| **RNF-17** (LGPD: consultar, exportar e excluir dados pessoais) | Não há tela de dados pessoais no projeto. As avaliações escritas por um usuário ficam em `/avaliacoes`, mas não há exportação nem exclusão. |
| **RNF-14** (auditoria formal WCAG) | Foram aplicadas boas práticas, mas não houve verificação com ferramenta ou leitor de tela. |
| **RNF-20** (outros idiomas) | Os textos das telas estão escritos direto nos templates em português, como no restante do código. |
| **RNF-07, RNF-09, RNF-10** (senha, sessão, bloqueio de login) | O enunciado permite um usuário de teste já autenticado; as regras de permissão são verificadas no servidor. |
| **Seção 3.4** (HTTPS com TLS 1.2) e **RNF-21** (backup) | Dependem da implantação, não do código da aplicação rodando localmente. |

### 1.3 Alterações no fluxo de reserva

A avaliação não muda o comportamento das reservas PENDENTE, CONFIRMADA e CANCELADA, e os 15 testes originais passam sem alteração. A lista completa está no README, seção 9. Em resumo:

- **Tela 3 aceita CONCLUIDA** (pedido da equipe): `app.py`, `view_confirmacao()`; `models.py`, `obter_reserva_completa()`; `templates/confirmacao.html`.
- **`/pagamento/<id>` de reserva CONCLUIDA redireciona para a Tela 3**: `app.py`, `view_pagamento()`. Fora do plano aprovado; sem isso, a tela de pagamento apareceria para uma reserva já paga.
- **`templates/base.html`**: a barra de 3 passos só aparece nas telas que definem `step`, e o cabeçalho ganhou o link "Avaliações".
- **`templates/resumo.html`**: só exibe a nota média.
- **Problema encontrado e não corrigido:** sem usuário conectado, `/resumo` redireciona para si mesmo em laço. Já existia antes e corrigir mudaria o fluxo de reserva. As telas de avaliação respondem 401 com uma página explicativa, em vez de redirecionar para `/resumo`.

---

## 2. Ambiguidades e decisões

Cada item traz o trecho da ERS, a interpretação adotada e a alternativa descartada. Os identificadores AV-01 a AV-17 são os mesmos citados nos comentários do código e no README.

**AV-01: Quando e como a reserva passa para CONCLUIDA**
- **Trecho:** 4.4.2, passo 3: *"A data de check-out passa → o sistema muda a reserva para CONCLUIDA."*
- **Problema:** não diz se a reserva conclui no dia do check-out ou depois, qual mecanismo faz a mudança, nem de quais status ela parte.
- **Adotada:** conclui quando a data de hoje é **posterior** ao check-out ("a data passa"). A verificação é sob demanda, no mesmo padrão da expiração de 30 minutos (RN-04) do código existente, e só parte de CONFIRMADA. PENDENTE e CANCELADA nunca viram estadia.
- **Descartadas:** concluir no próprio dia do check-out, quando o hóspede ainda pode estar no imóvel; e um agendador em segundo plano, que exigiria dependência nova e impediria controlar o tempo nos testes.

**AV-02: O que é "convidar" a avaliar**
- **Trecho:** 4.6.2, passo 1: *"o sistema convida hóspede e anfitrião a avaliar"*. A seção 3.4 diz que notificações vão *"por e-mail e por push no aplicativo móvel"*.
- **Adotada:** um e-mail simulado para cada parte, enviado uma única vez, no momento da conclusão, mais o contador no link "Avaliações" do cabeçalho.
- **Descartada:** push, porque não existe aplicativo móvel.

**AV-03: Publicação das avaliações**
- **Trecho:** 4.6.2, passo 3: *"Ambos avaliam ou o prazo termina → o sistema publica as avaliações."*
- **Problema:** nenhum RF trata da publicação, e a tabela `avaliacao` (B.4) não tem coluna para ela.
- **Adotada:** a avaliação fica oculta para a outra parte e para o público até as duas partes avaliarem ou o prazo terminar. O estado "publicada" é calculado a partir dos dados. O autor vê a própria avaliação como "aguardando"; a outra parte só sabe que ela existe.
- **Descartada:** criar a coluna `publicada`, fugindo do projeto de tabelas.

**AV-04: RF-32 contra a publicação (contradição)**
- **Trecho:** RF-32: *"recalcular a nota média da acomodação a cada nova avaliação"*, contra o passo 3 da 4.6.2.
- **Problema:** recalcular no envio coloca na média uma nota ainda oculta, e a variação da média revela o seu valor.
- **Adotada:** a média só considera avaliações publicadas e muda quando cada uma é publicada.
- **Descartada:** a leitura literal do RF-32.

**AV-05: Onde fica a nota média**
- **Trecho:** RF-15 e RF-32 citam a nota média da acomodação; a tabela `acomodacao` (B.4) não tem coluna para ela.
- **Adotada:** calcular com `AVG` na consulta, sem guardar, o que a mantém sempre atualizada.
- **Descartada:** criar a coluna `notaMedia`.

**AV-06: Qual nota média o UC19 atualiza**
- **Trecho:** UC18 e UC19 têm uma única descrição, com a pós-condição *"Avaliação registrada e nota média atualizada."*
- **Problema:** a ERS só define nota média da acomodação, e a tabela `usuario` não tem coluna de nota.
- **Adotada:** a média do hóspede (notas publicadas dadas por anfitriões) é calculada e mostrada ao anfitrião na tela "Avaliar hóspede".
- **Descartada:** não ter média para o hóspede, deixando a pós-condição do UC19 sem efeito.

**AV-07: Quem é avaliado, e o anfitrião hospedado na própria acomodação**
- **Trecho:** a tabela `avaliacao` não indica quem é avaliado. A seção 2.3 diz que *"Um mesmo usuário pode atuar como hóspede e como anfitrião"*, e o fluxo de reserva não impede o anfitrião de reservar a própria acomodação.
- **Adotada:** o avaliado é deduzido do autor: se o autor é o hóspede da reserva, a avaliação é da acomodação (UC18); se é o anfitrião, é do hóspede (UC19). Quando hóspede e anfitrião são a mesma pessoa, a avaliação é recusada, ninguém é convidado e a reserva não aparece entre as pendentes (cenário G).
- **Descartada:** criar a coluna `tipo` em `avaliacao`.

**AV-08: Comentário obrigatório ou opcional (contradição), e tamanho**
- **Trecho:** UC18-UC19, passo 2: *"O usuário informa a nota (1 a 5) e um comentário."* RF-29: *"comentário opcional"*.
- **Adotada:** opcional, porque o requisito prevalece sobre o passo do caso de uso. Texto só com espaços vira nulo. Limite de 1000 caracteres, que a ERS não define.
- **Descartada:** comentário obrigatório.

**AV-09: Nota inteira ou fracionada**
- **Trecho:** RF-29: *"nota de 1 a 5"*.
- **Adotada:** só inteiros de 1 a 5, verificados no servidor e por `CHECK` no banco.
- **Descartada:** meias estrelas.

**AV-10: Como contar os 14 dias**
- **Trecho:** RN-06: *"O prazo para avaliar uma estadia é de 14 dias após o check-out."* O check-out não tem hora.
- **Adotada:** a avaliação é aceita até o fim do dia `checkOut + 14`, inclusive (cenário C).
- **Descartada:** 14 × 24 horas a partir de um horário que a ERS não define.

**AV-11: O prazo termina com uma avaliação só**
- **Trecho:** 4.6.2, passo 3, não trata o caso.
- **Adotada:** a única avaliação existente é publicada e entra na média (cenário D).
- **Descartada:** descartar a avaliação solitária ou mantê-la oculta para sempre.

**AV-12: Editar ou excluir avaliação**
- **Trecho:** a ERS não trata. RF-31 limita a uma avaliação por participante; TBD-05 deixa em aberto a resposta pública.
- **Adotada:** depois de enviada, a avaliação não pode ser alterada nem excluída. Resposta pública e moderação ficam fora do escopo.
- **Descartada:** permitir edição até a publicação, que exigiria regras que a ERS não define.

**AV-13: Acomodação sem avaliações**
- **Trecho:** RF-15 manda exibir a nota média, sem tratar o caso de não haver nenhuma.
- **Adotada:** a tela mostra "Sem avaliações". A média aparece com uma casa decimal e vírgula (4,5).
- **Descartada:** mostrar nota 0, que seria lida como avaliação péssima.

**AV-14: Formato da API e códigos de resposta**
- **Trecho:** seção 3.4: *"O cliente se comunica com o servidor por uma API REST com dados em JSON."*
- **Adotada:** envio por `fetch` com JSON, como no pagamento existente. As respostas seguem o padrão `{"sucesso", "mensagem"}` do código: 400 para regras de negócio, 401 sem login, 403 para quem não participa, 404 para reserva inexistente e 409 para avaliação repetida.
- **Descartada:** formulário HTML tradicional; e 422 para regras de negócio, que destoaria do código existente.

**AV-15: Endereço exato depois da estadia**
- **Trecho:** RNF-05\*: *"O endereço exato da acomodação só deve ser exibido ao hóspede após a reserva ser CONFIRMADA"*. A ERS não diz o que acontece depois de CONCLUIDA.
- **Adotada (decisão da equipe):** a reserva CONCLUIDA já foi confirmada, então a Tela 3 continua mostrando o endereço completo. As telas de avaliação mostram só bairro e cidade.
- **Descartada:** voltar a esconder o endereço depois do check-out, que era o comportamento implícito do código anterior.

**AV-16: Convite quando o prazo já terminou**
- **Trecho:** 4.6.2, passo 1, junto com a RN-06.
- **Problema:** como a conclusão é sob demanda, uma reserva pode ser concluída mais de 14 dias depois do check-out, se ninguém acessou o sistema nesse período.
- **Adotada:** a reserva é concluída, mas ninguém recebe convite, porque não há mais prazo para avaliar.
- **Descartada:** enviar um convite que levaria a uma tela de "prazo encerrado".

**AV-17: Auditoria das avaliações**
- **Trecho:** RNF-22: *"Toda mudança de status de reserva e de pagamento deve ser registrada com data, hora e responsável."*
- **Problema:** a regra não cita avaliações.
- **Adotada:** a mudança CONFIRMADA → CONCLUIDA é registrada em `historico_status_reserva`. A avaliação em si já guarda autor (`autor_id`) e data e hora (`dataAvaliacao`), e não muda depois de gravada, então não há histórico separado.
- **Descartada:** criar uma tabela de histórico de avaliações, fora do projeto de tabelas.
