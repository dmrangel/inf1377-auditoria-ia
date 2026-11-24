# Prompt para a IA geradora: gerenciamento de acomodações

Baseado no modelo [`alunos/_modelo/prompt_geracao.md`](../../_modelo/prompt_geracao.md). Só os colchetes do modelo foram preenchidos; o resto do texto é igual ao usado pelos outros integrantes, para que as auditorias sejam comparáveis.

**Antes de enviar:**

1. Anexe a ERS (`requisitos/ERS_v1.2_Plataforma_de_Hospedagem.pdf`) ou, num agente como o Antigravity, coloque o PDF numa pasta vazia e abra **só essa pasta** como workspace.
2. Escolha o modelo antes da primeira mensagem e não troque até o fim.
3. Copie o texto entre as linhas e envie numa conversa nova.
4. Não apague a conversa. Ela faz parte da entrega.

---

Você é um desenvolvedor de software experiente. Em anexo está a Especificação de Requisitos de Software (ERS v1.2, padrão IEEE 830) de uma plataforma de hospedagem inspirada no Airbnb, escrita pelo nosso grupo na disciplina de Engenharia de Requisitos.

## Tarefa

Implemente **o gerenciamento de acomodações**, descrito na ERS nas seções **4.2 (RF-07 a RF-11), 3.3 (serviço de CEP e armazenamento de arquivos) e 5.3 (RNF-11)** e nos casos de uso **UC05, UC06 e UC07**.

O fluxo começa quando o anfitrião, já logado, escolhe "Anunciar espaço" ou abre a lista das suas acomodações. Ele termina quando o anúncio foi publicado, editado, desativado ou teve datas bloqueadas no calendário. A lista também mostra ao anfitrião as reservas recebidas em cada acomodação.

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

Antes de escrever o código, apresente um plano curto: telas, rotas, tabelas e as ambiguidades que já encontrou.

---
