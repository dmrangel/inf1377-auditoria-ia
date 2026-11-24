# Auditoria: cancelamento e reembolso

- **IA auditora:** ChatGPT, no navegador, numa conversa nova e sem acesso à conversa de geração.
- **Prompt:** [`prompts/auditoria_chatgpt.md`](../prompts/auditoria_chatgpt.md).
- **Conversa completa:** [`interacao_ia/conversa_auditoria.md`](../interacao_ia/conversa_auditoria.md).

O relatório da IA vem primeiro, sem alteração de conteúdo. Depois dele está a verificação feita pelo grupo, porque o ChatGPT não conseguiu rodar o sistema (o ambiente dele não tinha Flask) e deixou alguns achados como suspeita.

---

## Veredito da auditoria

O cancelamento e o reembolso foram implementados parcialmente, mas a entrega não pode ser considerada integralmente conforme à ERS v1.2. O código atende a várias regras do UC12 no caminho principal, incluindo autorização das partes, cálculo básico dos reembolsos, histórico de status e tratamento de recusas simuladas do gateway. Entretanto, há falhas relevantes na integração com o fluxo existente: uma reserva cancelada pode voltar a ser confirmada por um PIX tardio, pagamentos aprovados em duplicidade podem resultar em valores não devolvidos e alterações no preço da acomodação afetam retroativamente o cálculo do reembolso. Também há problemas de segurança e lacunas de especificação. O parecer é parcial, porque faltam arquivos necessários para validar as interfaces e executar integralmente a suíte automatizada. Não considero a funcionalidade aprovada para uso financeiro real.

## 1. Arquivos ausentes e limitações

Foram recebidos os dez arquivos: ERS v1.2, cancelamento.py, database.py, models.py, README.md, app.py, email_service.py, payment_gateway.py, conftest.py e test_cancelamento.py.

Faltam arquivos referenciados pelo próprio código e pelo relatório:
- templates/base.html, minhas_reservas.html, reserva_detalhe.html, cancelar_reserva.html e _macros.html.
- templates/resumo.html, pagamento.html e confirmacao.html.
- static/js/cancelamento.js, static/css/style.css e os JavaScript das telas anteriores.
- tests/test_fluxo_reserva.py e requirements.txt.
Essas ausências impedem confirmar acessibilidade, comportamento visual, proteção do formulário completo e regressões das telas anteriores. Também impedem verificar toda a rastreabilidade declarada pela IA.

Execução: tentei iniciar os testes recebidos em uma estrutura temporária que reproduz os caminhos de importação. A coleta foi interrompida por ausência de werkzeug. Flask também não está instalado neste ambiente. Portanto, não há resultado válido de aprovação ou reprovação da suíte oficial.

Consegui executar testes isolados das funções de negócio, utilizando um banco SQLite temporário e substituindo apenas a dependência de geração de hash necessária à criação dos dados de demonstração. Os arquivos entregues não foram modificados.

## 2. Problemas encontrados

Critérios: Alta = quebra de regra de negócio, segurança relevante ou risco financeiro/de dados; Média = requisito parcialmente atendido; Baixa = robustez ou qualidade. “Executado” significa reproduzido no núcleo isolado, não na aplicação web completa.

| ID | Severidade | Problema e requisito afetado | Evidência e reprodução | Verificação |
|---|---|---|---|---|
| A-01 | Alta | PIX tardio reconfirma reserva cancelada. RF-20, RF-21, RF-19, RN-04, UC12 | app.py:413–425; models.py:275–283. Criar PENDENTE com PIX, cancelar e depois confirmar o pagamento. O código volta a reserva para CONFIRMADA. | Executado no núcleo isolado |
| A-02 | Alta | Reembolso considera somente o último pagamento aprovado. RF-27, UC12 e Seção 4.5.1 | cancelamento.py:216–221, 238–244. Criar reserva com dois pagamentos aprovados e cancelar: apenas um pagamento é reembolsado. | Executado |
| A-03 | Alta | Preço alterado após a reserva muda o reembolso tardio. RN-05, RF-18, RF-27 | cancelamento.py:224–233; models.py:16–41. Alterar acomodacao.precoNoite antes do cancelamento. O cálculo usa o preço atual, não o contratado. | Executado |
| A-04 | Alta | Usuário pode assumir a identidade de outra parte por rota de desenvolvimento, passando a ter permissão para cancelar reservas e solicitar reembolso. RF-21, RNF-11, segurança do UC12 | app.py:36–46, 653–676 aproximadamente; rota /api/dev/switch-user sem autenticação efetiva. Trocar a sessão para o ID de um anfitrião e chamar a API de cancelamento. | Suspeita pela leitura; impacto condicionado à exposição da rota |
| A-05 | Alta | Idempotência financeira não é durável nem vinculada explicitamente ao valor e ao pagamento original. RF-27, RNF-22, UC12 | payment_gateway.py:155–157, 171–212; cancelamento.py:321–325. Reiniciar o processo elimina o histórico de chaves; uma nova solicitação pode produzir outro estorno. O risco depende do comportamento do gateway real. | Suspeita pela leitura |
| A-06 | Média | Falha de e-mail pode ser apresentada como notificação concluída. UC12 passo 5, Seção 3.4 | cancelamento.py:389–423. A exceção é capturada, mas mensagem_resultado afirma que a outra parte foi notificada. | Suspeita pela leitura |
| A-07 | Média | Notificações push não são implementadas. Seção 3.4 | email_service.py:91–175; README §8.7 reconhece ausência. Só há registro de mensagens de e-mail. | Confirmado por leitura |
| A-08 | Média | Garantia de reembolso diante de falha do gateway e banco não está demonstrada de ponta a ponta. RF-27, UC12 | cancelamento.py:303–384. A transação SQLite protege o banco, mas não torna atômica a operação no gateway externo. Uma falha após um estorno aceito exige reconciliação. | Suspeita pela leitura |
| A-09 | Média | Comportamento de cancelamento durante a estadia não considera diárias já utilizadas ou repasse ao anfitrião. RN-05, RN-08, UC12 | cancelamento.py:94–149, 173–179. A regra aplica 50% de todas as diárias até o check-out. A ERS não detalha esse cenário. | Confirmado por leitura, mas é sobretudo lacuna da ERS |
| A-10 | Baixa | Garantias de cobertura e testes não verificadas. RNF-15 | README §8.5 declara 86% de cobertura; não há relatório de cobertura anexado, e a execução completa não foi possível. | Não verificável |

### Reprodução financeira de A-03

O experimento isolado produziu:
Reembolso tardio — mesma reserva, antes e depois de alterar o preço cadastrado
Preço anterior: R$ 500/noite
R$ 500,00

Preço posterior: R$ 800/noite
R$ 800,00

O valor originalmente pago pela reserva era R$ 1.140,00. Mesmo sem alterar a reserva ou seu pagamento, a prévia mudou de R$ 500,00 para R$ 800,00.

Isso demonstra que o cálculo não está preservando a base econômica da contratação. A diferença poderia ser ainda mais prejudicial se o preço diminuísse.

### Reprodução de A-01 e A-02

Em A-01, observei exatamente esta sequência no núcleo:
PENDENTE
CANCELADA
CONFIRMADA

Última transição causada pela confirmação tardia do pagamento PIX.
Como validar_disponibilidade_e_regras ignora reservas canceladas, as datas podem ter sido disponibilizadas para outra pessoa antes da reconfirmação. Isso cria risco de dupla reserva.

Em A-02, o experimento gerou dois pagamentos aprovados de R$ 900,80 e apenas uma operação REEMBOLSADO de R$ 900,80. Permaneceram dois registros APROVADO. O código não demonstra como resolver o excedente financeiro.

## 3. Rastreabilidade dos requisitos

| Requisito | Avaliação | Justificativa |
|---|---|---|
| RF-21 — cancelamento pelo hóspede/anfitrião | Parcial | Verificação correta das partes na função central, mas rota de troca de identidade compromete segurança se exposta |
| RF-25 — status de pagamentos | Parcial | Registra linha REEMBOLSADO, porém não protege adequadamente estados posteriores |
| RF-27 — processar reembolso | Parcial | Cálculo e solicitação existem; há problemas com múltiplos pagamentos, alteração de preço e falhas externas |
| RN-05 — política das 48 horas | Parcial | Cálculo básico corresponde à interpretação documentada; falta preservar o valor histórico |
| UC12 passos 1–3 | Não verificável integralmente | Backend existente; templates ausentes |
| UC12 passo 4 | Parcial | Cancelamento e solicitação são implementados, mas não há garantia transacional ponta a ponta |
| UC12 passo 5 | Parcial | E-mail simulado enviado, sem push e com possível mensagem incorreta em falha |
| UC12 fluxo 2a | Atendido no núcleo | Cancelamento pelo anfitrião calcula reembolso integral |
| RN-04 | Parcial na integração | Expiração implementada, mas PIX posterior pode reverter o cancelamento |
| RF-19 | Parcial na integração | Liberação de datas funciona; reconfirmação posterior pode provocar conflito |
| RF-28 | Parcial | Comprovante simulado para reembolso, sem garantia de entrega |
| RNF-05* | Parcialmente sustentado | Endereço ocultado fora de CONFIRMADA, mas reconfirmação indevida pode revelá-lo novamente |
| RNF-08 | Sustentado na parte auditada | Estorno usa txid e não requer armazenar número/CVV |
| RNF-11 | Parcial | Autorização local existe, mas identidade simulada pode ser assumida |
| RNF-15 | Não verificável | Não foi possível medir cobertura |
| RNF-19 | Parcialmente sustentado | Registros não são apagados pelo cancelamento; retenção por cinco anos não é demonstrada |
| RNF-22 | Parcial | Históricos registrados, mas transições indevidas continuam possíveis |

## 4. Confronto com o relatório da IA geradora

O README não é inteiramente enganoso: ele reconhece várias limitações importantes, inclusive o PIX tardio, o pagamento duplicado e a mudança de preços. Entretanto, algumas afirmações excedem o que foi demonstrado.

| Afirmação da IA | Parecer |
|---|---|
| “35 passam e 1 é xfail” | Não verificado. Há testes parametrizados compatíveis com a contagem declarada, mas não foi possível executar a suíte inteira. |
| “86% de cobertura total e 99% em cancelamento.py” | Não verificado. Não foram fornecidos resultados de execução nem relatório de cobertura. |
| “Tudo acontece numa única transação” | Impreciso. A transação é do SQLite; a chamada ao gateway está fora de sua garantia atômica. |
| “Nunca fica uma reserva CANCELADA sem reembolso devido” | Não garantido. Casos de pagamentos múltiplos e estados posteriores não estão resolvidos. |
| “A mesma chave evita estorno em dobro” | Alegação excessiva. A implementação simulada guarda chaves apenas na memória do processo. |
| “As seções 1 a 7 não mudaram de comportamento” | Não demonstrado. O código anterior integral e sua suíte não foram entregues. A integração apresenta falha no PIX. |
| “Acesso apenas às partes” | Verdadeiro para a validação local, mas insuficiente se a rota de troca de usuários permanecer acessível. |
| “A lacuna do PIX é conhecida e documentada” | Correto. Há teste marcado xfail e descrição explícita no README. |
| “Push não implementado” | Correto. O relatório reconhece a ausência. |

O ponto mais importante é que documentar uma falha não equivale a atender ao requisito. O xfail é uma boa ferramenta de transparência, mas não transforma a interação com o PIX em comportamento conforme.

## 5. O que a IA geradora acertou

A implementação contém decisões tecnicamente positivas que merecem reconhecimento:
1. Separação de responsabilidades: cancelamento.py concentra regras de negócio; app.py expõe as rotas; serviços externos são simulados separadamente.
2. Autorização no núcleo: papel_do_usuario verifica hóspede e anfitrião vinculados à reserva, em vez de confiar somente em botões da interface.
3. Pré-condições do UC12: impede cancelar reservas já CANCELADA ou CONCLUIDA.
4. Cálculo do limite exato das 48 horas: usa uma condição inclusiva coerente com a interpretação registrada.
5. Cancelamento de PENDENTE sem pagamento aprovado: não chama o serviço de estorno desnecessariamente.
6. Registro de histórico: adiciona transições de reserva e pagamento com identificação do responsável.
7. Tratamento de indisponibilidade e recusa simuladas: não registra o cancelamento no banco quando o gateway informa falha.
8. Prevenção de cancelamento duplo: utiliza BEGIN IMMEDIATE, controle de estado e chave de idempotência simulada.
9. Revalidação do valor exibido: evita aceitar silenciosamente um reembolso diferente daquele mostrado ao usuário.
10. Reconhecimento de ambiguidades: o README explica decisões e alternativas descartadas, permitindo ao auditor distinguir escolhas de implementação de requisitos explícitos.
Esses acertos sustentam a avaliação de que o fluxo básico foi efetivamente desenvolvido, não apenas descrito.

## 6. Lacunas da própria ERS

Esses pontos não devem ser tratados automaticamente como descumprimentos da IA. A especificação precisa ser complementada antes de uma avaliação contratual definitiva.

| ID | Lacuna | Requisito sugerido |
|---|---|---|
| L-01 | Horário de check-in e fuso para contar as 48 horas | Definir horário, fuso e inclusividade do prazo de cancelamento |
| L-02 | Base histórica de cálculo dos 50% | Persistir valor das diárias e taxa aplicáveis no instante da contratação; reembolso não pode depender de preço atualizado |
| L-03 | PIX liquidado após cancelamento | Proibir reconfirmação; registrar pagamento recebido fora de ordem e definir estorno ou conciliação |
| L-04 | Múltiplos pagamentos aprovados | Definir tratamento de cobranças duplicadas e restituição do excedente |
| L-05 | Cancelamento durante estadia | Definir se é permitido, diárias elegíveis e efeito de noites consumidas |
| L-06 | Repasse já realizado ao anfitrião | Definir responsabilidade, recuperação de valores e saldo necessário ao reembolso |
| L-07 | Gateway aceita estorno, mas banco local falha | Exigir reconciliação financeira, idempotência persistente e recuperação após interrupção |
| L-08 | Falha na notificação | Definir retentativas, registro de entrega e comportamento da interface |
| L-09 | Pagamento e estorno em processamento | Introduzir estados operacionais suficientes para representar operações assíncronas e falhas |
| L-10 | Uma pessoa é simultaneamente hóspede e anfitriã | Determinar qual papel governa a política de cancelamento |

A decisão de permitir cancelamento durante a estadia e conceder 50% das diárias não é necessariamente uma violação literal da RN-05. É uma interpretação possível de uma regra insuficiente. O risco financeiro, porém, precisa ser resolvido na especificação antes de adotar essa política.

## 7. Conclusão e prioridade

**Resultado por severidade:** 10 constatações (Alta 5, Média 4, Baixa 1).

A prioridade técnica seria impedir alterações de uma reserva cancelada por webhooks posteriores, preservar os valores contratados para cálculos financeiros e garantir a conciliação de todos os pagamentos aprovados. Também é indispensável remover ou restringir efetivamente os mecanismos de identidade simulada fora de um ambiente controlado de demonstração.

Veredito final: entrega parcialmente conforme, com falhas graves e validação incompleta. Os requisitos centrais do cancelamento estão representados em código, mas a integração financeira não preserva todas as invariantes necessárias. Para concluir a auditoria da entrega completa, é necessário receber os arquivos de interface e a suíte anterior listados na Seção 1, além de conseguir executar o projeto com suas dependências.


---

# Verificação do grupo

O ChatGPT recebeu 10 arquivos e não pôde executar a suíte. O grupo rodou o projeto completo e o script [`verificacoes/verificacao_grupo.py`](verificacoes/verificacao_grupo.py), que usa um banco temporário e nunca o banco do app.

```bash
cd alunos/pedro-loschi
python auditoria/verificacoes/verificacao_grupo.py
cd codigo && python -m pytest -q
```

## Resultado da execução

- **Suíte completa:** 50 testes aprovados e 1 falha esperada (`xfail`). Os 15 testes originais do fluxo de reserva passam sem alteração.
- **Cobertura** (`coverage run -m pytest`): 99% em `cancelamento.py` e 86% no código da aplicação, sem contar os testes. A afirmação da IA geradora se confirma, e a RNF-15 (70%) é atendida.

## Julgamento de cada achado

| ID | Julgamento do grupo | Como |
|---|---|---|
| A-01 | **Confirmado.** O próprio teste `xfail` da IA geradora reproduz a reconfirmação da reserva cancelada por um PIX tardio. A IA geradora documentou o problema (AMB-06), mas, como diz o auditor, documentar não é atender. | `tests/test_cancelamento.py`, teste marcado `xfail` |
| A-02 | **Confirmado pela leitura** e já admitido pela IA geradora (AMB-08). `_pagamento_a_reembolsar()` só pega o pagamento APROVADO mais recente. | `cancelamento.py:216` |
| A-03 | **Confirmado executando.** Num cancelamento tardio, a mesma reserva devolve R$ 450,00 antes e R$ 900,00 depois de o anfitrião dobrar o preço por noite. Em `_valor_diarias()`, o valor das diárias é recalculado com o preço atual porque a tabela `reserva` do B.4 só guarda o `valorTotal` (AMB-09). Com isso, o anfitrião pode alterar o valor devolvido depois da compra. | `verificacao_grupo.py`, bloco A-03 |
| A-04 | **Confirmado executando.** O auditor deixou como suspeita. Um usuário sem relação com a reserva recebe HTTP 403 ao tentar cancelar, mas depois de chamar `/api/dev/switch-user` com o id do hóspede, sem senha, cancela a reserva e dispara o reembolso (HTTP 200, reserva CANCELADA). A rota veio do código do Davi (achado B04 da rodada 2), mas o cancelamento aumenta o dano: agora ela permite desfazer reservas e mover dinheiro. | `verificacao_grupo.py`, bloco A-04 |
| A-05 | **Procede em parte.** As chaves de idempotência ficam num dicionário em memória do gateway simulado e se perdem ao reiniciar. Num gateway real, a idempotência seria do próprio gateway, mas o código não guarda a chave no banco para reenviar a mesma. Mantemos como risco, com severidade média. | `services/payment_gateway.py` |
| A-06 | **Confirmado pela leitura.** Se o envio de e-mail falhar, `cancelar_reserva()` grava `erro_notificacao`, mas `mensagem_resultado()` sempre diz "foi notificado por e-mail". | `cancelamento.py:401-423` |
| A-07 | **Procede.** Push não foi implementado, e a IA geradora já tinha declarado isso. | `codigo/README.md` §8.7 |
| A-08 | **Procede como risco de arquitetura.** O estorno no gateway e a gravação no banco não são atômicos entre si. | `cancelamento.py:303-384` |
| A-09 | **É lacuna da ERS, não erro da IA.** A ERS não diz se dá para cancelar durante a estadia. A IA permitiu e registrou a decisão (AMB-05). | ERS, RN-05 e UC12 |
| A-10 | **Não procede.** O grupo rodou a suíte e a cobertura, e as duas afirmações da IA geradora se confirmaram. | resultado acima |

## Pontos em que o grupo discorda do auditor

- **Arquivos "faltando":** os templates, o JavaScript e o `test_fluxo_reserva.py` existem no repositório. Eles não foram anexados para respeitar o limite de anexos do ChatGPT. As ressalvas da seção 1 do relatório vêm desse recorte, e não de falhas da entrega.
- **A-10:** era "não verificável" para o auditor, mas foi verificado pelo grupo e está correto.
- **A-05:** a severidade alta pressupõe um gateway real. Com o gateway simulado que o prompt autorizou, o grupo classifica como média.

## Contagem final

Pelo julgamento do grupo, ficam 8 problemas válidos: **4 de severidade alta** (A-01, A-02, A-03 e A-04), **4 de severidade média** (A-05, A-06, A-07 e A-08). O A-09 é lacuna da ERS e o A-10 foi descartado.
