# Auditoria do código gerado por IA: rodada 2

**Disciplina:** INF1377 – Engenharia de Requisitos
**Código auditado:** gerado pelo Gemini 3.8 Flash (High) no Antigravity, numa conversa única, a partir de `prompt_rodada2_antigravity.md` e do PDF da ERS v1.2
**Referência da auditoria:** ERS v1.2
**Auditor:** Claude (Opus 5.5)
**Data:** 10/11/2026

## 1. O que mudou entre as rodadas

O modelo foi o mesmo nas duas rodadas. O que mudou foi o processo:

| | Rodada 1 | Rodada 2 |
|---|---|---|
| Modelo | Gemini 3.8 Flash, trocado duas vezes no meio da conversa | Gemini 3.8 Flash (High), do início ao fim |
| Entrada | Prompt e ERS v1.2 num chat do navegador; o código voltou num documento único, depois gravado pelo Antigravity | Prompt e ERS v1.2 direto no Antigravity, que planejou e gravou o código na mesma conversa |
| Interação | Conversa da geração apagada por engano | Conversa completa em `interacao_ia/conversa_antigravity.md`: plano, "concordo, pode implementar" e pedido de resumo |
| Tamanho | cerca de 1.100 linhas | cerca de 3.700 linhas |

O grupo não deu nenhuma correção à IA durante a rodada 2: o plano foi aprovado como estava, para que o resultado pudesse ser comparado com a rodada 1.

## 2. Veredito

A rodada 2 é melhor que a rodada 1. Seis dos problemas da rodada 1 foram resolvidos, e o código segue o projeto de tabelas da ERS v1.2. Os problemas mais graves continuam no mesmo lugar: o aviso de pagamento do PIX. O webhook segue sem autenticação, aceita pagamentos para reservas já pagas e, pior que na rodada 1, reativa reservas canceladas, o que permite dois hóspedes no mesmo período. Para facilitar os testes, a IA também criou uma rota que deixa qualquer visitante assumir a identidade de outro usuário, o que anula o controle de acesso que ela mesma implementou.

Os problemas podem ser reproduzidos com `python auditoria/verificacoes.py`, que usa um banco temporário e também confere as correções.

## 3. Problemas da rodada 1 que foram corrigidos

| Rodada 1 | Situação na rodada 2 | Evidência |
|---|---|---|
| A05 Reserva expirada bloqueava as datas | Corrigido: a expiração roda antes de checar a disponibilidade | `verificacoes.py` |
| A06 0 ou −3 hóspedes aceitos | Corrigido em parte: mínimo de 1 hóspede; check-in no passado continua aceito (B06) | `verificacoes.py` |
| A03 Qualquer usuário via a confirmação de outro | Corrigido para usuários logados, mas reaberto pela rota de desenvolvimento (B04) | `verificacoes.py` |
| A08 Pagamento sem auditoria | Corrigido: as duas tabelas de histórico são preenchidas, com o id do responsável. O cartão ainda é gravado direto como APROVADO ou RECUSADO, sem passar por PROCESSANDO | `verificacoes.py`, `models.py` |
| A10 Testes falhavam na segunda execução | Corrigido: os 15 testes passam em execuções repetidas. Surgiu outro problema (B09) | duas execuções do `pytest` |
| A11 Anfitrião não era notificado | Corrigido: hóspede e anfitrião recebem e-mail | `verificacoes.py` |
| A12 QR Code gerado por serviço externo | Corrigido: SVG gerado localmente | `verificacoes.py` |
| A13 Banco fora do B.4 da v1.2 | Corrigido: `superhost` no usuário e tabelas de histórico | `verificacoes.py` |
| A01 e A02 Webhook sem autenticação e pagamento duplicado | **Continuam** (B01 e B02). O valor pago agora é conferido | `verificacoes.py` |
| A04 PIX pago fora do prazo | **Mudou e ficou pior** (B03) | `verificacoes.py` |

## 4. Problemas encontrados na rodada 2

| ID | Severidade | Problema | Requisito afetado | Evidência |
|:-:|:-:|---|---|---|
| B01 | Alta | O webhook `/api/webhook/pix` não exige assinatura. O próprio hóspede gera um PIX e chama o webhook com o valor da cobrança: a reserva é confirmada sem pagamento. | 3.4, RF-23 | B01: HTTP 200, reserva CONFIRMADA |
| B02 | Alta | O webhook não verifica se a reserva já foi paga. Cartão aprovado e depois um PIX gerado antes resultam em dois pagamentos APROVADO. A função `process_refund` existe no gateway, mas nunca é chamada. | RF-23, RF-27 | B02: 2 pagamentos APROVADO |
| B03 | Alta | Se o PIX é pago depois de a reserva expirar, o webhook muda a reserva de CANCELADA para CONFIRMADA sem verificar se as datas continuam livres. Se outro hóspede reservou o período nesse meio-tempo, os dois ficam confirmados. | RN-04, RF-19 | B03: duas reservas confirmadas no mesmo período |
| B04 | Alta | A rota `/api/dev/switch-user` está sempre ativa e não pede autenticação. Qualquer visitante assume a identidade de qualquer usuário, inclusive anfitriões, e vê a confirmação com endereço completo e telefone do anfitrião. | RNF-05, RNF-11 | B04: visitante vê o CEP da reserva do hóspede 1 |
| B05 | Média | `/api/pagamento/pix/gerar` e `/api/reservas/<id>/status` não verificam o dono da reserva. Outro usuário gera cobranças e acompanha o status de reservas alheias. As rotas de tela e de cartão verificam. | RNF-11 | B05: HTTP 200 nas duas rotas |
| B06 | Média | Reserva aceita com check-in no passado. | RN-01, RF-17 | B06 |
| B07 | Média | Formulário sem acomodação, id não numérico na URL e `reserva_id` inválido geram erro 500. Quando a conversão de número falha no formulário, a mensagem técnica do Python aparece ao usuário. | 3.1 (mensagens em linguagem simples) | B07: HTTP 500 nos três casos |
| B08 | Média | O mesmo aviso de PIX pode ser processado mais de uma vez: cada repetição registra um novo histórico e reenvia os e-mails ao hóspede e ao anfitrião. | RF-28, RNF-22 | B08: segundo aviso aceito, 4 e-mails |
| B09 | Média | Os testes chamam `init_db(force_recreate=True)`, que apaga o `hospedagem.db` do próprio app. Rodar o `pytest` destrói os dados da demonstração; com o servidor aberto no Windows, a exclusão pode falhar. | RNF-15 | execução do `pytest` apagou uma reserva criada antes dela |
| B10 | Baixa | O webhook abre a conexão com o banco fora de um bloco `try/finally`. Uma exceção no meio deixa a conexão aberta, o que na rodada 1 travou o banco (A09). | RNF-12 | `app.py`, função `api_webhook_pix` |
| B11 | Baixa | `secret_key` padrão fixa no código e `debug=True`. | Segurança geral | `app.py` linhas 21 e 520 |

## 5. Onde o relatório da IA exagerou

O `RESUMO_GERAL.md` afirma que o sistema "atende rigorosamente a todas as restrições da especificação". Os casos abaixo contradizem isso:

- **RNF-11 "Apenas hóspede dono pode acessar os dados da reserva".** Falso por causa de B04 e B05. O teste `test_rnf11_e_login_requerido` só cobre as rotas que de fato verificam.
- **"15 testes automatizados com 100% de sucesso".** Os testes passam, mas nenhum cobre webhook repetido, webhook sem assinatura, pagamento duplicado ou PIX após expiração. Os 100% medem os cenários escolhidos, não o sistema.
- **RF-25.** O resumo lista PROCESSANDO, APROVADO e RECUSADO. REEMBOLSADO nunca é usado, e o cartão nunca passa por PROCESSANDO.
- **RNF-14 (WCAG 2.1 AA).** A evidência citada é "navegação por teclado, contraste e modal de ajuda". Não há verificação registrada.

## 6. Ambiguidades: o que a IA viu e o que não viu

As cinco "ambiguidades" listadas pela IA são as mesmas do plano. Duas são decisões de projeto, não ambiguidades da ERS: o momento de gravar a reserva e criar ou sobrescrever registros de pagamento. As lacunas reais que a rodada 1 já tinha revelado não aparecem:

1. A ERS não exige que o aviso do gateway seja autenticado (B01).
2. A ERS não diz o que fazer com um pagamento recebido para reserva cancelada ou já paga (B02, B03).
3. A ERS não proíbe check-in no passado (B06).

As duas rodadas tropeçaram nos mesmos pontos que a ERS não define. Isso indica que o problema está na especificação, não no modelo. A recomendação da auditoria da rodada 1 continua valendo: incluir esses três itens na ERS como requisitos.

## 7. Próximos passos sugeridos

1. Adicionar à ERS os requisitos da Seção 6 e a regra de que rotas de desenvolvimento não existem em produção.
2. Se o grupo quiser uma rodada 3, entregar esta auditoria à IA, pedir as correções e rodar `auditoria/verificacoes.py` de novo.
