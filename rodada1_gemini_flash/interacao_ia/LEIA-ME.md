# Registro da interação com IA

A implementação do fluxo de reserva, pagamento e confirmação foi feita com IA em duas etapas.

## Etapa 1: geração do código (Gemini, no navegador)

O grupo enviou ao Gemini o prompt de `../../prompt_ia_fluxo_reserva.md` junto com a ERS v1.2 em PDF. A IA respondeu com um documento único contendo a arquitetura, a tabela de rastreabilidade, as decisões de projeto e todo o código-fonte.

**A conversa desta etapa foi apagada por engano e não pôde ser recuperada.** A Atividade nos apps do Gemini também não guardou o registro. O que foi preservado:

| Parte | Arquivo |
|---|---|
| Pedido enviado à IA | `../../prompt_ia_fluxo_reserva.md` |
| Especificação anexada | ERS v1.2 (Google Docs do grupo) |
| Resposta completa da IA | `documento_de_entrega_do_fluxo_de_reserva.md` |

Observação: embora tenha recebido a ERS v1.2, a IA escreveu "ERS v1.1" no cabeçalho do documento e no código. Esse ponto está registrado na auditoria.

## Etapa 2: gravação do código no projeto (Antigravity)

O documento da etapa 1 foi passado ao agente do Antigravity, que criou os arquivos na pasta do projeto, instalou as dependências, rodou os testes e escreveu o resumo `../resumo_geral_implementacao.md`. A conversa está completa em `conversa_antigravity.md`, exportada do log local do Antigravity com `exportar_antigravity.py`.

Durante essa conversa o modelo foi trocado duas vezes: Gemini 3.8 Flash (High), Gemini 4 Argon (Medium) e Gemini 3.8 Flash (Medium).

## Auditoria

A análise crítica do código está em `../auditoria/auditoria_ia.md`, feita por uma segunda IA (Claude), como sugerido pelo professor. Os problemas encontrados podem ser reproduzidos com `python auditoria/verificacoes.py`.
