# Julia Kymie: Gerenciamento de acomodações

[← Voltar à página do grupo](../../README.md)

| | |
|---|---|
| **Funcionalidade** | Gerenciamento de acomodações |
| **Onde está na ERS** | 4.2 (RF-07 a RF-11); 3.3 (serviço de CEP e armazenamento de arquivos); RNF-11; UC05, UC06 e UC07 |
| **IA geradora** | Claude Code (app de desktop), modelo Claude Opus 5.5 |
| **IA auditora** | Codex (app de desktop), modelo GPT-6.2 Sol, esforço alto |
| **Status** | Concluído |

## Resultado

Geração concluída (conduzida por Gabriel Emile no Claude Code): código em `codigo/`, com 114 testes pytest (todos passando), tabela de rastreabilidade (`codigo/RASTREABILIDADE.md`) e 18 ambiguidades da ERS registradas (`codigo/AMBIGUIDADES.md`). A auditoria, feita pelo Codex (GPT-6.2 Sol) rodando o sistema, os testes e o navegador, encontrou **18 problemas: 6 de severidade alta, 10 média e 2 baixa**. Os testes da IA passavam todos, mas não cobriam esses cenários.

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
└── auditoria/             relatório da auditoria (auditoria_ia.md)
```

## Registro da interação com a IA

- **Geração:** [`interacao_ia/conversa_geracao.md`](interacao_ia/conversa_geracao.md). O prompt enviado é o de [`prompts/geracao.md`](prompts/geracao.md), adaptado ao Claude Code: em vez de anexar a ERS, aponta para o PDF no repositório e acrescenta regras (não abrir as pastas dos outros, gravar só em `codigo/`, não commitar). A primeira mensagem traz uma nota de contexto antes do prompt.
- **Auditoria:** [`interacao_ia/conversa_auditoria.md`](interacao_ia/conversa_auditoria.md). Exportada do log local do Codex; as instruções de sistema do Codex foram omitidas e as saídas longas de comandos foram cortadas em 2.000 caracteres.

## Auditoria

Relatório completo: [`auditoria/auditoria_ia.md`](auditoria/auditoria_ia.md). Os seis problemas de severidade alta:

- **P01:** o login de demonstração permite assumir a identidade de outro anfitrião sem credenciais (pré-condição do UC05, RNF-11).
- **P02:** o endereço exato pode aparecer no título público do anúncio (RNF-05).
- **P03:** um arquivo inválido conta como foto para atingir o mínimo de 5 (RF-08, UC05).
- **P04:** operações simultâneas quebram o mínimo e o máximo de fotos (RF-08, RF-09).
- **P05:** a edição pode descartar dados digitados ou sobrescrever dados já salvos (RF-09, UC06).
- **P06:** a validação de capacidade e disponibilidade fica desatualizada se uma reserva for gravada no meio da alteração (RN-02, RF-10).

Lacunas da ERS apontadas pela auditoria: UC06 e UC07 não têm fluxo detalhado; a ERS não define o efeito de editar ou desativar um anúncio com reservas existentes; o RF-10 não define a semântica dos bloqueios e o B.4 não tem tabelas de fotos e bloqueios; o RF-07 não define formatos e limites dos campos; não há tratamento para CEP indisponível ou falha parcial no armazenamento.

## Como rodar

```bash
cd alunos/julia-kymie/codigo
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
python -m pytest       # testes, com banco separado do app
```

Os cenários (caminho feliz e erros) estão em [`codigo/README.md`](codigo/README.md).
