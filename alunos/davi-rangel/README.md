# Davi Rangel: fluxo de reserva, pagamento e confirmação

[← Voltar à página do grupo](../../README.md)

| | |
|---|---|
| **Funcionalidade** | Fluxo de reserva, pagamento e confirmação em no máximo três telas |
| **Onde está na ERS** | Seções 3.1, 4.4 e 4.5; casos de uso UC10 (Solicitar reserva) e UC16 (Efetuar pagamento) |
| **IA geradora** | Gemini 3.8 Flash, duas rodadas |
| **IA auditora** | Claude (Opus 5.5) |
| **Status** | Concluído |

## Resultado

O fluxo foi gerado duas vezes pelo mesmo modelo e as duas versões foram auditadas com o mesmo método: leitura do código contra a ERS v1.2 e execução de cada suspeita num banco temporário.

| | Rodada 1 | Rodada 2 |
|---|---|---|
| Processo | ERS e prompt num chat do navegador; código gravado depois pelo Antigravity | ERS e prompt direto no Antigravity, numa conversa única |
| Problemas encontrados | 17 (5 de severidade alta) | 11 (4 de severidade alta) |
| Problemas da rodada 1 corrigidos | – | 8 de 11 verificados (3 deles só em parte) |
| Testes da própria IA | 10, só passam com o banco vazio | 15, repetíveis, mas apagam o banco do app |
| Ponto fraco comum | aviso de pagamento do PIX sem autenticação, pagamento duplicado e PIX pago fora do prazo | os mesmos, e o PIX tardio agora gera reserva dupla |

As duas rodadas falharam nos mesmos pontos que a ERS não define: autenticação do aviso do gateway, pagamento recebido para reserva cancelada ou já paga e check-in no passado. Isso volta para a especificação como requisitos novos.

## Arquivos

```
davi-rangel/
├── prompts/
│   ├── rodada1.md          prompt enviado na rodada 1
│   └── rodada2.md          mesmo prompt, com as diferenças da rodada 2 anotadas
├── prints/                 capturas da conversa da rodada 2
├── rodada1/
│   ├── (código gerado pela IA)
│   ├── interacao_ia/       registro da interação e explicação da conversa perdida
│   └── auditoria/          auditoria_ia.md e verificacoes.py
└── rodada2/
    ├── (código gerado pela IA)
    ├── RESUMO_GERAL.md     resumo escrito pela própria IA
    ├── interacao_ia/       conversa completa exportada do Antigravity
    └── auditoria/          auditoria_ia.md e verificacoes.py
```

## Registro da interação com a IA

- **Rodada 1:** a conversa em que o código foi gerado foi apagada por engano e não pôde ser recuperada. O pedido, a ERS e a resposta completa da IA foram preservados, e a conversa de gravação no Antigravity está inteira. Explicação em [`rodada1/interacao_ia/LEIA-ME.md`](rodada1/interacao_ia/LEIA-ME.md).
- **Rodada 2:** conversa completa em [`rodada2/interacao_ia/conversa_antigravity.md`](rodada2/interacao_ia/conversa_antigravity.md): o plano proposto pela IA, a aprovação sem correções e o pedido de resumo.

## Auditorias

- [Rodada 1](rodada1/auditoria/auditoria_ia.md)
- [Rodada 2](rodada2/auditoria/auditoria_ia.md), com a comparação entre as rodadas

## Conversa da rodada 2 em imagens

Capturas de tela da conversa no Antigravity, na ordem em que aconteceu.

**1. Pedido inicial: o prompt da rodada 2 enviado ao Antigravity, e o início do plano da IA.**

![Print 1 da conversa da rodada 2](prints/01.png)

**2. Plano, Tela 1: resumo da estadia, com as regras RN-01, RN-02, RF-19 e o cálculo da taxa.**

![Print 2 da conversa da rodada 2](prints/02.png)

**3. Plano, Tela 2: pagamento por cartão (síncrono) e PIX (assíncrono), com o timer de 30 minutos.**

![Print 3 da conversa da rodada 2](prints/03.png)

**4. Plano, Tela 3: confirmação com endereço completo, e o início da tabela de rotas.**

![Print 4 da conversa da rodada 2](prints/04.png)

**5. Plano: rotas do servidor.**

![Print 5 da conversa da rodada 2](prints/05.png)

**6. Plano: rotas de desenvolvimento, entre elas a /api/dev/switch-user, que a auditoria aponta como falha grave (B04).**

![Print 6 da conversa da rodada 2](prints/06.png)

**7. Plano: projeto de tabelas seguindo o B.4 da ERS v1.2, e a primeira ambiguidade.**

![Print 7 da conversa da rodada 2](prints/07.png)

**8. Ambiguidades 1 e 2: quando gravar a reserva e como arredondar o desconto de superhost.**

![Print 8 da conversa da rodada 2](prints/08.png)

**9. Ambiguidades 3 a 5: expiração dos 30 minutos, proteção do endereço e novas tentativas de pagamento.**

![Print 9 da conversa da rodada 2](prints/09.png)

**10. Última ambiguidade e início da arquitetura proposta.**

![Print 10 da conversa da rodada 2](prints/10.png)

**11. Arquitetura de módulos proposta.**

![Print 11 da conversa da rodada 2](prints/11.png)

**12. Aprovação, sem nenhuma correção, para manter a comparação com a rodada 1.**

![Print 12 da conversa da rodada 2](prints/12.png)

**13. Resposta final, depois de 9 minutos de trabalho: arquivos criados.**

![Print 13 da conversa da rodada 2](prints/13.png)

**14. Continuação: telas, testes ("15 testes, 100% de aprovação") e documentação.**

![Print 14 da conversa da rodada 2](prints/14.png)

**15. Instruções de execução escritas pela IA.**

![Print 15 da conversa da rodada 2](prints/15.png)

**16. Resumo da rastreabilidade e das decisões, segundo a própria IA.**

![Print 16 da conversa da rodada 2](prints/16.png)

## Como rodar

Requer Python 3. Dentro de `rodada1/` ou `rodada2/`:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

O app abre em `http://127.0.0.1:5000`. No WSL, crie o ambiente com `python3 -m venv ~/venvs/inf1377` e ative com `source ~/venvs/inf1377/bin/activate`.

Para reproduzir os problemas da auditoria (usa um banco temporário e não altera o do app):

```bash
python auditoria/verificacoes.py
```

Os testes escritos pela IA rodam com `pytest`. Na rodada 2, eles apagam e recriam o `hospedagem.db` do app.
