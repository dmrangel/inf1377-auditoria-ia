# Prompt para a IA geradora: cancelamento e reembolso

Baseado no modelo [`alunos/_modelo/prompt_geracao.md`](../../_modelo/prompt_geracao.md), na variante em que a funcionalidade se soma ao código do fluxo de reserva. Só os colchetes do modelo foram preenchidos e as regras do repositório foram acrescentadas, como nas páginas da Julia e da Rafaela, para que as auditorias sejam comparáveis.

Antes de enviar, o código de `alunos/davi-rangel/rodada2/` (fluxo de reserva, pagamento e confirmação) foi copiado para `alunos/pedro-loschi/codigo/`, sem a auditoria, a conversa e o resumo do Davi. Cancelamento e reembolso não fazem sentido sem reservas e pagamentos, por isso esta funcionalidade parte desse código.

A ERS não foi anexada: ela está no repositório, em `requisitos/`, e a IA leu o PDF de lá.

---

Você é um desenvolvedor de software experiente. A Especificação de Requisitos de Software (ERS v1.2, padrão IEEE 830) de uma plataforma de hospedagem inspirada no Airbnb, escrita pelo nosso grupo na disciplina de Engenharia de Requisitos, está neste repositório em `requisitos/ERS_v1.2_Plataforma_de_Hospedagem.pdf`.

## Regras do repositório

- O código em `alunos/pedro-loschi/codigo/` já implementa o fluxo de reserva, pagamento e confirmação. Leia a ERS e esse código. Não abra as pastas dos outros integrantes em `alunos/` nem os outros arquivos de `requisitos/`.
- Grave tudo em `alunos/pedro-loschi/codigo/` e não altere nada fora dessa pasta.
- Não faça commit nem push. Eu reviso e envio.

## Tarefa

Acrescente a esse código **o cancelamento de reserva e o reembolso**, sem alterar o comportamento do fluxo de reserva. Use o mesmo visual (templates e CSS) e o mesmo banco de dados que já existem. A funcionalidade está descrita na ERS nos requisitos **RF-21, RF-25 e RF-27**, na sequência 4 da seção **4.4.2**, na seção **4.5.1** (o reembolso como pagamento da reserva), na regra de negócio **RN-05** e no caso de uso **UC12 (Cancelar reserva)**.

O fluxo começa quando o hóspede ou o anfitrião, já logado, abre uma reserva PENDENTE ou CONFIRMADA e escolhe "Cancelar". Ele termina quando a reserva está CANCELADA, o reembolso devido foi solicitado ao gateway e registrado, e a outra parte foi notificada.

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
