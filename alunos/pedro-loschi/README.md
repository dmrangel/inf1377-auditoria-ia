# Pedro Loschi: Cancelamento e reembolso

[← Voltar à página do grupo](../../README.md)

| | |
|---|---|
| **Funcionalidade** | Cancelamento de reserva e reembolso, acrescentados ao fluxo de reserva, pagamento e confirmação do Davi (rodada 2) |
| **Onde está na ERS** | RF-21, RF-25 e RF-27; seção 4.4.2 (sequência 4) e 4.5.1; RN-05; UC12 (Cancelar reserva) |
| **IA geradora** | Claude (Opus 5.5), numa sessão separada do Claude |
| **IA auditora** | A definir (de outra empresa, por exemplo ChatGPT/Codex ou Gemini) |
| **Status** | Geração concluída; auditoria pendente |

## Resultado

Geração concluída: código em `codigo/`, que parte de uma cópia de `alunos/davi-rangel/rodada2/`. A IA acrescentou `cancelamento.py`, três telas (minhas reservas, detalhe da reserva e confirmação do cancelamento), rotas de API, a simulação do reembolso no gateway e 36 testes novos. A suíte inteira termina com 50 testes aprovados e 1 falha esperada (`xfail`); os 15 testes originais do fluxo de reserva continuam iguais e agora usam um banco temporário, sem apagar o banco do app. A falha esperada é proposital: um PIX pago depois do cancelamento reconfirma a reserva, e corrigir isso exigiria mudar o fluxo de reserva, o que o prompt proibia. A IA registrou 14 ambiguidades da ERS na Seção 8 de [`codigo/README.md`](codigo/README.md).

A auditoria ainda não foi feita.

## Arquivos

```
pedro-loschi/
├── README.md              esta página
├── prompts/
│   ├── geracao.md         prompt enviado à IA geradora
│   └── auditoria.md       prompt para a IA auditora
├── codigo/                código gerado pela IA
├── interacao_ia/          registro da conversa de geração
└── auditoria/             relatório da auditoria (pendente)
```

## Registro da interação com a IA

- **Geração:** [`interacao_ia/registro_geracao.md`](interacao_ia/registro_geracao.md). O ambiente usado não grava o log da conversa em disco, então não foi possível exportá-la com `ferramentas/exportar_claude_code.py`. O registro foi escrito pela própria IA geradora logo depois da resposta final: o plano e a resposta final estão transcritos, e as 40 ações intermediárias estão resumidas. O arquivo avisa isso no topo.
- **Auditoria:** pendente.

## Como rodar

```bash
cd alunos/pedro-loschi/codigo
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000, menu "Minhas reservas"
python -m pytest       # testes, com banco separado do app
```

Os cenários de cancelamento (caminho feliz e erros) estão na Seção 8.3 de [`codigo/README.md`](codigo/README.md).
