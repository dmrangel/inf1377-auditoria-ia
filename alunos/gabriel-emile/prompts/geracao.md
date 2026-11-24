# Prompt para a IA geradora: busca e visualização de acomodações

Baseado no modelo [`alunos/_modelo/prompt_geracao.md`](../../_modelo/prompt_geracao.md). Os colchetes do modelo foram preenchidos e, como a geração rodou no Claude Code com o repositório aberto (e não num chat com a ERS anexada), o primeiro parágrafo aponta para o PDF no repositório e há um bloco com as regras do repositório, como na página da Rafaela.

| | |
|---|---|
| **Ferramenta** | Claude Code no app de desktop, com este repositório aberto como pasta de trabalho |
| **Modelo** | Claude Opus 5.5 (`claude-opus-5-5`) |
| **Conversa completa** | [`interacao_ia/conversa_geracao.md`](../interacao_ia/conversa_geracao.md) |

---

Você é um desenvolvedor de software experiente. A Especificação de Requisitos de Software (ERS v1.2, padrão IEEE 830) de uma plataforma de hospedagem inspirada no Airbnb, escrita pelo nosso grupo na disciplina de Engenharia de Requisitos, está neste repositório em `requisitos/ERS_v1.2_Plataforma_de_Hospedagem.pdf`.

## Regras do repositório

- Leia a ERS. Não abra as pastas dos outros integrantes em `alunos/` nem os outros arquivos de `requisitos/`.
- Grave tudo em `alunos/gabriel-emile/codigo/` e não altere nada fora dessa pasta.
- Não faça commit nem push. Eu reviso e envio.

## Tarefa

Implemente **a busca e visualização de acomodações**, descrita na ERS nas seções **4.3 (RF-12 a RF-16), 5.1 (RNF-01) e 5.2 (RNF-05)** e nos casos de uso **UC08 e UC09**.

O fluxo começa quando o visitante ou hóspede, na tela inicial, informa a localização desejada, as datas e o número de hóspedes. Ele termina quando o usuário abre um anúncio e vê os detalhes, as avaliações e o calendário da acomodação. A reserva em si fica fora desta tarefa.

Leia a ERS inteira antes de começar. Todos os requisitos funcionais, não funcionais, regras de negócio, casos de uso e o projeto de tabelas que afetam essa funcionalidade devem ser respeitados.

## Tecnologia (obrigatória)

- Back-end: **Python 3 + Flask**.
- Banco de dados: **SQLite**, criado automaticamente na primeira execução.
- Front-end: **HTML, CSS e JavaScript puro** (sem frameworks).
- Deve rodar localmente com `pip install -r requirements.txt` e `python app.py`.

## Simplificações permitidas

- **Sistemas externos são simulados** dentro do próprio projeto. Mantenha-os em módulos separados, com a mesma interface que um serviço real teria, e documente como simular cada resposta.
- **Login:** pode existir um usuário de teste já autenticado, mas as regras de quem pode fazer o quê devem ser verificadas no servidor.
- **Dados de exemplo:** crie dados de teste suficientes para demonstrar todos os cenários, inclusive os de erro.
- Funcionalidades fora desta tarefa **não** precisam ser implementadas.

## O que entregar

1. O código-fonte completo, organizado em arquivos, com comentários onde a regra de negócio não for óbvia.
2. Um `README.md` explicando como rodar e como testar cada cenário (caminho feliz e erros).
3. Testes automatizados (pytest) para as regras de negócio, usando um banco separado do banco do app.
4. **Tabela de rastreabilidade:** para cada requisito, regra de negócio ou passo de caso de uso da ERS que você considerou relevante, informe o ID, onde foi implementado (arquivo e função) e como testar. Liste também os requisitos relevantes que **não** implementou e por quê.
5. **Lista de ambiguidades e decisões:** sempre que a ERS for ambígua, incompleta ou contraditória, **não decida em silêncio**. Registre o trecho, a interpretação que você adotou e a alternativa descartada.

Antes de escrever o código, apresente um plano curto: telas, rotas, tabelas e as ambiguidades que já encontrou. Depois do plano, siga direto para a implementação, sem esperar resposta.

---
