# Ferramentas

## Exportar uma conversa do Antigravity

O Antigravity não tem botão de exportação, mas grava cada conversa no computador em:

```
%USERPROFILE%\.gemini\antigravity\brain\<id-da-conversa>\.system_generated\logs\transcript_full.jsonl
```

O script `exportar_antigravity.py` transforma esse log num Markdown legível, com os seus pedidos, as respostas e o raciocínio da IA, as ações que ela executou e as trocas de modelo.

1. Descubra o id da conversa: é o nome da pasta mais recente em `%USERPROFILE%\.gemini\antigravity\brain\`.
2. Rode, a partir da raiz do repositório:

```bash
python ferramentas/exportar_antigravity.py <id-da-conversa> alunos/<seu-nome>/interacao_ia/conversa_geracao.md
```

## Conversas em outras ferramentas

- **Gemini, ChatGPT ou Claude no navegador:** use o botão de compartilhar da conversa para gerar um link e salve o link na sua página. Copie também o texto da conversa para um arquivo `.md` em `interacao_ia/`, porque o link pode deixar de funcionar.
- **Não apague a conversa** até a entrega. Uma conversa apagada não pode ser recuperada (ver `alunos/davi-rangel/rodada1/interacao_ia/LEIA-ME.md`).
