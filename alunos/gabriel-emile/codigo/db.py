"""Acesso ao banco SQLite.

O banco é criado automaticamente na primeira execução (schema.sql + dados de
exemplo de seed.py). Os testes usam outro arquivo, passado em
app.config["DATABASE"].
"""
import os
import sqlite3
import unicodedata

from flask import current_app, g

AQUI = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(AQUI, "schema.sql")


def normalizar(texto):
    """Minúsculas, sem acentos e sem espaços extras.

    Usada para comparar localizações: "São Paulo", "sao paulo" e
    "SAO  PAULO" devem ser a mesma cidade (ver AMBIGUIDADES.md, A16).
    """
    if texto is None:
        return None
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def conectar(caminho):
    con = sqlite3.connect(caminho, detect_types=0)
    con.row_factory = sqlite3.Row
    # deterministic=True permite usar norm() em índice de expressão.
    con.create_function("norm", 1, normalizar, deterministic=True)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def get_db():
    if "db" not in g:
        g.db = conectar(current_app.config["DATABASE"])
    return g.db


def fechar_db(_erro=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def criar_esquema(con):
    with open(SCHEMA, encoding="utf-8") as f:
        con.executescript(f.read())
    con.commit()


def inicializar_se_preciso(caminho, popular=True):
    """Cria o arquivo do banco e, se estiver vazio, insere os dados de exemplo."""
    pasta = os.path.dirname(os.path.abspath(caminho))
    os.makedirs(pasta, exist_ok=True)
    con = conectar(caminho)
    try:
        criar_esquema(con)
        vazio = con.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 0
        if vazio and popular:
            from seed import popular as popular_dados
            popular_dados(con)
    finally:
        con.close()
