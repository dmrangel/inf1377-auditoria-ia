# Prompt para a IA geradora (modelo)

Troque o que está entre colchetes antes de enviar. É o mesmo prompt usado no fluxo de reserva (`alunos/davi-rangel/prompts/rodada2.md`), generalizado para qualquer funcionalidade.

**Antes de enviar:**

1. Anexe a ERS (`requisitos/ERS_v1.2_Plataforma_de_Hospedagem.pdf`) ou, num agente como o Antigravity, coloque o PDF na pasta de trabalho e abra **só essa pasta** como workspace.
2. Escolha o modelo antes da primeira mensagem e não troque até o fim.
3. Não apague a conversa. Ela faz parte da entrega.

---

Você é um desenvolvedor de software experiente. Em anexo está a Especificação de Requisitos de Software (ERS v1.2, padrão IEEE 830) de uma plataforma de hospedagem inspirada no Airbnb, escrita pelo nosso grupo na disciplina de Engenharia de Requisitos.

## Tarefa

Implemente **[NOME DA FUNCIONALIDADE]**, descrita na ERS em **[SEÇÕES, por exemplo 4.6 e 5.5]** e nos casos de uso **[IDs, por exemplo UC18 e UC19]**.

[Descreva em uma ou duas frases onde a funcionalidade começa e onde termina, do ponto de vista do usuário.]

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

**Variante, se o grupo decidir que as funcionalidades devem se somar ao mesmo site:** copie `alunos/davi-rangel/rodada2/` para a sua pasta antes de começar e troque a primeira frase da Tarefa por: "O código desta pasta já implementa o fluxo de reserva. Acrescente a ele [NOME DA FUNCIONALIDADE], sem alterar o comportamento do fluxo de reserva."
