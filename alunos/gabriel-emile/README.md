# Gabriel Emile: Busca e visualização de acomodações

[← Voltar à página do grupo](../../README.md)

| | |
|---|---|
| **Funcionalidade** | Busca e visualização de acomodações |
| **Onde está na ERS** | 4.3 (RF-12 a RF-16); RNF-01; RNF-05; UC08 e UC09 |
| **IA geradora** | Claude Code (app de desktop), modelo Claude Opus 5.5 |
| **IA auditora** | Codex (app de desktop), modelo GPT-6.2 Sol, esforço alto |
| **Status** | Concluído |

## Resultado

Geração concluída: código em `codigo/`, com 112 testes pytest (todos passando), tabela de rastreabilidade (`codigo/RASTREABILIDADE.md`) e 21 ambiguidades da ERS registradas (`codigo/AMBIGUIDADES.md`). A auditoria, feita pelo Codex (GPT-6.2 Sol) rodando o sistema, os testes e o navegador, encontrou **18 problemas: 4 de severidade alta, 11 média e 3 baixa**, quase todos confirmados executando. Os testes da IA passavam todos, mas não cobriam esses cenários.

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
└── auditoria/             relatório da auditoria (auditoria_ia.md)
```

## Registro da interação com a IA

- **Geração:** [`interacao_ia/conversa_geracao.md`](interacao_ia/conversa_geracao.md). A conversa foi aberta a partir de outra sessão do Claude Code, por isso a primeira mensagem traz uma nota de contexto antes do prompt de [`prompts/geracao.md`](prompts/geracao.md).
- **Auditoria:** [`interacao_ia/conversa_auditoria.md`](interacao_ia/conversa_auditoria.md). Exportada do log local do Codex; as instruções de sistema do Codex foram omitidas e as saídas longas de comandos foram cortadas em 2.000 caracteres.

## Auditoria

Relatório completo: [`auditoria/auditoria_ia.md`](auditoria/auditoria_ia.md). Os quatro problemas de severidade alta:

- **AUD-01:** uma sessão nova assume a identidade da hóspede de teste e recebe o endereço exato de uma acomodação, mesmo com o login simulado desligado (RNF-05).
- **AUD-03:** a reserva pendente continua ocupando as datas exatamente no instante em que completa 30 minutos (RN-04, RF-13).
- **AUD-04:** a nota média pública aceita avaliações fora das regras de autoria, estado da reserva e prazo (RF-15, RF-32, RN-06).
- **AUD-05:** um anúncio com denúncia de risco julgada procedente volta a aparecer na busca se continuar ativo (RF-36, RNF-06).

Lacunas da ERS apontadas pela auditoria: UC08 e UC09 não têm descrição no PDF; a ERS não define se a rua pode ser inferida pela busca pública nem o acesso ao endereço depois da estadia; não define a origem do instante em que a reserva pendente começa a contar nem o intervalo de noites; não define a hora exata do fim do prazo de avaliação nem a diferença entre média interna e média pública.

## Como rodar

```bash
cd alunos/gabriel-emile/codigo
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
python -m pytest       # testes, com banco separado do app
```

Os cenários (caminho feliz e erros) estão em [`codigo/README.md`](codigo/README.md).
