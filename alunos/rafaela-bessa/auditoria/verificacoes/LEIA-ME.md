# Scripts de verificação da auditoria

Estes três scripts foram escritos pelo **Gemini, no Antigravity**, durante a auditoria. O prompt
pedia que ele não alterasse nada em `codigo/` e criasse fora dessa pasta qualquer script de
verificação, e foi o que ele fez: eles rodaram na pasta da auditoria e são a prova de execução
dos problemas que a tabela de [`../auditoria_ia.md`](../auditoria_ia.md) marca como confirmados.

Estão aqui exatamente como ele os escreveu, sem nenhuma alteração.

| Arquivo | O que verifica |
|---|---|
| `verify_audit.py` | A dessincronização de `concluir_reservas_encerradas()`, a validação de nota e o convite por e-mail |
| `verify_audit2.py` | RF-19 com reservas `CONCLUIDA` sobrepostas e a publicação das avaliações |
| `verify_audit3.py` | Casos de borda: arredondamento, `init_db()` repetido e duplicação do seed |

## Como rodar

A partir de `alunos/rafaela-bessa/` (eles procuram o código em `codigo/` a partir da pasta atual):

```bash
python auditoria/verificacoes/verify_audit.py
python auditoria/verificacoes/verify_audit2.py
python auditoria/verificacoes/verify_audit3.py
```

> **Atenção:** diferente do `verificacoes.py` do Davi, estes scripts **não** usam banco
> temporário: eles chamam `database.init_db(force_recreate=True)` e portanto **apagam e recriam o
> `codigo/hospedagem.db`** do app. O banco não está no repositório e é recriado sozinho na próxima
> execução de `python app.py`, mas qualquer dado de teste que você tenha criado na tela se perde.
