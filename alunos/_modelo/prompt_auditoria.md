# Prompt para a IA auditora (modelo)

Use uma IA **diferente** da que gerou o código. Envie junto:

- a ERS (`requisitos/ERS_v1.2_Plataforma_de_Hospedagem.pdf`);
- o código gerado (a pasta inteira, ou o link do repositório no GitHub);
- o resumo ou relatório que a IA geradora escreveu sobre o próprio trabalho.

Se a IA auditora conseguir executar código (por exemplo, um agente com terminal), peça para ela comprovar cada problema rodando o sistema. Foi o que tornou a auditoria do fluxo de reserva convincente.

---

Você é um auditor de software. Em anexo estão a Especificação de Requisitos de Software (ERS v1.2) de uma plataforma de hospedagem, o código de **[NOME DA FUNCIONALIDADE]** gerado por outra IA a partir dessa ERS, e o relatório que essa IA escreveu sobre o próprio trabalho.

Faça uma auditoria crítica do código **em relação à ERS**. Não corrija o código: o objetivo é avaliar o que a IA entregou.

1. Leia a ERS inteira e todos os arquivos do código.
2. Para cada requisito, regra de negócio e caso de uso ligado a essa funcionalidade, verifique se o código faz o que a ERS pede. Procure principalmente fora do caminho feliz: entradas inválidas, acesso de outro usuário, ações repetidas, estados fora de ordem, falhas de serviços externos.
3. Liste os problemas numa tabela com: ID, severidade, problema, requisito da ERS afetado e evidência (arquivo e linha, e como reproduzir). Severidade **Alta** quebra uma regra de negócio ou causa perda financeira ou de dados; **Média** é um requisito atendido pela metade; **Baixa** é qualidade ou robustez.
4. Para cada problema, diga se você **confirmou executando** o sistema ou se é uma **suspeita pela leitura** do código.
5. Compare o relatório da IA geradora com o código e aponte as afirmações que o código não sustenta (por exemplo, "todos os requisitos atendidos" ou "testes cobrindo todas as regras").
6. Liste o que a IA geradora acertou.
7. Separe os problemas que vêm de **lacunas da própria ERS**, ou seja, pontos que a especificação não define, e sugira o requisito que deveria ser acrescentado.

Responda em português, com um veredito de um parágrafo no início.
