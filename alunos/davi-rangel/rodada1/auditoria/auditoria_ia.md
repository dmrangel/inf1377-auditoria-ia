# Auditoria do código gerado por IA: fluxo de reserva, pagamento e confirmação

**Disciplina:** INF1377 – Engenharia de Requisitos
**Código auditado:** gerado pelo Gemini 3.8 Flash a partir do prompt [`prompts/rodada1.md`](../../prompts/rodada1.md) e da ERS
**Referência da auditoria:** ERS v1.2
**Auditor:** Claude (Opus 5.5), seguindo a sugestão do professor de uma IA criticar a outra
**Data:** 10/11/2026

## 1. Como a auditoria foi feita

1. Leitura de todos os arquivos gerados: `app.py`, `database.py`, `models.py`, `services/`, `templates/`, `static/app.js` e `tests/test_fluxo.py`.
2. Comparação de cada requisito ligado ao fluxo (Seções 3.1, 3.4, 4.4, 4.5, 5 e B.3/B.4 da ERS) com o que o código faz de fato.
3. Execução do sistema numa cópia isolada para confirmar cada suspeita. Os nove problemas da Seção 3 podem ser reproduzidos com:

```
python auditoria/verificacoes.py
```

O script usa um banco temporário e não altera o `hospedagem.db` do projeto.

## 2. Veredito

O caminho feliz funciona. As três telas existem, o cálculo do valor total está certo (inclusive o desconto de superhost como 10% sobre a taxa), o endereço completo só aparece na tela de confirmação e o PIX usa um identificador (txid) por cobrança, como pede a ERS.

Os problemas aparecem fora do caminho feliz, que é justamente o que a ERS mais detalha: pagamento duplicado, PIX pago fora do prazo, expiração da reserva, controle de acesso e auditoria. Também há um problema de método: os testes só passam com o banco vazio, e o relatório da IA diz que a suíte cobre "todas as RNs, RFs e RNFs", o que não é verdade.

## 3. Problemas encontrados

Severidade: **Alta** quebra uma regra de negócio ou causa perda financeira ou de dados; **Média** é um requisito atendido pela metade; **Baixa** é qualidade ou robustez.

| ID | Severidade | Problema | Requisito afetado | Evidência |
|:-:|:-:|---|---|---|
| A01 | Alta | O webhook do PIX (`/api/webhook/pix`) não exige assinatura nem segredo. Qualquer pessoa que conheça um txid confirma a reserva sem pagar. O valor só é comparado com `<`, então qualquer valor maior é aceito. | 3.4, 4.5.2 passo 4 ("confere o valor"), RF-23 | `verificacoes.py` A01: webhook falso com valor 99999 retorna 200 |
| A02 | Alta | O webhook não verifica se a reserva já está CONFIRMADA. Se o hóspede paga no cartão e depois paga um PIX gerado antes, os dois pagamentos ficam APROVADO e nada é reembolsado. | RF-23, RF-27, UC16 | A02: 2 pagamentos APROVADO na mesma reserva |
| A03 | Alta | As rotas `/reservas/<id>/pagamento`, `/confirmacao` e `/status` não verificam se a reserva pertence ao usuário logado. Trocando o número na URL, outro usuário vê a confirmação com rua e CEP. | RNF-05, UC16 pré-condição ("reserva PENDENTE **do hóspede**") | A03: usuário 2 vê o endereço da reserva do usuário 1 |
| A04 | Alta | Se o banco avisa um PIX pago depois dos 30 minutos, o sistema responde erro, não reembolsa e deixa o pagamento em PROCESSANDO para sempre. O hóspede perde o dinheiro. | RN-04, RF-25, RF-27 | A04: webhook 400, pagamento PROCESSANDO |
| A05 | Alta | A expiração da RN-04 só acontece quando alguém abre aquela reserva específica. A verificação de disponibilidade conta reservas PENDENTE vencidas, então datas abandonadas ficam bloqueadas indefinidamente. | RN-04, RF-19 | A05: reserva vencida há 2 dias ainda bloqueia o período |
| A06 | Média | A reserva é criada com 0 ou −3 hóspedes e com check-in no passado. A RN-02 só verifica o limite superior. | RN-01, RN-02, RF-17 | A06: as três reservas inválidas retornam 200 |
| A07 | Média | Campo ausente ou data malformada geram erro 500 (página de erro do servidor), não uma mensagem ao usuário. As mensagens que existem citam códigos como "(RN-01)", que não fazem sentido para o hóspede. | 3.1 ("mensagens de erro em linguagem simples") | A07: dois pedidos malformados retornam 500 |
| A08 | Média | A auditoria registra só a reserva. Mudanças de status do pagamento não são registradas. O pagamento por cartão é gravado direto como APROVADO ou RECUSADO, sem passar por PROCESSANDO. O "responsável" é o nome digitado, não o id do usuário. | RNF-22, RF-25, 4.5.2 passo 1, UC16 passo 3 | A08: entidades auditadas = só `reserva` |
| A09 | Média | As conexões com o banco não são fechadas quando ocorre uma exceção. Depois de um erro de gravação, os pedidos seguintes falham com "database is locked" até o servidor ser reiniciado. | RNF-12 (disponibilidade) | A09: pedido válido falha com 500 após 5,5 s |
| A10 | Média | Os testes usam o banco real (`hospedagem.db`), não um banco de teste. Na segunda execução, 7 dos 10 testes falham, porque as reservas da primeira execução ocupam as mesmas datas. Isso também quebra a demonstração do README: no banco atual do projeto, o cenário "Studio Luxo Superhost" com as datas padrão da tela inicial responde "Acomodação já reservada". | RNF-15, RNF-13 | `pytest` duas vezes seguidas: 10 passaram, depois 7 falharam |
| A11 | Média | O hóspede recebe o e-mail, mas o anfitrião não é notificado. No PIX, o e-mail vai para um endereço fixo no código (`hospede@teste.com`), não para o hóspede da reserva. | 4.4.2 passo 2, UC16 passo 5, RF-28 | `app.py` linhas 189–192 e 270–272 |
| A12 | Média | O QR Code do PIX é gerado por um serviço externo (`api.qrserver.com`), contrariando o pedido de simular os sistemas externos dentro do projeto. Sem internet a imagem não aparece, e os dados da cobrança vão para um terceiro. | Prompt ("sistemas externos simulados"), 3.3 | `services/payment_gateway.py` linha 37 |
| A13 | Baixa | O banco não segue o projeto de tabelas da ERS v1.2: `superhost` foi para a acomodação (a ERS põe no usuário), não existem as tabelas de histórico de status, e há uma tabela `auditoria` genérica no lugar delas. | B.4 | `database.py` |
| A14 | Baixa | O login é simulado com um hóspede fixo em todas as requisições, então as verificações "usuário não autenticado" do código nunca disparam. O prompt permitia o hóspede de teste, mas pedia que a regra fosse verificada no servidor. | UC10 pré-condição | `app.py` linhas 14–20 |
| A15 | Baixa | Valores em dinheiro são calculados e guardados como `float`. Funciona nos exemplos, mas o certo é usar `Decimal` ou centavos inteiros. | RF-18 | `models.py`, `database.py` |
| A16 | Baixa | Os formulários não ligam rótulos aos campos (`<label for>`), e os avisos usam `alert()` e emojis como única informação. Isso prejudica leitores de tela. | RNF-14 (WCAG 2.1 AA) | `templates/pagamento.html`, `index.html` |
| A17 | Baixa | `secret_key` fixa no código e `debug=True`. Aceitável num protótipo, mas deve ser dito. | Segurança geral | `app.py` linhas 12 e 302 |

## 4. Onde o relatório da IA exagerou

O `resumo_geral_implementacao.md` que o Gemini escreveu tem afirmações que o código não sustenta:

- **"10 testes automatizados cobrindo todas as RNs, RFs e RNFs."** Os testes cobrem o caminho feliz e cinco regras. Não há teste para webhook inválido, pagamento duplicado, PIX vencido, acesso de outro usuário nem auditoria de pagamento. E a suíte só passa uma vez (A10).
- **RNF-02 "Processamento síncrono e instantâneo".** Nada mede o tempo. A afirmação vale para o simulador, não para um gateway real.
- **RF-25 "Status do pagamento: PROCESSANDO, APROVADO, RECUSADO".** O cartão nunca passa por PROCESSANDO, e REEMBOLSADO nunca é usado (A08).
- **RNF-22 "Auditoria de mudanças de status".** Só da reserva (A08).
- **Versão da ERS.** O grupo enviou a ERS v1.2, mas o documento de entrega gerado pela IA diz "ERS v1.1" no cabeçalho, no comentário do banco e no título das páginas. O banco também ignora o que entrou no B.4 da v1.2: o superhost no usuário e as tabelas de histórico de status (A13).

## 5. O que a IA acertou

- As três telas pedidas na Seção 3.1 (resumo, pagamento e confirmação).
- O cálculo do RF-18 com a taxa da RN-03 e o desconto da RN-07 interpretado como 10% sobre o valor da taxa, igual à ERS v1.2. Há teste para isso.
- O RNF-05 no caminho normal: a tela de resumo nem consulta rua e CEP no banco, e a confirmação só abre com status CONFIRMADA (a falha é o controle de acesso, A03).
- O RNF-08: o número do cartão e o CVV não são gravados.
- A distinção entre cartão síncrono e PIX assíncrono com txid único por cobrança (RF-23), incluindo a nova tentativa após recusa (RF-26).
- A decisão sobre o TBD-03 (confirmação automática), igual à que tomamos na ERS v1.2.
- O registro das próprias decisões e ambiguidades, como o prompt pedia.

## 6. Lacunas da própria ERS que a auditoria revelou

Parte dos erros vem de pontos que a ERS não define. Isso é resultado de Engenharia de Requisitos e deve voltar para o documento:

1. **Webhook:** a ERS não exige que o aviso do gateway seja autenticado (A01). Sugestão de RNF: "O sistema deve aceitar avisos de pagamento somente com assinatura válida do gateway."
2. **PIX pago depois do prazo:** a ERS não diz o que fazer (A04). Sugestão de RN: "Pagamento recebido para reserva cancelada ou já paga deve ser reembolsado integralmente."
3. **Pagamentos simultâneos:** a ERS permite vários códigos PIX ativos, mas não diz o que acontece quando mais de um é pago (A02).
4. **Valores mínimos:** a ERS não exige ao menos 1 hóspede nem proíbe check-in no passado (A06). A RN-01 e a RN-02 podem ser completadas.
5. **Acesso à reserva:** o RNF-11 protege as reservas do anfitrião, mas nenhum requisito diz que só o hóspede dono vê a própria reserva (A03).

## 7. Próximos passos sugeridos

1. Guardar a conversa completa com o Gemini (prompt, respostas e o pedido do resumo). Ela faz parte da entrega.
2. Adicionar à ERS os itens da Seção 6.
3. Devolver esta auditoria ao Gemini e pedir as correções, guardando também essa conversa. Rodar `auditoria/verificacoes.py` de novo para conferir quais problemas foram resolvidos.
4. Antes de apresentar, apagar o `hospedagem.db` para a demonstração começar com o banco limpo (A10).
