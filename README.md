# INF1377: implementação por IA e auditoria de requisitos

Trabalho do grupo 3WA na disciplina INF1377 – Engenharia de Requisitos (PUC-Rio), sobre uma plataforma de hospedagem inspirada no Airbnb.

Depois de escrever a Especificação de Requisitos de Software (ERS), cada integrante do grupo implementa uma funcionalidade do sistema com IA e audita o resultado:

1. Envia a ERS e um prompt a uma **primeira IA**, que gera o código da funcionalidade.
2. Envia a ERS, o código e o relatório da primeira IA a uma **segunda IA**, que faz a auditoria crítica.
3. Guarda as duas conversas completas e publica tudo na sua página deste repositório.

A avaliação é sobre especificação e auditoria, não sobre o código em si. Cada integrante precisa saber explicar o processo inteiro, dos prompts à auditoria.

## Integrantes

| Integrante | Funcionalidade | IA geradora | IA auditora | Status |
|---|---|---|---|---|
| [Davi Rangel](alunos/davi-rangel/README.md) | Fluxo de reserva, pagamento e confirmação | Gemini 3.8 Flash | Claude (Opus 5.5) | Concluído |
| [Gabriel Emile](alunos/gabriel-emile/README.md) | – | – | – | A fazer |
| [Julia Kymie](alunos/julia-kymie/README.md) | – | – | – | A fazer |
| [Lis Villanova](alunos/lis-villanova/README.md) | – | – | – | A fazer |
| [Pedro Loschi](alunos/pedro-loschi/README.md) | – | – | – | A fazer |
| [Rafaela Bessa](alunos/rafaela-bessa/README.md) | – | – | – | A fazer |

### Sugestão de divisão

A ERS tem sete funcionalidades (Seção 4). Reserva e pagamento já estão feitos. As outras cinco dão uma por integrante:

| Funcionalidade | Onde está na ERS |
|---|---|
| Cadastro e autenticação de usuários | 4.1; UC01 a UC04; RNF-07, RNF-09, RNF-10, RNF-18 |
| Gerenciamento de acomodações | 4.2; UC05 a UC07; serviço de CEP |
| Busca e visualização de acomodações | 4.3; UC08 e UC09; RNF-05 |
| Cancelamento e reembolso | RF-21 e RF-27; UC12 e UC17; RN-05 |
| Avaliação e denúncias | 4.6 e 4.7; UC18 a UC22; RN-06 e RN-07 |

Se o professor pedir que as funcionalidades se somem ao mesmo site, cada um parte do código de `alunos/davi-rangel/rodada2/`. O prompt modelo traz as duas versões.

## Como fazer a sua parte

1. **Prompts:** copie [`alunos/_modelo/prompt_geracao.md`](alunos/_modelo/prompt_geracao.md) e [`alunos/_modelo/prompt_auditoria.md`](alunos/_modelo/prompt_auditoria.md) para `alunos/<seu-nome>/prompts/` e preencha os colchetes.
2. **Geração:** rode o prompt de geração numa IA. Use o mesmo modelo do início ao fim e não apague a conversa.
3. **Auditoria:** rode o prompt de auditoria numa IA diferente da primeira.
4. **Registro:** exporte as duas conversas para `alunos/<seu-nome>/interacao_ia/` (veja [`ferramentas/`](ferramentas/README.md)) e salve os prints em `alunos/<seu-nome>/prints/` numerados (`01.png`, `02.png`, ...).
5. **Página:** preencha o `README.md` da sua pasta, que já existe com o modelo, e atualize a sua linha na tabela de integrantes acima.
6. **Envio:** faça commit só da sua pasta e da sua linha da tabela, e dê push. Para ter permissão de push, peça ao Davi para te adicionar como colaborador do repositório.

A página do Davi serve de exemplo completo, com duas rodadas, auditorias e scripts que reproduzem cada problema.

## Estrutura

```
.
├── requisitos/
│   ├── ERS_v1.2_Plataforma_de_Hospedagem.pdf   ERS usada por todos
│   ├── diagramas/                              casos de uso (PlantUML) e classes (Mermaid)
│   ├── modelagem/                              modelos conceitual, lógico e físico (Visual Paradigm)
│   └── documentos/                             documentos anteriores do grupo
├── ferramentas/                                exportação das conversas do Antigravity
└── alunos/
    ├── _modelo/                                página e prompts modelo
    ├── davi-rangel/
    ├── gabriel-emile/
    ├── julia-kymie/
    ├── lis-villanova/
    ├── pedro-loschi/
    └── rafaela-bessa/
```

## Lacunas da ERS encontradas até agora

As auditorias também revisam a especificação. Pontos que a ERS v1.2 não define e que levaram a IA a errar:

| Lacuna | Encontrada em |
|---|---|
| O aviso de pagamento do gateway não precisa ser autenticado | Fluxo de reserva (Davi) |
| Não diz o que fazer com pagamento recebido para reserva cancelada ou já paga | Fluxo de reserva (Davi) |
| Não proíbe check-in no passado | Fluxo de reserva (Davi) |
| Nenhum requisito diz que só o hóspede dono vê a própria reserva | Fluxo de reserva (Davi) |

Ao terminar a sua auditoria, acrescente aqui as lacunas que você encontrou.
