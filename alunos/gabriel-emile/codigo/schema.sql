-- Esquema do banco (SQLite), baseado no Apêndice B.4 da ERS v1.2.
-- Os nomes de tabelas e colunas seguem o B.4. As tabelas marcadas com
-- [EXTENSÃO] não existem no B.4 e foram criadas por necessidade
-- (ver AMBIGUIDADES.md, itens A07 e A08).
-- As tabelas pagamento e historico_status_pagamento do B.4 não são criadas
-- porque a busca/visualização não as usa (o status da reserva já basta).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuario (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    senhaHash     TEXT    NOT NULL,
    telefone      TEXT,
    dataCadastro  TEXT    NOT NULL,
    ehAnfitriao   INTEGER NOT NULL DEFAULT 0,
    superhost     INTEGER NOT NULL DEFAULT 0,
    taxaResposta  REAL
);

CREATE TABLE IF NOT EXISTS acomodacao (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    anfitriao_id     INTEGER NOT NULL REFERENCES usuario(id),
    titulo           TEXT    NOT NULL,
    descricao        TEXT    NOT NULL,
    precoNoite       REAL    NOT NULL CHECK (precoNoite > 0),
    capacidadeMaxima INTEGER NOT NULL CHECK (capacidadeMaxima >= 1),
    quartos          INTEGER NOT NULL CHECK (quartos >= 0),
    banheiros        INTEGER NOT NULL CHECK (banheiros >= 0),
    camas            INTEGER NOT NULL CHECK (camas >= 0),
    regras           TEXT,
    cep              TEXT    NOT NULL,
    rua              TEXT    NOT NULL,
    numero           TEXT    NOT NULL,
    bairro           TEXT    NOT NULL,
    cidade           TEXT    NOT NULL,
    estado           TEXT    NOT NULL,
    ativo            INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS reserva (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    hospede_id    INTEGER NOT NULL REFERENCES usuario(id),
    acomodacao_id INTEGER NOT NULL REFERENCES acomodacao(id),
    checkIn       TEXT    NOT NULL,   -- AAAA-MM-DD
    checkOut      TEXT    NOT NULL,   -- AAAA-MM-DD (dia de saída, não ocupa a noite)
    numHospedes   INTEGER NOT NULL,
    valorTotal    REAL    NOT NULL,
    status        TEXT    NOT NULL CHECK (status IN ('PENDENTE','CONFIRMADA','CANCELADA','CONCLUIDA'))
);

CREATE TABLE IF NOT EXISTS historico_status_reserva (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    reserva_id     INTEGER NOT NULL REFERENCES reserva(id),
    statusAnterior TEXT,
    statusNovo     TEXT    NOT NULL,
    dataHora       TEXT    NOT NULL,  -- AAAA-MM-DDTHH:MM:SS
    responsavel_id INTEGER REFERENCES usuario(id)
);

CREATE TABLE IF NOT EXISTS avaliacao (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    reserva_id    INTEGER NOT NULL REFERENCES reserva(id),
    autor_id      INTEGER NOT NULL REFERENCES usuario(id),
    nota          INTEGER NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario    TEXT,
    dataAvaliacao TEXT    NOT NULL,
    UNIQUE (reserva_id, autor_id)
);

CREATE TABLE IF NOT EXISTS denuncia (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    autor_id      INTEGER NOT NULL REFERENCES usuario(id),
    acomodacao_id INTEGER REFERENCES acomodacao(id),
    motivo        TEXT    NOT NULL,
    descricao     TEXT,
    status        TEXT    NOT NULL,   -- EM_ANALISE, PROCEDENTE, IMPROCEDENTE
    parecer       TEXT,
    admin_id      INTEGER REFERENCES usuario(id)
);

-- [EXTENSÃO] RF-08 exige de 5 a 30 fotos, mas o B.4 não tem tabela de fotos.
-- "chave" é o identificador do arquivo no serviço de armazenamento (simulado).
CREATE TABLE IF NOT EXISTS foto_acomodacao (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    acomodacao_id INTEGER NOT NULL REFERENCES acomodacao(id),
    chave         TEXT    NOT NULL,
    legenda       TEXT,
    ordem         INTEGER NOT NULL DEFAULT 0
);

-- [EXTENSÃO] RF-10 (anfitrião bloqueia datas), sem tabela no B.4.
-- Intervalo semiaberto [dataInicio, dataFim), igual ao da reserva.
CREATE TABLE IF NOT EXISTS bloqueio_data (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    acomodacao_id INTEGER NOT NULL REFERENCES acomodacao(id),
    dataInicio    TEXT    NOT NULL,
    dataFim       TEXT    NOT NULL,
    CHECK (dataFim > dataInicio)
);

-- Índices para a busca (RNF-01). norm() é registrada pela aplicação (db.py)
-- e remove acentos/caixa; o índice de expressão permite usar o índice mesmo
-- comparando "Sao Paulo" com "São Paulo".
CREATE INDEX IF NOT EXISTS ix_acomodacao_cidade   ON acomodacao(norm(cidade), norm(bairro));
CREATE INDEX IF NOT EXISTS ix_reserva_acomodacao  ON reserva(acomodacao_id, status, checkIn, checkOut);
CREATE INDEX IF NOT EXISTS ix_bloqueio_acomodacao ON bloqueio_data(acomodacao_id, dataInicio, dataFim);
CREATE INDEX IF NOT EXISTS ix_avaliacao_reserva   ON avaliacao(reserva_id);
CREATE INDEX IF NOT EXISTS ix_foto_acomodacao     ON foto_acomodacao(acomodacao_id, ordem);
CREATE INDEX IF NOT EXISTS ix_denuncia_acomodacao ON denuncia(acomodacao_id, status);
CREATE INDEX IF NOT EXISTS ix_historico_reserva   ON historico_status_reserva(reserva_id);
