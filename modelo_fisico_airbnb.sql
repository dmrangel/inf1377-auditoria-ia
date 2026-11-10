-- =============================================================
-- INF1377 - Engenharia de Requisitos - Airbnb
-- Modelo FISICO (MySQL) para importar no Visual Paradigm:
--   Tools > DB > Reverse DDL...  (Database: MySQL, Generate ERD marcado)
-- Baseado no diagrama de classes "Pra Platform Booking Flow".
-- =============================================================

-- -------------------------------------------------------------
-- Tabelas de dominio (enumeracoes do diagrama de classes)
-- -------------------------------------------------------------

CREATE TABLE StatusReserva (
  id     INT         NOT NULL AUTO_INCREMENT,
  codigo VARCHAR(20) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE (codigo)
) COMMENT = 'Enum: PENDENTE, CONFIRMADA, CANCELADA, CONCLUIDA';

CREATE TABLE StatusPagamento (
  id     INT         NOT NULL AUTO_INCREMENT,
  codigo VARCHAR(20) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE (codigo)
) COMMENT = 'Enum: PROCESSANDO, APROVADO, RECUSADO, REEMBOLSADO';

CREATE TABLE MetodoPagamento (
  id     INT         NOT NULL AUTO_INCREMENT,
  codigo VARCHAR(20) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE (codigo)
) COMMENT = 'Enum: CARTAO_CREDITO, PIX';

-- -------------------------------------------------------------
-- Usuario e especializacoes (heranca: uma tabela por subclasse)
-- -------------------------------------------------------------

CREATE TABLE Usuario (
  id           INT          NOT NULL AUTO_INCREMENT,
  nome         VARCHAR(100) NOT NULL,
  email        VARCHAR(255) NOT NULL,
  senha        VARCHAR(255) NOT NULL,
  telefone     VARCHAR(15)  NOT NULL,
  dataCadastro DATETIME     NOT NULL,
  PRIMARY KEY (id),
  UNIQUE (email)
) COMMENT = 'Classe base. Um usuario pode ser Anfitriao e Hospede ao mesmo tempo (RN07)';

CREATE TABLE Anfitriao (
  usuarioId    INT          NOT NULL,
  superhost    BOOLEAN      NOT NULL DEFAULT FALSE,
  taxaResposta DECIMAL(5,2) NULL,
  PRIMARY KEY (usuarioId),
  CONSTRAINT fk_anfitriao_usuario FOREIGN KEY (usuarioId) REFERENCES Usuario (id)
) COMMENT = 'Especializacao de Usuario. taxaResposta nula ate haver historico';

CREATE TABLE Hospede (
  usuarioId INT NOT NULL,
  PRIMARY KEY (usuarioId),
  CONSTRAINT fk_hospede_usuario FOREIGN KEY (usuarioId) REFERENCES Usuario (id)
) COMMENT = 'Especializacao de Usuario, sem atributos proprios';

-- -------------------------------------------------------------
-- Acomodacao
-- -------------------------------------------------------------

CREATE TABLE Acomodacao (
  id               INT           NOT NULL AUTO_INCREMENT,
  anfitriaoId      INT           NOT NULL,
  titulo           VARCHAR(100)  NOT NULL,
  descricao        TEXT          NOT NULL,
  precoNoite       DECIMAL(10,2) NOT NULL,
  capacidadeMaxima INT           NOT NULL,
  qtdQuartos       INT           NOT NULL,
  qtdBanheiros     INT           NOT NULL,
  qtdCamas         INT           NOT NULL,
  regrasCasa       TEXT          NULL,
  rua              VARCHAR(150)  NOT NULL,
  numero           VARCHAR(10)   NOT NULL,
  bairro           VARCHAR(100)  NOT NULL,
  cidade           VARCHAR(100)  NOT NULL,
  estado           VARCHAR(50)   NOT NULL,
  pais             VARCHAR(50)   NOT NULL,
  cep              CHAR(8)       NOT NULL,
  ativa            BOOLEAN       NOT NULL DEFAULT TRUE,
  PRIMARY KEY (id),
  CONSTRAINT fk_acomodacao_anfitriao FOREIGN KEY (anfitriaoId) REFERENCES Anfitriao (usuarioId)
) COMMENT = 'Anfitriao gerencia 1..* acomodacoes (garantido por regra de negocio, RN01/RN08). ativa = remocao logica (UC07)';

-- -------------------------------------------------------------
-- Reserva e historico de status
-- -------------------------------------------------------------

CREATE TABLE Reserva (
  id                    INT           NOT NULL AUTO_INCREMENT,
  hospedeId             INT           NOT NULL,
  acomodacaoId          INT           NOT NULL,
  dataCheckInPrevista   DATE          NOT NULL,
  dataCheckOutPrevista  DATE          NOT NULL,
  dataCheckInRealizada  DATETIME      NULL,
  dataCheckOutRealizada DATETIME      NULL,
  valorTotal            DECIMAL(10,2) NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_reserva_hospede    FOREIGN KEY (hospedeId)    REFERENCES Hospede (usuarioId),
  CONSTRAINT fk_reserva_acomodacao FOREIGN KEY (acomodacaoId) REFERENCES Acomodacao (id)
) COMMENT = 'Status atual = ultimo registro em HistoricoStatusReserva';

CREATE TABLE HistoricoStatusReserva (
  id              INT      NOT NULL AUTO_INCREMENT,
  reservaId       INT      NOT NULL,
  statusReservaId INT      NOT NULL,
  dataHora        DATETIME NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_historico_reserva FOREIGN KEY (reservaId)       REFERENCES Reserva (id),
  CONSTRAINT fk_historico_status  FOREIGN KEY (statusReservaId) REFERENCES StatusReserva (id)
) COMMENT = 'Toda alteracao de status da reserva gera um registro';

-- -------------------------------------------------------------
-- Pagamento
-- -------------------------------------------------------------

CREATE TABLE Pagamento (
  id                INT           NOT NULL AUTO_INCREMENT,
  reservaId         INT           NOT NULL,
  statusPagamentoId INT           NOT NULL,
  metodoPagamentoId INT           NOT NULL,
  valor             DECIMAL(10,2) NOT NULL,
  codigoAutorizacao VARCHAR(50)   NULL,
  dataHora          DATETIME      NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_pagamento_reserva FOREIGN KEY (reservaId)         REFERENCES Reserva (id),
  CONSTRAINT fk_pagamento_status  FOREIGN KEY (statusPagamentoId) REFERENCES StatusPagamento (id),
  CONSTRAINT fk_pagamento_metodo  FOREIGN KEY (metodoPagamentoId) REFERENCES MetodoPagamento (id)
) COMMENT = 'Reserva 1..* Pagamento: cada tentativa gera um registro (RN09 permite 0 enquanto PENDENTE)';

-- -------------------------------------------------------------
-- Avaliacao
-- -------------------------------------------------------------

CREATE TABLE Avaliacao (
  id            INT          NOT NULL AUTO_INCREMENT,
  reservaId     INT          NOT NULL,
  tipoAutor     VARCHAR(10)  NOT NULL,
  nota          INT          NOT NULL,
  comentario    VARCHAR(500) NULL,
  dataAvaliacao DATE         NOT NULL,
  PRIMARY KEY (id),
  UNIQUE (reservaId, tipoAutor),
  CONSTRAINT fk_avaliacao_reserva FOREIGN KEY (reservaId) REFERENCES Reserva (id)
) COMMENT = 'tipoAutor = HOSPEDE ou ANFITRIAO. UNIQUE(reservaId, tipoAutor) garante no maximo 2 por reserva (0..2, RN05)';
