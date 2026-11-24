# Julia Kymie: Gerenciamento de acomodações

[← Voltar à página do grupo](../../README.md)

| | |
|---|---|
| **Funcionalidade** | Gerenciamento de acomodações |
| **Onde está na ERS** | 4.2 (RF-07 a RF-11); 3.3 (serviço de CEP e armazenamento de arquivos); RNF-11; UC05, UC06 e UC07 |
| **IA geradora** | Claude Code (app de desktop), modelo Claude Opus 5.5 |
| **IA auditora** | A definir (diferente da geradora) |
| **Status** | Em andamento: geração concluída, auditoria pendente |

## Resultado

Geração concluída (conduzida por Gabriel Emile no Claude Code): código em `codigo/`, com 114 testes pytest (todos passando), tabela de rastreabilidade (`codigo/RASTREABILIDADE.md`) e 18 ambiguidades da ERS registradas (`codigo/AMBIGUIDADES.md`). A auditoria ainda não foi feita.

## Arquivos

```
julia-kymie/
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

- **Geração:** [`interacao_ia/conversa_geracao.md`](interacao_ia/conversa_geracao.md). O prompt enviado é o de [`prompts/geracao.md`](prompts/geracao.md), adaptado ao Claude Code: em vez de anexar a ERS, aponta para o PDF no repositório e acrescenta regras (não abrir as pastas dos outros, gravar só em `codigo/`, não commitar). A primeira mensagem traz uma nota de contexto antes do prompt.
- **Auditoria:** pendente.

## Auditoria

[Link para `auditoria/auditoria_ia.md` e um resumo dos problemas mais graves.]

## Conversa em imagens

**1. [O que aparece no print.]**

<!-- Coloque os prints em prints/ e troque esta linha por: ![Print 1](prints/01.png) -->

## Como rodar

```bash
cd alunos/julia-kymie/codigo
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
python -m pytest       # testes, com banco separado do app
```

Os cenários (caminho feliz e erros) estão em [`codigo/README.md`](codigo/README.md).
