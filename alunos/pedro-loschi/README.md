# Pedro Loschi: Cancelamento e reembolso

[← Voltar à página do grupo](../../README.md)

| | |
|---|---|
| **Funcionalidade** | Cancelamento de reserva e reembolso, acrescentados ao fluxo de reserva, pagamento e confirmação do Davi (rodada 2) |
| **Onde está na ERS** | RF-21, RF-25 e RF-27; seções 4.4.2 (sequência 4) e 4.5.1; RN-05; UC12 (Cancelar reserva) |
| **IA geradora** | Claude (Opus 5.5), numa sessão separada do Claude |
| **IA auditora** | ChatGPT, no navegador |
| **Status** | Concluído |

## Resultado

O código em `codigo/` parte de uma cópia de `alunos/davi-rangel/rodada2/`. A IA geradora acrescentou `cancelamento.py`, três telas (minhas reservas, detalhe da reserva e confirmação do cancelamento), rotas de API, a simulação do reembolso no gateway e 36 testes novos. A suíte termina com 50 testes aprovados e 1 falha esperada (`xfail`), com 99% de cobertura em `cancelamento.py`. Os 15 testes originais do Davi passam sem alteração e agora usam um banco temporário. A IA registrou 14 ambiguidades da ERS (Seção 8.8 de [`codigo/README.md`](codigo/README.md)).

A auditoria do ChatGPT apontou **10 problemas: 5 de severidade alta, 4 média e 1 baixa**. Como o ChatGPT não conseguiu rodar o sistema, o grupo reproduziu os achados com um script. Depois dessa verificação ficaram **8 problemas válidos: 4 altos e 4 médios**. Um achado foi reclassificado como lacuna da ERS e outro foi descartado porque o grupo comprovou que estava errado. Os quatro de severidade alta:

- **A-01:** um PIX pago depois do cancelamento volta a confirmar a reserva cancelada, e as datas podem já ter sido reservadas por outra pessoa. A própria IA geradora encontrou o problema e o deixou visível num teste `xfail`, mas não o resolveu.
- **A-02:** se a reserva tiver dois pagamentos aprovados, só o mais recente é devolvido.
- **A-03:** o reembolso de 50% usa o preço por noite **atual**. O grupo reproduziu: a mesma reserva devolve R$ 450,00 e, depois de o anfitrião dobrar o preço, R$ 900,00. A causa vem da ERS, porque a tabela `reserva` do B.4 não guarda o valor das diárias.
- **A-04:** a rota de teste `/api/dev/switch-user`, herdada do código do Davi, deixa qualquer visitante agir como o hóspede, sem senha, e cancelar a reserva dele. O auditor deixou como suspeita; o grupo confirmou executando.

O resultado mais útil foi sobre a ERS: três dos quatro problemas graves (A-01, A-02 e A-03) vêm de pontos que a especificação não define.

## Arquivos

```
pedro-loschi/
├── README.md                    esta página
├── prompts/
│   ├── geracao.md               prompt enviado à IA geradora
│   ├── auditoria.md             prompt de auditoria do grupo (versão para agente com terminal)
│   └── auditoria_chatgpt.md     versão enviada ao ChatGPT, com a lista de anexos
├── codigo/                      código gerado pela IA
├── interacao_ia/
│   ├── registro_geracao.md      registro da conversa de geração
│   └── conversa_auditoria.md    conversa de auditoria
└── auditoria/
    ├── auditoria_ia.md          relatório do ChatGPT e verificação do grupo
    └── verificacoes/            script que reproduz A-03 e A-04
```

## Registro da interação com a IA

- **Geração:** [`interacao_ia/registro_geracao.md`](interacao_ia/registro_geracao.md). O ambiente usado não grava o log da conversa em disco, então não foi possível exportá-la com `ferramentas/exportar_claude_code.py`. O registro foi escrito pela própria IA geradora logo depois da resposta final: o plano e a resposta final estão transcritos, e as 40 ações intermediárias estão resumidas. O arquivo avisa isso no topo.
- **Auditoria:** [`interacao_ia/conversa_auditoria.md`](interacao_ia/conversa_auditoria.md), com a mensagem enviada, os anexos e a resposta completa do ChatGPT.
- **Tentativas anteriores:** antes do ChatGPT, a auditoria foi tentada duas vezes com outros modelos do Claude (Fable 5.2 e Sonnet 5.5). As duas pararam antes de gravar qualquer arquivo: a primeira por falta de créditos de uso, a segunda por uma interrupção das salvaguardas do modelo. Por isso a auditoria acabou numa IA de outra empresa, como as do Gabriel, da Julia e da Lis.

## Auditoria

Relatório completo e julgamento de cada achado: [`auditoria/auditoria_ia.md`](auditoria/auditoria_ia.md).

**Pontos em que o grupo discordou do auditor:**

- O ChatGPT disse que faltavam arquivos (templates, JavaScript, testes do fluxo de reserva). Eles existem no repositório e só não foram anexados.
- O ChatGPT marcou como "não verificável" que os testes passam e a cobertura é de 86%. O grupo rodou a suíte e confirmou os dois números.
- O ChatGPT classificou como alta a idempotência guardada em memória (A-05). Com o gateway simulado que o prompt autorizou, o grupo classificou como média.

**Lacunas da ERS encontradas:**

- A RN-05 não diz a hora do check-in nem o fuso para contar as 48 horas.
- A ERS não guarda o valor das diárias contratadas (B.4), então o reembolso de 50% depende do preço atual (A-03).
- A ERS não define o que fazer com um pagamento que chega depois do cancelamento, nem com dois pagamentos aprovados na mesma reserva (A-01 e A-02).
- A ERS não diz se dá para cancelar durante a estadia, nem como fica o valor já repassado ao anfitrião (RN-08).
- O UC12 não tem fluxo alternativo para falha do gateway de reembolso.
- O UC17 (Processar reembolso) aparece no diagrama B.2 e não tem descrição.

## Como rodar

```bash
cd alunos/pedro-loschi/codigo
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000, menu "Minhas reservas"
python -m pytest       # 50 aprovados e 1 xfail, com banco separado do app

cd ..
python auditoria/verificacoes/verificacao_grupo.py   # reproduz A-03 e A-04
```

Os cenários de cancelamento (caminho feliz e erros) estão na Seção 8.3 de [`codigo/README.md`](codigo/README.md).
