# Gabriel Emile: Busca e visualização de acomodações

[← Voltar à página do grupo](../../README.md)

| | |
|---|---|
| **Funcionalidade** | Busca e visualização de acomodações |
| **Onde está na ERS** | 4.3 (RF-12 a RF-16); RNF-01; RNF-05; UC08 e UC09 |
| **IA geradora** | Claude Code (app de desktop), modelo Claude Opus 5.5 |
| **IA auditora** | A definir (diferente da geradora) |
| **Status** | Em andamento: geração concluída, auditoria pendente |

## Resultado

Geração concluída: código em `codigo/`, com 112 testes pytest (todos passando), tabela de rastreabilidade (`codigo/RASTREABILIDADE.md`) e 21 ambiguidades da ERS registradas (`codigo/AMBIGUIDADES.md`). A auditoria ainda não foi feita.

## Arquivos

```
gabriel-emile/
├── README.md              esta página
├── prompts/
│   ├── geracao.md         prompt enviado à IA geradora
│   └── auditoria.md       prompt enviado à IA auditora
├── prints/                capturas das conversas (01.png, 02.png, ...)
├── codigo/                código gerado pela IA
├── interacao_ia/          conversas completas exportadas
└── auditoria/             relatório da auditoria
```

## Registro da interação com a IA

- **Geração:** [`interacao_ia/conversa_geracao.md`](interacao_ia/conversa_geracao.md). A conversa foi aberta a partir de outra sessão do Claude Code, por isso a primeira mensagem traz uma nota de contexto antes do prompt de [`prompts/geracao.md`](prompts/geracao.md).
- **Auditoria:** pendente.

## Auditoria

[Link para `auditoria/auditoria_ia.md` e um resumo dos problemas mais graves.]

## Conversa em imagens

**1. [O que aparece no print.]**

<!-- Coloque os prints em prints/ e troque esta linha por: ![Print 1](prints/01.png) -->

## Como rodar

```bash
cd alunos/gabriel-emile/codigo
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
python -m pytest       # testes, com banco separado do app
```

Os cenários (caminho feliz e erros) estão em [`codigo/README.md`](codigo/README.md).
