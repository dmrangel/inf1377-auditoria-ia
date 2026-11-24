-- Esquema do banco (SQLite). Segue o projeto de tabelas da ERS v1.2, Apêndice B.4.
-- Tabelas "foto" e "bloqueio_data" NÃO existem no B.4: foram acrescentadas para
-- atender RF-08 e RF-10 (ver AMBIGUIDADES.md, itens A05 e A06).
-- As tabelas pagamento, avaliacao, denuncia e historico_status_pagamento não são
-- usadas por esta funcionalidade e por isso não foram criadas.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuario (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    senhaHash     TEXT    NOT NULL,
    telefone      TEXT,
    dataCadastro  TEXT    NOT NULL,
    ehAnfitriao   INTEGER NOT NULL DEFAULT 0 CHECK (ehAnfitriao IN (0, 1)),
    superhost     INTEGER NOT NULL DEFAULT 0 CHECK (superhost IN (0, 1)),
    taxaResposta  REAL
);

CREATE TABLE IF NOT EXISTS acomodacao (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    anfitriao_id      INTEGER NOT NULL REFERENCES usuario(id),
    titulo            TEXT    NOT NULL,
    descricao         TEXT    NOT NULL,
    -- Guardado em CENTAVOS (inteiro) para evitar erro de arredondamento (decisão A13).
    precoNoite        INTEGER NOT NULL CHECK (precoNoite > 0),
    capacidadeMaxima  INTEGER NOT NULL CHECK (capacidadeMaxima >= 1),
    quartos           INTEGER NOT NULL CHECK (quartos >= 0),
    banheiros         INTEGER NOT NULL CHECK (banheiros >= 1),
    camas             INTEGER NOT NULL CHECK (camas >= 1),
    regras            TEXT    NOT NULL,
    cep               TEXT    NOT NULL,
    rua               TEXT    NOT NULL,
    numero            TEXT    NOT NULL,
    bairro            TEXT    NOT NULL,
    cidade            TEXT    NOT NULL,
    estado            TEXT    NOT NULL,
    ativo             INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

-- Fotos do anúncio (RF-08). O arquivo em si fica no serviço de armazenamento
-- (simulado); aqui guardamos só a chave devolvida por ele.
CREATE TABLE IF NOT EXISTS foto (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    acomodacao_id   INTEGER NOT NULL REFERENCES acomodacao(id),
    chave           TEXT    NOT NULL UNIQUE,
    tipoConteudo    TEXT    NOT NULL CHECK (tipoConteudo IN ('image/jpeg', 'image/png')),
    tamanhoBytes    INTEGER NOT NULL,
    ordem           INTEGER NOT NULL,
    dataEnvio       TEXT    NOT NULL
);

-- Datas bloqueadas pelo anfitrião (RF-10). Uma linha por NOITE bloqueada:
-- a data D bloqueia a noite de D para D+1 (decisão A07).
CREATE TABLE IF NOT EXISTS bloqueio_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    acomodacao_id   INTEGER NOT NULL REFERENCES acomodacao(id),
    data            TEXT    NOT NULL,
    UNIQUE (acomodacao_id, data)
);

CREATE TABLE IF NOT EXISTS reserva (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    hospede_id      INTEGER NOT NULL REFERENCES usuario(id),
    acomodacao_id   INTEGER NOT NULL REFERENCES acomodacao(id),
    checkIn         TEXT    NOT NULL,
    checkOut        TEXT    NOT NULL,
    numHospedes     INTEGER NOT NULL,
    valorTotal      INTEGER NOT NULL,   -- centavos
    status          TEXT    NOT NULL CHECK (status IN ('PENDENTE','CONFIRMADA','CANCELADA','CONCLUIDA'))
);

CREATE TABLE IF NOT EXISTS historico_status_reserva (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reserva_id      INTEGER NOT NULL REFERENCES reserva(id),
    statusAnterior  TEXT,
    statusNovo      TEXT    NOT NULL,
    dataHora        TEXT    NOT NULL,
    responsavel_id  INTEGER REFERENCES usuario(id)
);

CREATE INDEX IF NOT EXISTS idx_acomodacao_anfitriao ON acomodacao(anfitriao_id);
CREATE INDEX IF NOT EXISTS idx_foto_acomodacao      ON foto(acomodacao_id);
CREATE INDEX IF NOT EXISTS idx_reserva_acomodacao   ON reserva(acomodacao_id);
