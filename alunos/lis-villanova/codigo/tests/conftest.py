"""
Configuração dos testes.

Cada teste recebe um banco SQLite NOVO numa pasta temporária do pytest
(tmp_path), nunca o hospedagem.db do app, e sem os dados de exemplo:
cada teste cria só o que precisa.
"""

from datetime import datetime, timezone

import pytest

import app as modulo_app
import tempo
import usuarios
from database import conectar

SENHA = "Senha123"


@pytest.fixture
def app(tmp_path):
    caminho = tmp_path / "teste.db"
    assert str(caminho) != modulo_app.BANCO_PADRAO  # banco separado do app
    aplicacao = modulo_app.create_app({
        "TESTING": True,
        "DATABASE": str(caminho),
        "POPULAR_DADOS_EXEMPLO": False,
        "SECRET_KEY": "chave-de-teste",
    })
    yield aplicacao


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def conn(app):
    c = conectar(app.config["DATABASE"])
    yield c
    c.close()


@pytest.fixture
def caixa(app):
    """Serviço de e-mail simulado do app (para conferir o que foi 'enviado')."""
    return app.extensions["email"]


class Relogio:
    """Relógio controlável: substitui tempo.agora_utc nos testes de tempo."""

    def __init__(self, monkeypatch):
        self.agora = datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc)
        monkeypatch.setattr(tempo, "agora_utc", lambda: self.agora)

    def avancar(self, delta):
        self.agora = self.agora + delta


@pytest.fixture
def relogio(monkeypatch):
    return Relogio(monkeypatch)


def criar_usuario(conn, email="ana@teste.com", senha=SENHA, nome="Ana Teste",
                  telefone="21999998888", agora=None):
    """Cadastra pela regra de negócio real e devolve (id, token_confirmacao)."""
    return usuarios.cadastrar(conn, nome, email, senha, telefone, True, agora=agora)


def entrar(client, email="ana@teste.com", senha=SENHA):
    return client.post("/api/login", json={"email": email, "senha": senha})
