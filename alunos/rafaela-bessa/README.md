# Rafaela Bessa: avaliação de estadia

[← Voltar à página do grupo](../../README.md)

| | |
|---|---|
| **Funcionalidade** | Avaliação de estadia, acrescentada ao fluxo de reserva, pagamento e confirmação que já existia |
| **Onde está na ERS** | Seção 4.6 (RF-29 a RF-32), RF-15, regra de negócio RN-06 e casos de uso UC18 (Avaliar estadia) e UC19 (Avaliar hóspede) |
| **IA geradora** | Claude (Opus 5.5), no Claude Code |
| **IA auditora** | Gemini, no Antigravity |
| **Status** | Concluído |

## Resultado

A IA geradora entregou a funcionalidade inteira numa só conversa: 51 testes aprovados (os 15
originais do fluxo de reserva, sem alteração, e 36 novos), 88% de cobertura do código da aplicação,
e um relatório próprio com tabela de rastreabilidade requisito a requisito. O caminho feliz e a
regra central — a publicação cega, em que nenhuma das partes vê a avaliação da outra antes de as
duas avaliarem ou de o prazo de 14 dias terminar — funcionam como a ERS pede.

A auditoria encontrou **11 problemas: 2 de severidade alta, 4 média e 5 baixa**, oito deles
comprovados rodando o sistema, e **6 afirmações dos relatórios da própria IA geradora que o código
não sustenta**. Os dois mais graves:

- **AUD-01 (alta):** ao introduzir o status `CONCLUIDA`, a IA não o acrescentou à verificação de
  sobreposição de datas em `models.validar_disponibilidade_e_regras()`, que só olhava
  `CONFIRMADA` e `PENDENTE`. Com isso é possível criar uma reserva para datas passadas, sobreposta
  a uma estadia já concluída, pagá-la, vê-la virar `CONCLUIDA` na hora e fabricar avaliações para
  distorcer a nota média — quebrando RF-19 e RF-32 de uma vez. A IA havia escrito no README que
  "a avaliação de estadia não muda o comportamento das reservas PENDENTE, CONFIRMADA e CANCELADA";
  o problema é justamente uma consequência que ela não percebeu.
- **AUD-03 (alta):** `_validar_nota()` usa `str.isdigit()` antes de `int()`. Caracteres como `"²"`
  ou `"❹"` passam pelo `isdigit()` e estouram no `int()`, derrubando a requisição com HTTP 500 em
  vez de devolver erro de validação.

O mais revelador foi o **AUD-02**: o teste que a própria IA escreveu para a tela de confirmação
chamava `concluir_reservas_encerradas()` à mão antes de abrir a página, o que mascarou o bug de
dessincronização de status na primeira requisição. O teste passava; a tela, no primeiro acesso,
mostrava "RESERVA CONFIRMADA" e escondia o botão de avaliar.

A auditoria também separou **7 lacunas da própria ERS v1.2** (LAC-01 a LAC-07), com a redação
sugerida para uma v1.3. Duas valem destaque, porque explicam decisões que a IA tomou no escuro: o
RF-32 manda recalcular a média "a cada nova avaliação" enquanto a seção 4.6.2 só publica as
avaliações quando ambos avaliam (LAC-01), e nenhuma regra proíbe o anfitrião de reservar e avaliar
a própria acomodação para inflar a nota (LAC-03). Essas voltam para a especificação como
requisitos novos, não como defeitos de código.

## Arquivos

```
rafaela-bessa/
├── README.md              esta página
├── prompts/
│   ├── geracao.md         prompt enviado ao Claude, com as 4 mensagens seguintes
│   └── auditoria.md       prompt enviado ao Gemini
├── codigo/                código gerado pela IA, com README.md e RELATORIO.md escritos por ela
├── interacao_ia/
│   ├── conversa_geracao.md    conversa completa com o Claude (338 mensagens)
│   └── conversa_auditoria.md  conversa completa com o Gemini (77 passos)
└── auditoria/
    ├── auditoria_ia.md    a auditoria do Gemini
    └── verificacoes/      os scripts com que ele comprovou os problemas
```

## Registro da interação com a IA

As duas conversas estão **completas**, sem cortes: cada pedido meu, cada resposta, cada ação que a
IA executou e o resultado de cada uma.

- **Geração:** [`interacao_ia/conversa_geracao.md`](interacao_ia/conversa_geracao.md) — Claude Opus
  5.5 no Claude Code, 18/11/2026, das 15h03 às 20h30 (UTC). Cinco mensagens minhas: o pedido do
  plano, o ajuste do plano ao código que já existia, a aprovação com uma correção, o pedido da
  suíte de testes com cobertura e o pedido do `RELATORIO.md`. Exportada do log local do app com
  [`exportar_claude_code.py`](../../ferramentas/exportar_claude_code.py).
- **Auditoria:** [`interacao_ia/conversa_auditoria.md`](interacao_ia/conversa_auditoria.md) —
  Gemini no Antigravity, 18/11/2026, das 20h51 às 21h08 (UTC). Exportada do log local com
  [`exportar_antigravity.py`](../../ferramentas/exportar_antigravity.py).

Não há prints: as conversas exportadas são o registro, e trazem mais do que uma captura de tela
mostraria. O raciocínio do Claude aparece em apenas 2 das 57 etapas em que ele pensou, porque o log
do app guarda a assinatura do bloco de raciocínio mas descarta o texto; nada foi removido por mim.

A auditoria rodou numa pasta separada, fora deste repositório, com o PDF da ERS v1.2 e uma cópia do
código, para que o agente do Antigravity não visse as pastas dos outros integrantes nem o histórico
do git. O código auditado é idêntico ao que está em [`codigo/`](codigo/).

## Auditoria

[`auditoria/auditoria_ia.md`](auditoria/auditoria_ia.md) — veredito, verificação requisito a
requisito, a tabela dos 11 problemas com evidência e modo de reproduzir, a comparação entre os
relatórios da IA geradora e o código real, o que ela acertou e as lacunas da ERS.

| Severidade | Problemas |
|---|---|
| Alta | AUD-01 (manipulação da nota média via reservas sobrepostas no passado), AUD-03 (HTTP 500 na validação da nota) |
| Média | AUD-02 (status dessincronizado na primeira abertura da Tela 3), AUD-04 (botão de avaliar exibido indevidamente), AUD-05 (duplicação das reservas do seed), AUD-07 (convite perdido se o e-mail falhar) |
| Baixa | AUD-06 (códigos HTTP da rota web), AUD-08 (`IntegrityError` genérico virando 409), AUD-09 (página pública de acomodação desativada), AUD-10 (arredondamento divergente da média), AUD-11 (banco legado sem `CHECK` e data fora do formato) |

Os scripts que o Gemini escreveu para comprovar os problemas estão em
[`auditoria/verificacoes/`](auditoria/verificacoes/), com instruções em
[`verificacoes/LEIA-ME.md`](auditoria/verificacoes/LEIA-ME.md). **Atenção:** eles recriam o
`codigo/hospedagem.db`.

## Como rodar

Requer Python 3. Dentro de `codigo/`:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

O app abre em `http://127.0.0.1:5000`. No WSL, crie o ambiente com
`python3 -m venv ~/venvs/inf1377` e ative com `source ~/venvs/inf1377/bin/activate`.

Os cenários de teste A a G (estadia à espera de avaliação, prazo encerrado, reserva cancelada,
auto-hospedagem e outros) são criados por `seed_avaliacoes.py` na primeira execução e estão
descritos na seção 5.3 do [`codigo/README.md`](codigo/README.md). O seletor de usuário no topo da
página troca entre Lucas e Ana (hóspedes), Carlos e Mariana (anfitriões).

Os testes:

```bash
pytest --cov=. --cov-report=term
```
