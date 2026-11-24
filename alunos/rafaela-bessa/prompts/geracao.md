# Prompt da geração (Claude Opus 5.5)

| | |
|---|---|
| **Ferramenta** | Claude Code no app de desktop, com este repositório aberto como pasta de trabalho |
| **Modelo** | Claude Opus 5.5 (`claude-opus-5-5`) |
| **Quando** | 18/11/2026, das 15h03 às 20h30 (UTC) |
| **Conversa completa** | [`interacao_ia/conversa_geracao.md`](../interacao_ia/conversa_geracao.md) |

A ERS v1.2 não foi anexada no chat: ela já estava no repositório, em `requisitos/`, e a IA leu o PDF de lá. O código do fluxo de reserva, pagamento e confirmação também já estava em `codigo/`, e a tarefa era acrescentar a avaliação de estadia a ele.

A conversa teve cinco mensagens minhas. A primeira é o pedido, reproduzido entre as linhas abaixo. As outras quatro vêm depois, na ordem em que foram enviadas.

---

Você é um desenvolvedor de software experiente. A Especificação de Requisitos de Software (ERS v1.2, padrão IEEE 830) de uma plataforma de hospedagem inspirada no Airbnb, escrita pelo nosso grupo na disciplina de Engenharia de Requisitos, está neste repositório em `requisitos/ERS_v1.2_Plataforma_de_Hospedagem.pdf`.
Regras do repositório

* O código em `alunos/rafaela-bessa/codigo/` já implementa o fluxo de reserva, pagamento e confirmação. Leia a ERS e esse código. Não abra as pastas dos outros integrantes em `alunos/` nem os outros arquivos de `requisitos/`.
* Grave tudo em `alunos/rafaela-bessa/codigo/` e não altere nada fora dessa pasta.
* Não faça commit nem push. Eu reviso e envio.

Tarefa
Acrescente a esse código a avaliação de estadia, sem alterar o comportamento do fluxo de reserva. Use o mesmo visual (templates e CSS) e o mesmo banco de dados que já existem. A funcionalidade está descrita na ERS na seção 4.6 (RF-29 a RF-32) e na regra de negócio RN-06, e nos casos de uso UC18 (Avaliar estadia) e UC19 (Avaliar hóspede).
A funcionalidade começa quando uma reserva passa para CONCLUIDA e o sistema convida o hóspede e o anfitrião a avaliar. Ela termina quando as avaliações são publicadas e a nota média da acomodação é atualizada. O selo superhost (RF-33 e RN-07) fica fora desta tarefa.
Leia a ERS inteira antes de começar. Todos os requisitos funcionais, não funcionais, regras de negócio, casos de uso e o projeto de tabelas que afetam essa funcionalidade devem ser respeitados.
Tecnologia (obrigatória)

* Back-end: Python 3 + Flask.
* Banco de dados: SQLite, criado automaticamente na primeira execução.
* Front-end: HTML, CSS e JavaScript puro (sem frameworks).
* Deve rodar localmente com `pip install -r requirements.txt` e `python app.py`.

Simplificações permitidas

* Sistemas externos são simulados dentro do próprio projeto. Mantenha-os em módulos separados, com a mesma interface que um serviço real teria, e documente como simular cada resposta.
* Login: pode existir um usuário de teste já autenticado, mas as regras de quem pode fazer o quê devem ser verificadas no servidor.
* Dados de exemplo: crie dados de teste suficientes para demonstrar todos os cenários, inclusive os de erro.
* Funcionalidades fora desta tarefa não precisam ser implementadas.

Agora
Ainda não escreva código. Apresente um plano curto: telas, rotas, tabelas e as ambiguidades da ERS que você já encontrou. Sempre que a ERS for ambígua, incompleta ou contraditória, não decida em silêncio: diga o trecho, a interpretação que pretende adotar e a alternativa descartada.

---

## Mensagens seguintes

### 2. Ajuste do plano ao código que já existia (18/11, 15h10)

Copiei o código do fluxo de reserva para alunos/rafaela-bessa/codigo/. Continue sem abrir a pasta do Davi. Leia esse código, ajuste o plano ao que existe de fato e me mostre só o que mudou. Ainda não escreva código.

### 3. Aprovação do plano, com uma correção, e pedido de implementação (18/11, 15h15)

Plano aprovado, com um ajuste: a conclusão da reserva não pode quebrar a tela de confirmação. Faça a correção mínima para que /confirmacao/<id> aceite também reservas CONCLUIDAS, mostrando o endereço completo como numa CONFIRMADA, e registre essa alteração no fluxo de reserva no README.

Implemente o código-fonte completo em alunos/rafaela-bessa/codigo/, organizado em arquivos, com comentários onde a regra de negócio não for óbvia. Atualize o README.md explicando como rodar e como testar cada cenário, do caminho feliz aos erros. Se precisar mudar algo do plano, diga o quê e por quê.

### 4. Execução da suíte de testes com cobertura (18/11, 16h20)

Rode agora a suíte completa (os 15 testes originais e os 36 novos) com a medição de cobertura e mostre a saída do pytest aqui na conversa.

### 5. Pedido do RELATORIO.md e correção da cobertura no README (18/11, 20h27)

Por último, crie alunos/rafaela-bessa/codigo/RELATORIO.md com:

1. Tabela de rastreabilidade: para cada requisito, regra de negócio ou passo de caso de uso da ERS que você considerou relevante, informe o ID, onde foi implementado (arquivo e função) e como testar. Liste também os requisitos relevantes que não implementou e por quê.
2. Lista de ambiguidades e decisões: cada ponto em que a ERS foi ambígua, incompleta ou contraditória, com o trecho, a interpretação que você adotou e a alternativa descartada.

Corrija também, no README, a cobertura para o número sem os arquivos de teste.
