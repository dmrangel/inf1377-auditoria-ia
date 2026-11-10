# Prompt para a IA – Fluxo de reserva, pagamento e confirmação

> **Como usar:** anexe a ERS v1.2 completa (Google Docs > Arquivo > Fazer download > PDF)
> e cole o texto abaixo na mesma mensagem. Guarde a conversa inteira: ela faz parte da entrega.
>
> **Decisão de projeto do prompt:** ele **não lista** os requisitos que a IA deve seguir.
> O professor quer ver se a IA "cata" sozinha as regras na ERS (ex.: superhost, PIX assíncrono).
> Por isso o prompt pede uma **tabela de rastreabilidade**: é ela que a auditoria vai conferir.

---

Você é um desenvolvedor de software experiente. Em anexo está a Especificação de Requisitos de
Software (ERS v1.2, padrão IEEE 830) de uma plataforma de hospedagem inspirada no Airbnb,
escrita pelo nosso grupo na disciplina de Engenharia de Requisitos.

## Tarefa

Implemente **o fluxo de reserva, pagamento e confirmação** descrito na ERS, em **no máximo três
telas**, conforme a seção 3.1: (1) resumo da estadia, (2) pagamento e (3) confirmação.
O fluxo começa quando o hóspede, já logado, escolhe uma acomodação, as datas e o número de
hóspedes, e termina na tela de confirmação.

Leia a ERS inteira antes de começar. Todos os requisitos funcionais, não funcionais, regras de
negócio, casos de uso e o projeto de tabelas que afetam esse fluxo devem ser respeitados.

## Tecnologia (obrigatória)

- Back-end: **Python 3 + Flask**.
- Banco de dados: **SQLite**, criado automaticamente na primeira execução.
- Front-end: **HTML, CSS e JavaScript puro** (sem frameworks).
- Deve rodar localmente com `pip install -r requirements.txt` e `python app.py`.

## Simplificações permitidas

- **Sistemas externos são simulados** dentro do próprio projeto (gateway de pagamento,
  serviço de e-mail). Mantenha-os em módulos separados, com a mesma interface que um serviço
  real teria, e documente como simular cada resposta (aprovação, recusa, confirmação do PIX).
- **Login:** pode existir um hóspede de teste já autenticado, mas a regra "o hóspede precisa
  estar logado" deve ser verificada no servidor.
- **Dados de exemplo:** crie acomodações e anfitriões de teste suficientes para demonstrar
  todos os cenários do fluxo, inclusive os de erro.
- Funcionalidades fora do fluxo (cadastro, busca, avaliação, denúncias, cancelamento pelo
  usuário) **não** precisam ser implementadas.

## O que entregar

1. O código-fonte completo, organizado em arquivos, com comentários onde a regra de negócio
   não for óbvia.
2. Um `README.md` explicando como rodar e como testar cada cenário (caminho feliz e erros).
3. Testes automatizados (pytest) para as regras de negócio do fluxo.
4. **Tabela de rastreabilidade:** para cada requisito, regra de negócio ou passo de caso de uso
   da ERS que você considerou relevante para o fluxo, informe o ID, onde foi implementado
   (arquivo e função) e como testar. Liste também os requisitos relevantes que **não**
   implementou e por quê.
5. **Lista de ambiguidades e decisões:** sempre que a ERS for ambígua, incompleta ou
   contraditória, **não decida em silêncio**. Registre o trecho, a interpretação que você
   adotou e a alternativa descartada.

Antes de escrever o código, apresente um plano curto: telas, rotas, tabelas e as
ambiguidades que já encontrou.
