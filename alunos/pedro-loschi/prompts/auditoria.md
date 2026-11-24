# Prompt para a IA auditora: cancelamento e reembolso

Baseado no modelo [`alunos/_modelo/prompt_auditoria.md`](../../_modelo/prompt_auditoria.md). Foram preenchidos o nome da funcionalidade e os caminhos do repositório, e acrescentadas as regras de onde gravar, como nas outras páginas.

A IA auditora é um modelo **diferente** do gerador e começou numa conversa nova, sem ver a geração. Ela recebeu:

- a ERS (`requisitos/ERS_v1.2_Plataforma_de_Hospedagem.pdf`);
- o código gerado (a pasta `alunos/pedro-loschi/codigo/` inteira);
- o relatório da IA geradora, que está na Seção 8 de `codigo/README.md` (cenários, tabela de rastreabilidade, requisitos não implementados e ambiguidades).

Como ela tinha terminal, foi pedido que comprovasse cada problema rodando o sistema, com scripts em `auditoria/verificacoes/`, como na auditoria do fluxo de reserva.

---

Você é um auditor de software. Neste repositório estão a Especificação de Requisitos de Software (ERS v1.2) de uma plataforma de hospedagem, em `requisitos/ERS_v1.2_Plataforma_de_Hospedagem.pdf`, o código de **cancelamento de reserva e reembolso** gerado por outra IA a partir dessa ERS, em `alunos/pedro-loschi/codigo/`, e o relatório que essa IA escreveu sobre o próprio trabalho (Seção 8 do `README.md` da mesma pasta, com a tabela de rastreabilidade e a lista de ambiguidades).

O cancelamento foi acrescentado a um código de fluxo de reserva, pagamento e confirmação que já existia. Audite o cancelamento e o reembolso, e os efeitos que eles têm sobre o resto do fluxo. Problemas do fluxo de reserva que não têm relação com o cancelamento só entram se o cancelamento os piorar.

## Regras do repositório

- Não abra as pastas dos outros integrantes em `alunos/` nem os outros arquivos de `requisitos/`.
- Não altere o código em `alunos/pedro-loschi/codigo/`. Grave o relatório em `alunos/pedro-loschi/auditoria/auditoria_ia.md` e os scripts que comprovam cada problema em `alunos/pedro-loschi/auditoria/verificacoes/`. Os scripts devem usar um banco temporário, nunca o banco do app.
- Não faça commit nem push.

## Tarefa

Faça uma auditoria crítica do código **em relação à ERS**. Não corrija o código: o objetivo é avaliar o que a IA entregou.

1. Leia a ERS inteira e todos os arquivos do código.
2. Para cada requisito, regra de negócio e caso de uso ligado a essa funcionalidade, verifique se o código faz o que a ERS pede. Procure principalmente fora do caminho feliz: entradas inválidas, acesso de outro usuário, ações repetidas, estados fora de ordem, falhas de serviços externos.
3. Liste os problemas numa tabela com: ID, severidade, problema, requisito da ERS afetado e evidência (arquivo e linha, e como reproduzir). Severidade **Alta** quebra uma regra de negócio ou causa perda financeira ou de dados; **Média** é um requisito atendido pela metade; **Baixa** é qualidade ou robustez.
4. Para cada problema, diga se você **confirmou executando** o sistema ou se é uma **suspeita pela leitura** do código.
5. Compare o relatório da IA geradora com o código e aponte as afirmações que o código não sustenta (por exemplo, "todos os requisitos atendidos" ou "testes cobrindo todas as regras").
6. Liste o que a IA geradora acertou.
7. Separe os problemas que vêm de **lacunas da própria ERS**, ou seja, pontos que a especificação não define, e sugira o requisito que deveria ser acrescentado.

Responda em português, com um veredito de um parágrafo no início.
