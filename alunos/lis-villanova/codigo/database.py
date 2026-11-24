"""
database.py - Conexão e criação do banco SQLite.

A tabela `usuario` segue o Apêndice B.4 da ERS v1.1 (id, nome, email único,
senhaHash, telefone, dataCadastro, ehAnfitriao). As colunas extras existem
porque requisitos da própria ERS precisam guardar estado que o B.4 não prevê;
cada uma está justificada em AMBIGUIDADES.md (item A-17).
"""

import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                  TEXT    NOT NULL,
    -- RF-02: e-mail único. COLLATE NOCASE impede "Ana@x.com" e "ana@x.com"
    -- mesmo que algum caminho esqueça de normalizar.
    email                 TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    -- RNF-07: só o hash com salt, nunca a senha.
    senhaHash             TEXT    NOT NULL,
    telefone              TEXT    NOT NULL,
    dataCadastro          TEXT    NOT NULL,
    -- RF-06: todo usuário é hóspede; o papel de anfitrião é ativado depois.
    ehAnfitriao           INTEGER NOT NULL DEFAULT 0 CHECK (ehAnfitriao IN (0, 1)),

    -- ---- Colunas além do B.4 (ver AMBIGUIDADES.md, A-17) ----
    dataAtivacaoAnfitriao TEXT,
    emailConfirmado       INTEGER NOT NULL DEFAULT 0 CHECK (emailConfirmado IN (0, 1)),
    -- RNF-18: registro do consentimento com termos de uso e política de privacidade.
    consentimentoTermosEm TEXT    NOT NULL,
    versaoTermos          TEXT    NOT NULL,
    -- RNF-10: falhas de login seguidas e fim do bloqueio.
    tentativasFalhas      INTEGER NOT NULL DEFAULT 0,
    bloqueadoAte          TEXT,
    -- Incrementada a cada troca de senha: sessões com versão antiga deixam de valer.
    versaoSessao          INTEGER NOT NULL DEFAULT 1
);

-- Links enviados por e-mail (confirmação de cadastro e recuperação de senha).
-- Guarda só o SHA-256 do token: quem lê o banco não consegue usar o link.
CREATE TABLE IF NOT EXISTS token_usuario (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuario (id) ON DELETE CASCADE,
    tipo       TEXT    NOT NULL CHECK (tipo IN ('CONFIRMACAO_EMAIL', 'RECUPERACAO_SENHA')),
    tokenHash  TEXT    NOT NULL UNIQUE,
    criadoEm   TEXT    NOT NULL,
    expiraEm   TEXT    NOT NULL,
    usadoEm    TEXT
);
"""


def conectar(caminho):
    """Abre uma conexão com linhas acessíveis por nome e chaves estrangeiras ativas."""
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    # O SQLite vem com FKs desligadas; sem isto o ON DELETE CASCADE não funciona.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """Conexão da requisição atual (uma por requisição, fechada no teardown)."""
    if "db" not in g:
        g.db = conectar(current_app.config["DATABASE"])
    return g.db


def fechar_db(_erro=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(caminho, popular=True):
    """Cria as tabelas se não existirem e, com o banco vazio, insere os dados de exemplo."""
    conn = conectar(caminho)
    try:
        conn.executescript(SCHEMA)
        vazio = conn.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 0
        if popular and vazio:
            # Import local para evitar import circular (dados_exemplo usa usuarios).
            from dados_exemplo import popular as popular_dados

            popular_dados(conn)
        conn.commit()
    finally:
        conn.close()
