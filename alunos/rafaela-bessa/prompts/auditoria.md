# Prompt da auditoria (Gemini, no Antigravity)

| | |
|---|---|
| **Ferramenta** | Antigravity (agente do Gemini), com a pasta `auditoria-avaliacao` aberta como workspace |
| **Quando** | 18/11/2026, das 20h51 às 21h08 (UTC) |
| **Conversa completa** | [`interacao_ia/conversa_auditoria.md`](../interacao_ia/conversa_auditoria.md) |
| **Resultado** | [`auditoria/auditoria_ia.md`](../auditoria/auditoria_ia.md) |

A auditoria rodou fora deste repositório, numa pasta separada com o PDF da ERS v1.2 e uma cópia do código em `codigo/`, para que o agente não visse as pastas dos outros integrantes nem o histórico do git. O código auditado é idêntico ao que está em [`codigo/`](../codigo/).

O prompt pedia que o próprio Gemini gravasse a auditoria em `auditoria_ia.md`, e depois pedi a ele que incluísse este prompt no começo do relatório — por isso ele também aparece lá.

---

Você é um auditor de software. Nesta pasta estão a Especificação de Requisitos de Software (ERS_v1.2_Plataforma_de_Hospedagem.pdf) de uma plataforma de hospedagem e, em codigo/, o código do sistema. Nesse código, outra IA acrescentou a avaliação de estadia (seção 4.6, RF-29 a RF-32, RN-06, UC18 e UC19) a um fluxo de reserva, pagamento e confirmação que já existia. O relatório dessa IA sobre o próprio trabalho está em codigo/RELATORIO.md e codigo/README.md.

Escopo da auditoria: os arquivos novos da avaliação (avaliacoes.py, rotas_avaliacao.py, seed_avaliacoes.py, os templates e o JavaScript das avaliações, tests/test_avaliacao.py) e as alterações que a IA fez no fluxo de reserva para encaixar a avaliação (descritas na seção 9 do README). O fluxo de reserva em si já foi auditado separadamente; aponte problemas nele só quando afetarem a avaliação.

Faça uma auditoria crítica do código em relação à ERS. Não corrija o código: o objetivo é avaliar o que a IA entregou. Você pode instalar as dependências, rodar o sistema e os testes para comprovar os problemas, mas não altere os arquivos de codigo/; se precisar de um script de verificação, crie fora dessa pasta.

Leia a ERS inteira e todos os arquivos do código.
Para cada requisito, regra de negócio e caso de uso ligado a essa funcionalidade, verifique se o código faz o que a ERS pede. Procure principalmente fora do caminho feliz: entradas inválidas, acesso de outro usuário, ações repetidas, estados fora de ordem, falhas de serviços externos.
Liste os problemas numa tabela com: ID, severidade, problema, requisito da ERS afetado e evidência (arquivo e linha, e como reproduzir). Severidade Alta quebra uma regra de negócio ou causa perda financeira ou de dados; Média é um requisito atendido pela metade; Baixa é qualidade ou robustez.
Para cada problema, diga se você confirmou executando o sistema ou se é uma suspeita pela leitura do código.
Compare o relatório da IA geradora com o código e aponte as afirmações que o código não sustenta (por exemplo, "todos os requisitos atendidos" ou "testes cobrindo todas as regras").
Liste o que a IA geradora acertou.
Separe os problemas que vêm de lacunas da própria ERS, ou seja, pontos que a especificação não define, e sugira o requisito que deveria ser acrescentado.

Responda em português, com um veredito de um parágrafo no início. Ao final, grave a auditoria completa em auditoria_ia.md, nesta pasta (fora de codigo/).

---

## Mensagem seguinte

### 2. Pedido para registrar o prompt na própria auditoria (18/11, 21h08)

coloque na auditoria o prompt que te passei no inicio da conversa
