# Busca e visualização de acomodações

Implementação da funcionalidade **4.3 Busca e visualização de acomodações** da ERS v1.2 (RF-12 a RF-16, RNF-01, RNF-05, UC08 e UC09) da Plataforma de Hospedagem (INF1377, PUC-Rio).

- Back-end: Python 3 + Flask, API REST em JSON.
- Banco: SQLite, criado e populado automaticamente na primeira execução.
- Front-end: HTML, CSS e JavaScript puro.

Documentos que acompanham o código:

- [RASTREABILIDADE.md](RASTREABILIDADE.md): cada requisito, onde foi implementado e como testar, além do que não foi implementado e por quê.
- [AMBIGUIDADES.md](AMBIGUIDADES.md): trechos ambíguos da ERS, a decisão adotada e a alternativa descartada.

> O código foi gerado por IA e precisa de revisão humana. As decisões de AMBIGUIDADES.md são hipóteses a validar com o grupo.

## Como rodar

Requer Python 3.10 ou superior.

```powershell
cd alunos/gabriel-emile/codigo
pip install -r requirements.txt
python app.py
```

Abra <http://127.0.0.1:5000>. Na primeira execução é criado `instancia/plataforma.db` com os dados de exemplo.

- As datas dos dados de exemplo são **relativas ao dia em que o banco foi criado**. Para recriá-las com a data de hoje, apague a pasta `instancia/` e rode de novo.
- Outra porta: `$env:PORT=8000; python app.py`.

## Como rodar os testes

```powershell
python -m pytest
```

Com cobertura (RNF-15 exige 70% ou mais):

```powershell
python -m pytest --cov=. --cov-report=term
```

Os testes **não usam o banco do app**: cada teste cria um banco novo em uma pasta temporária (`tests/conftest.py`) com a data fixa de 10/03/2030, para que os cenários não dependam do dia em que são executados. Resultado atual: 112 testes passando, cobertura de 99%.

## Estrutura

```
codigo/
├── app.py                  cria a aplicação Flask (create_app) e roda o servidor
├── rotas.py                API REST (/api/...) e páginas HTML
├── regras/
│   ├── busca.py            validação e busca (RF-12 a RF-14, RF-16)
│   ├── disponibilidade.py  período livre, PENDENTE de 30 min, anúncio publicado
│   ├── avaliacoes.py       nota média e avaliações publicadas (RF-15)
│   └── detalhe.py          página do anúncio, endereço (RNF-05), calendário
├── servicos_externos/      sistemas externos SIMULADOS (ERS 3.3)
│   ├── mapas.py            serviço de mapas
│   └── armazenamento.py    armazenamento de fotos
├── sessao.py               login simulado (usuário de teste)
├── relogio.py              "hoje/agora" com data fixável nos testes
├── db.py, schema.sql       banco SQLite (tabelas do Apêndice B.4)
├── seed.py                 dados de exemplo
├── paginas/                HTML (início, resultados, anúncio, ajuda)
├── static/                 CSS e JavaScript
└── tests/                  testes pytest
```

## API

| Método e rota | Descrição |
|---|---|
| `GET /api/acomodacoes/busca` | Busca. Parâmetros: `cidade`*, `bairro` e/ou `rua`*, `estado`, `checkin`*, `checkout`* (AAAA-MM-DD), `hospedes`*, `preco_min`, `preco_max`, `quartos`, `banheiros`, `camas`, `ordenar` (`relevancia`, `preco_asc`, `preco_desc`, `nota_desc`), `pagina`. Erros de validação retornam 400 com `{"erro", "campos": {campo: mensagem}}`. |
| `GET /api/acomodacoes/<id>` | Detalhes. Com `checkin`, `checkout` e `hospedes` opcionais, informa se o período está disponível. Retorna 404 se o anúncio não existe ou não é visível para o usuário. |
| `GET /api/acomodacoes/<id>/avaliacoes` | Nota média e avaliações publicadas. |
| `GET /api/acomodacoes/<id>/calendario?mes=AAAA-MM&meses=1..6` | Dias livres, ocupados e passados. |
| `GET /api/sessao`, `POST /api/sessao {"usuario_id": n\|null}` | Login simulado (troca o usuário de teste). |
| `GET /api/usuarios-teste` | Lista os usuários de teste. |
| `GET /arquivos/<chave>` | Fotos (armazenamento simulado). |

## Login simulado

O app começa com **Ana Souza (hóspede)** autenticada. No topo de todas as páginas há um seletor "Usuário de teste" para trocar de usuário ou navegar como **Visitante**. A identidade fica na sessão assinada do Flask e **todas as regras de acesso são verificadas no servidor**. Por exemplo, o JSON de quem não pode ver o endereço exato não contém rua, número nem CEP.

| Usuário | Papel | Para que serve |
|---|---|---|
| Ana Souza | hóspede (padrão) | Tem reserva CONFIRMADA no #1 e só CANCELADA no #2 |
| Bruno Lima | anfitrião superhost | Dono dos #1, #2, #3, #8, #11, #12, #14, #17 |
| Carla Mendes | anfitriã | Dona dos #4 a #7, #9, #10, #13, #15, #16 |
| Diego Rocha | hóspede | Tem reserva PENDENTE no #15 e no #6 |
| Elisa Prado | hóspede | Tem reserva CONFIRMADA no #2 |
| Fábio Admin | (admin, só dados) | Emitiu parecer em uma denúncia |

## Sistemas externos simulados

Cada simulação fica em um módulo próprio, com a interface que um adaptador real teria. Trocar por um serviço real exige mudar só a criação do objeto em `app.py`.

| Serviço (ERS 3.3) | Módulo | Como simular cada resposta |
|---|---|---|
| Serviço de mapas | `servicos_externos/mapas.py` | **Sucesso:** bairros listados em `BAIRROS_CONHECIDOS` (ex.: anúncio #1, Copacabana). **Local não encontrado:** anúncio #17 (bairro "Vale das Videiras"), que mostra "Não encontramos este bairro no mapa". **Fora do ar:** iniciar com `$env:SIMULAR_FALHA_MAPAS=1; python app.py`. A página abre normalmente, com "O mapa está indisponível no momento". O serviço recebe só bairro e cidade, então o mapa é sempre aproximado (RNF-05). |
| Armazenamento de arquivos | `servicos_externos/armazenamento.py` | **Sucesso:** chaves `fotos/...` geram uma imagem SVG. **Arquivo ausente:** a 3ª foto do anúncio #15 (chave `ausente/...`) retorna 404 e a página mostra "Foto indisponível". **Fora do ar:** `$env:SIMULAR_FALHA_ARMAZENAMENTO=1; python app.py`. Todas as fotos retornam 503 e as páginas continuam funcionando com textos no lugar das imagens. |

## Dados de exemplo e cenário principal

**Cenário de demonstração:** cidade *Rio de Janeiro*, bairro *Copacabana*, check-in em *hoje + 14 dias*, check-out em *hoje + 17 dias*, *2 hóspedes*. O botão "Preencher com o cenário de demonstração" da tela inicial preenche esses valores.

| # | Anúncio (Copacabana) | Resultado no cenário | Por quê |
|---|---|---|---|
| 1 | Apartamento com vista para o mar | **aparece** | Nota 4,67 (3 avaliações) |
| 2 | Studio aconchegante perto da praia | não aparece | Reserva CONFIRMADA em +14 a +18 (RF-13) |
| 3 | Cobertura duplex com piscina | **aparece** | Reserva termina exatamente no dia do check-in (intervalo semiaberto) |
| 4 | Quarto econômico | não aparece | Capacidade 1 < 2 hóspedes (RF-13/RN-02) |
| 5 | Apartamento familiar | não aparece | Datas bloqueadas pelo anfitrião (RF-10) |
| 6 | Flat moderno no Posto 6 | não aparece | Reserva PENDENTE criada há 10 min (RN-04) |
| 7 | Kitnet reformada | **aparece** | A PENDENTE foi criada há 2 h e está vencida; o anúncio não tem avaliações ("Novo") |
| 8 | Apartamento desativado | nunca aparece | `ativo = 0` (RF-09) |
| 9 | Apartamento sob denúncia | nunca aparece | Denúncia RISCO_SEGURANCA em análise (RNF-06) |
| 10 | Apartamento na Rua Barata Ribeiro | **aparece** | A denúncia em análise não é de risco |
| 11 | Anúncio com só 3 fotos | nunca aparece | Menos de 5 fotos (RF-08) |

Outros: #12 Ipanema (nota 3,0; denúncia de risco julgada improcedente, por isso aparece), #13 Leblon (avaliação ainda **não publicada**), #14 Santa Teresa (nota 5,0), #15 Pinheiros/São Paulo (foto ausente), #16 Vila Madalena/São Paulo (só o anfitrião avaliou, então fica sem nota), #17 Petrópolis (mapa não encontrado).

## Roteiro de testes manuais

**M1. Caminho feliz (UC08 → UC09).** Na tela inicial, clique em "Preencher com o cenário de demonstração" e depois em **Buscar**. Devem aparecer 4 acomodações (#1, #3, #7, #10) para 3 noites, cada uma com foto, título, bairro e cidade, preço por noite e nota (ou "Novo").

**M2. Filtros e ordenação (RF-14, RF-16).** Na página de resultados:
- Preço máximo 300 → ficam #7 (R$ 150) e #10 (R$ 280).
- Limpar e escolher Banheiros "2 ou mais" → #3 e #10.
- Ordenar por "Menor preço" → #7, #10, #1, #3.
- Ordenar por "Maior nota" → #1 (4,67), #3 (4,5) e depois os sem nota.

**M3. Busca por rua e sem acentos (RF-12).**
- Cidade `rio de janeiro`, bairro vazio, rua `atlantica` → só o #1.
- Cidade `SAO PAULO` e bairro `pinheiros` → #15.

**M4. Página do anúncio (UC09).** Abra o #1 a partir da busca. A página deve mostrar fotos, capacidade, quartos, banheiros e camas, regras da casa, o anfitrião com o selo Superhost, o mapa aproximado, a caixa "Disponível nessas datas" com o período marcado no calendário, os dias +25 a +27 como ocupados (bloqueio) e 3 avaliações. A avaliação do anfitrião sobre a hóspede não aparece.

**M5. Endereço exato (RNF-05).** Use o seletor "Usuário de teste":
- *Ana* no #1 → mostra "Avenida Atlântica, 1702 ... CEP" (tem reserva CONFIRMADA).
- *Visitante* no #1 → só "Copacabana, Rio de Janeiro - RJ" e o aviso de que o endereço aparece após a confirmação.
- *Ana* no #2 → só o bairro (a reserva dela foi CANCELADA).
- *Diego* no #15 → só o bairro (a reserva dele está PENDENTE).
- *Bruno* no #2 → endereço completo (é o dono).

Para conferir que o dado nem chega ao navegador, abra `/api/acomodacoes/1` como Visitante.

**M6. Serviços externos.**
- O #17 mostra "Não encontramos este bairro no mapa".
- O #15 mostra "Foto indisponível" no lugar de uma das fotos.
- Reinicie com `SIMULAR_FALHA_MAPAS=1` ou `SIMULAR_FALHA_ARMAZENAMENTO=1` e veja as mensagens de falha (ver tabela acima).

**M7. Avaliações não publicadas e anúncios ocultos.**
- Busque bairro `Leblon` → o #13 aparece como "Novo", porque a avaliação da hóspede ainda está no prazo de 14 dias e o anfitrião não avaliou.
- Acesse `/acomodacao/8` e `/acomodacao/9` como Visitante → "Anúncio não encontrado ou indisponível".
- Como *Bruno*, abra `/acomodacao/8` → a página aparece com o aviso "desativado".

**M8. Erros de entrada (linguagem simples, campo destacado).**
- Busca sem cidade → "Informe a cidade."
- Sem bairro e sem rua → "Informe o bairro ou a rua desejada."
- Check-out igual ou anterior ao check-in → "...mínimo de 1 noite" (RN-01).
- Check-in no passado → "A data de check-in não pode estar no passado."
- Hóspedes 0 → "O valor deve estar entre 1 e 50."
- Preço mínimo maior que o máximo → mensagem no campo de preço máximo.
- Cidade `São Paulo` com bairro `Copacabana` → "Nenhuma acomodação disponível..." com sugestão.
- Ao abrir a página de um anúncio com datas inválidas na URL, a página continua funcionando e mostra o erro na caixa do período.

**M9. Desempenho (RNF-01).** Na aba Rede do navegador, a resposta de `/api/acomodacoes/busca` traz o cabeçalho `Server-Timing: app;dur=...` (em milissegundos). O teste `tests/test_desempenho.py` mede o p95 com 3.000 acomodações.

**M10. Acessibilidade e responsividade (RNF-14, RNF-16).**
- Navegue só com Tab: o primeiro item é "Pular para o conteúdo" e o foco fica sempre visível.
- Reduza a janela para 360 px: não deve aparecer rolagem horizontal.
- O botão **?** (ajuda) está em todas as telas.

## Limitações conhecidas

- O login é simulado e o servidor é o de desenvolvimento do Flask, sem HTTPS. A `SECRET_KEY` é aleatória a cada execução quando a variável de ambiente não está definida, então reiniciar o app desfaz a troca de usuário.
- O mapa é um desenho esquemático (SVG) feito sem biblioteca externa, porque o serviço de mapas é simulado.
- A acessibilidade seguiu boas práticas WCAG 2.1 AA, mas não passou por auditoria com ferramenta nem por teste com leitor de tela.
- SQLite atende à demonstração, mas não ao RNF-03 (10.000 usuários simultâneos).
