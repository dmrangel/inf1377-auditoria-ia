# Gerenciamento de acomodações

Implementação da funcionalidade **4.2 Gerenciamento de acomodações** da ERS v1.2 da Plataforma de Hospedagem: RF-07 a RF-11, serviço de CEP e armazenamento de arquivos (3.3), RNF-11 e os casos de uso UC05, UC06 e UC07.

- Back-end: Python 3 + Flask. Banco: SQLite, criado automaticamente.
- Front-end: HTML, CSS e JavaScript puro.
- [RASTREABILIDADE.md](RASTREABILIDADE.md): requisito → código → teste, mais os requisitos não implementados.
- [AMBIGUIDADES.md](AMBIGUIDADES.md): trechos ambíguos da ERS, a decisão tomada e a alternativa descartada.

## Como rodar

Requer Python 3.10 ou superior.

```powershell
cd alunos/julia-kymie/codigo
pip install -r requirements.txt
python app.py
```

Abra <http://127.0.0.1:5000>. Na primeira execução são criados `instancia/hospedagem.db` (banco com dados de exemplo) e `instancia/arquivos/` (fotos do armazenamento simulado). Para voltar ao estado inicial, pare o app e apague a pasta `instancia/`.

Para testar o upload com arquivos prontos (válidos e inválidos):

```powershell
python gerar_amostras.py
```

O comando cria a pasta `amostras/`.

## Testes automatizados

```powershell
python -m pytest
```

Cada teste usa um banco SQLite novo numa pasta temporária, **separado** do banco do app, com a data "hoje" fixada em 01/12/2026. São 114 testes. Para medir a cobertura (RNF-15 pede ≥ 70%):

```powershell
pip install pytest-cov
python -m pytest --cov=.
```

## Estrutura

```
app.py                     cria o app Flask, registra serviços e rotas
schema.sql                 tabelas (B.4 + foto + bloqueio_data)
banco.py                   conexão SQLite, criação do banco e dados de exemplo
autenticacao.py            login simulado (sessão) — RNF-09
dominio/acomodacoes.py     regras: UC05, UC06, UC07, RF-10, RF-11, RNF-11
dominio/validacao.py       validação de campos, fotos e datas
dominio/erros.py           erros de negócio → status HTTP + mensagem simples
servicos_externos/cep.py           serviço de CEP SIMULADO
servicos_externos/armazenamento.py armazenamento de arquivos SIMULADO
rotas/api.py               API REST/JSON
rotas/paginas.py           telas
templates/, static/        HTML, CSS e JS puro
tests/                     pytest
gerar_amostras.py          gera arquivos de teste para upload
```

## Login simulado e dados de exemplo

O login real (UC02) não faz parte da tarefa. No canto superior da tela há o seletor **"Logado como"**. Ao abrir uma tela pela primeira vez, o usuário é **Ana**. Todas as permissões são verificadas no servidor a partir da sessão; o navegador não decide nada. Sem sessão, a API responde 401. A sessão expira após 30 minutos sem uso (RNF-09).

| Usuário | Papel | Para que serve |
|---|---|---|
| **Ana Souza** | anfitriã (superhost) | dona de 3 acomodações; caminho feliz |
| **Bruno Lima** | anfitrião | dono do "Loft no centro de São Paulo"; testa o RNF-11 (Ana não pode mexer no dele, e vice-versa) |
| **Carla Dias** | só hóspede | testa o bloqueio de quem não é anfitrião |
| Diego Rocha | só hóspede | aparece como hóspede em reservas |

| Acomodação (dona) | Situação | Uso nos testes |
|---|---|---|
| 1. Apartamento em Copacabana (Ana) | ativo, 6 fotos, capacidade 4 | reservas em todos os status: **CONFIRMADA** daqui a 10 dias (4 noites, 4 hóspedes), **PENDENTE** daqui a 20 dias (3 noites), CONCLUIDA e CANCELADA |
| 2. Estúdio na Gávea (Ana) | ativo, **exatamente 5 fotos** | remover foto é recusado; noites bloqueadas daqui a 5 a 7 dias; sem reservas |
| 3. Casa em Ouro Preto (Ana) | **desativado**, 7 fotos | reativar; tem reserva CONFIRMADA futura |
| 4. Loft em São Paulo (Bruno) | ativo, 5 fotos | RNF-11 |

As datas das reservas são calculadas a partir do dia em que o banco é criado.

## Sistemas externos simulados

Ficam em módulos separados, com a interface que o cliente de um serviço real teria. Para trocar pelo serviço real, implemente a mesma classe e registre-a em `app.py::create_app`.

### Serviço de CEP — `servicos_externos/cep.py`

Interface: `buscar(cep) -> {cep, rua, bairro, cidade, estado}`. Pode lançar `CepInvalido`, `CepNaoEncontrado` ou `ServicoCepIndisponivel`.

| CEP digitado | Resposta simulada |
|---|---|
| `22451-900` | Rua Marquês de São Vicente, Gávea, Rio de Janeiro/RJ |
| `22071-001` | Avenida Atlântica, Copacabana, Rio de Janeiro/RJ |
| `01310-100` | Avenida Paulista, Bela Vista, São Paulo/SP |
| `30130-010` | Avenida Afonso Pena, Centro, Belo Horizonte/MG |
| `35400-000` | CEP geral de cidade: só Ouro Preto/MG; rua e bairro manuais |
| `99999-999` | **Serviço indisponível** (timeout simulado) |
| qualquer outro com 8 dígitos | **CEP não encontrado** (UC05, fluxo 3a) |
| sem 8 dígitos | **CEP inválido** |

### Armazenamento de arquivos — `servicos_externos/armazenamento.py`

Interface: `salvar(bytes, tipo, nome) -> chave`, `ler(chave)`, `remover(chave)`. Os arquivos ficam em `instancia/arquivos/` e são servidos em `/arquivos/<chave>`.

| Situação | Como provocar |
|---|---|
| Gravação normal | enviar JPEG ou PNG de até 10 MB |
| **Serviço indisponível** | enviar um arquivo cujo **nome** contenha `falha-armazenamento` (ex.: `amostras/falha-armazenamento.png`), ou iniciar com a variável de ambiente `FALHAR_ARMAZENAMENTO=1` |
| Arquivo recusado | tipo diferente de JPEG/PNG ou mais de 10 MB (o domínio já recusa antes) |

## Cenários de teste manual

Os códigos M0 a M18 são citados na [tabela de rastreabilidade](RASTREABILIDADE.md). Todos partem do banco recém-criado.

### Caminho feliz

- **M0 — Lista (RF-11).** Abra a tela inicial como Ana: aparecem as 3 acomodações dela, a de Ouro Preto como "Desativado". Cada uma tem a tabela das reservas recebidas (Copacabana mostra os 4 status). Troque para Bruno: só aparece o loft dele.
- **M1 — Anunciar espaço (UC05).** Clique em "Anunciar espaço" e informe o CEP `22451-900`. Clique em "Buscar CEP": rua, bairro, cidade e UF são preenchidos e ficam travados. Preencha número, título (≥ 5 caracteres), descrição (≥ 20), preço `250,00`, capacidade, quartos, banheiros, camas e regras. Escolha 5 fotos (`amostras/foto01.png` a `foto05.png`) e clique em "Publicar anúncio". A tela volta à lista com o novo anúncio "Publicado", que também aparece em "Anúncios publicados".
- **M9 — Editar (UC06).** Em Copacabana, clique em "Editar", mude o título e o preço e salve: aparece "Alterações salvas". As reservas antigas mantêm o valor que tinham.
- **M10 — Adicionar fotos.** Na edição, escolha mais fotos: elas são enviadas na hora e o contador sobe.
- **M13 — Desativar (UC07).** Na Gávea, clique em "Desativar" e confirme. O anúncio fica "Desativado" e some de "Anúncios publicados".
- **M14 — Reativar.** Em Ouro Preto, clique em "Reativar": ele volta para "Anúncios publicados". Lá só aparecem bairro e cidade, nunca rua e número (RNF-05).
- **M15 — Bloquear datas (RF-10).** Em "Calendário" da Gávea, clique em dois dias livres (ou digite as datas) e em "Bloquear noites": os dias ficam cinza-escuro. "Desbloquear noites" libera de novo.

### Erros e fluxos alternativos

- **M2 — CEP não encontrado (UC05 3a).** Use o CEP `20000-123`. Aparece "CEP não encontrado. Preencha o endereço manualmente." e os campos ficam livres. Sem preencher rua, bairro e cidade, a publicação é recusada com os campos destacados.
- **M3 — Serviço de CEP fora do ar.** CEP `99999-999`: mensagem de serviço indisponível. O endereço manual é aceito. Com o CEP `35400-000` só cidade e UF são preenchidas.
- **M4 — Campos inválidos.** Publique com título "Casa", preço `0` e camas `0`. O resumo de erros recebe o foco, cada campo fica destacado com sua mensagem, e os demais campos continuam preenchidos.
- **M5 — Menos de 5 fotos (UC05 5a).** Escolha 4 fotos e publique: "O anúncio precisa de no mínimo 5 fotos". Nada é gravado.
- **M6 — Mais de 30 fotos.** Escolha `foto01` a `foto31`: a tela aceita só 30 e avisa. Na edição de Copacabana (6 fotos), adicionar 25 de uma vez é recusado pelo servidor.
- **M7 — Tipo ou tamanho inválido.** `amostras/gif-disfarcado.png` passa pela tela, porque a extensão é .png, mas o **servidor** recusa ao ler a assinatura do arquivo: "não é JPEG nem PNG". `amostras/grande-11mb.png` é barrado na tela. Para ver o servidor recusar, chame a API (veja "Testar a API direto").
- **M8 — Armazenamento fora do ar.** Publique com 4 fotos válidas + `falha-armazenamento.png`: aparece "serviço de armazenamento indisponível" (503). O anúncio não é criado e nenhum arquivo fica órfão.
- **M11 — Remover foto abaixo do mínimo.** Na edição da Gávea (5 fotos), clique em "Remover" em qualquer foto: "O anúncio precisa ter no mínimo 5 fotos".
- **M12 — Capacidade menor que reserva.** Em Copacabana, mude a capacidade para 3 e salve. É recusado porque há reserva confirmada para 4 hóspedes (RN-02).
- **M13b — Desativar com reservas.** Em Copacabana, clique em "Desativar". Uma segunda confirmação lista as 2 reservas futuras e avisa que elas **não** serão canceladas.
- **M16 — Bloquear noite reservada.** No calendário de Copacabana, tente bloquear os dias da reserva confirmada (azuis). É recusado com o período da reserva. Datas passadas aparecem desabilitadas, e a API recusa bloqueá-las.
- **M17 — Permissões (RNF-11).** Como Ana, abra `/anfitriao/acomodacoes/4/editar` (o loft do Bruno): "Você não é o anfitrião desta acomodação". O mesmo vale para o calendário e as reservas. Como Carla (só hóspede), a lista e "Anunciar espaço" informam que a conta não tem o papel de anfitrião.
- **M18 — Ajuda e responsividade.** O botão "Ajuda" existe em todas as telas. Com a janela em 360 px, não há rolagem horizontal; a tabela de reservas rola dentro do cartão.

### Testar a API direto (curl)

```powershell
curl.exe -c c.txt -b c.txt -H "Content-Type: application/json" -d '{\"usuarioId\": 1}' http://127.0.0.1:5000/api/sessao
curl.exe -b c.txt -F "fotos=@amostras/grande-11mb.png" http://127.0.0.1:5000/api/acomodacoes/2/fotos
curl.exe -b c.txt http://127.0.0.1:5000/api/acomodacoes/4
```

O 1º comando entra como Ana. O 2º responde 400 (mais de 10 MB) e o 3º, 403 (RNF-11).

## API

| Método e rota | Função |
|---|---|
| `GET/POST/DELETE /api/sessao` | sessão simulada (`{"usuarioId": 1}`) |
| `GET /api/cep/<cep>` | consulta o serviço de CEP |
| `GET /api/minhas-acomodacoes` | RF-11 |
| `POST /api/acomodacoes` | UC05 (multipart: campos + `fotos`) |
| `GET/PUT /api/acomodacoes/<id>` | detalhe / UC06 (todos os campos) |
| `POST /api/acomodacoes/<id>/fotos`, `DELETE .../fotos/<fotoId>` | fotos (UC06) |
| `POST /api/acomodacoes/<id>/desativar` (`{"confirmar": true}`), `POST .../reativar` | UC07 / RF-09 |
| `GET /api/acomodacoes/<id>/reservas` | reservas recebidas |
| `GET /api/acomodacoes/<id>/calendario?mes=AAAA-MM` | noites bloqueadas e reservadas |
| `POST/DELETE /api/acomodacoes/<id>/bloqueios` (`{"inicio","fim"}`) | RF-10 |
| `GET /api/anuncios` | vitrine pública (só ativos, só bairro) |

Os erros seguem um formato único, com status 400, 401, 403, 404, 409 ou 503: `{"erro": "mensagem simples", "codigo": "...", "campos": {...}, "detalhes": [...]}`.

## Limitações conhecidas

- O login é simulado, e o servidor de desenvolvimento roda em HTTP, sem TLS.
- A `SECRET_KEY` é gerada a cada início do app (as sessões caem ao reiniciar). Para fixá-la, defina a variável de ambiente `SECRET_KEY`.
- Alterações em acomodações não geram registro de auditoria nem notificam hóspedes (ver [RASTREABILIDADE.md](RASTREABILIDADE.md#requisitos-relevantes-não-implementados-ou-só-em-parte)).
- A acessibilidade seguiu boas práticas da WCAG 2.1 AA, mas não passou por auditoria formal.
