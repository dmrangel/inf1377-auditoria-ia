"""Configuração dos testes.

Cada teste usa um banco SQLite NOVO em uma pasta temporária (tmp_path),
separado do banco do app (instancia/plataforma.db), com os dados de seed.py
gerados a partir de uma data FIXA, para que os cenários sejam determinísticos.
"""
import os
import sys
from datetime import date, datetime, timedelta

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from app import create_app  # noqa: E402
from db import conectar  # noqa: E402
from seed import popular  # noqa: E402

AGORA = datetime(2030, 3, 10, 10, 0, 0)
HOJE = AGORA.date()

# Usuários do seed
ANA, BRUNO, CARLA, DIEGO, ELISA = 1, 2, 3, 4, 5


def dia(delta):
    return (HOJE + timedelta(days=delta)).isoformat()


@pytest.fixture
def app(tmp_path):
    caminho = str(tmp_path / "teste.db")
    app = create_app({
        "TESTING": True,
        "DATABASE": caminho,
        "SECRET_KEY": "chave-de-teste",
        "POPULAR_DADOS_EXEMPLO": False,
        "AGORA": AGORA,
    })
    con = conectar(caminho)
    popular(con, agora=AGORA)
    con.close()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def entrar(client):
    """Troca o usuário de teste (login simulado). entrar(None) = visitante."""
    def _entrar(usuario_id):
        r = client.post("/api/sessao", json={"usuario_id": usuario_id})
        assert r.status_code == 200
    return _entrar


def params_demo(**extra):
    """Cenário principal: Copacabana, hoje+14 a hoje+17, 2 hóspedes."""
    p = {
        "cidade": "Rio de Janeiro",
        "bairro": "Copacabana",
        "checkin": dia(14),
        "checkout": dia(17),
        "hospedes": "2",
    }
    p.update({k: v for k, v in extra.items() if v is not None})
    for k, v in list(extra.items()):
        if v is None:
            p.pop(k, None)
    return p


@pytest.fixture
def buscar(client):
    def _buscar(**extra):
        return client.get("/api/acomodacoes/busca", query_string=params_demo(**extra))
    return _buscar


def ids(resposta):
    return [i["id"] for i in resposta.get_json()["itens"]]


__all__ = ["AGORA", "HOJE", "dia", "params_demo", "ids", "date"]
