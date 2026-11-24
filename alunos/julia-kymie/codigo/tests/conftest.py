"""Cada teste roda num banco SQLite NOVO dentro de uma pasta temporária,
separado do banco do app (instancia/hospedagem.db)."""

import io
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from imagens import png_numerado  # noqa: E402

HOJE = date(2026, 12, 1)

# IDs criados pelos dados de exemplo (banco.py)
ANA, BRUNO, CARLA, DIEGO = 1, 2, 3, 4
COPA, GAVEA, OURO, PAULISTA = 1, 2, 3, 4


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "teste.db"),
        "DIRETORIO_ARQUIVOS": str(tmp_path / "arquivos"),
        "HOJE": lambda: HOJE,
        "SECRET_KEY": "teste",
    })
    yield app


@pytest.fixture
def cliente(app):
    return app.test_client()


def entrar(cliente, usuario_id):
    r = cliente.post("/api/sessao", json={"usuarioId": usuario_id})
    assert r.status_code == 200
    return cliente


@pytest.fixture
def ana(cliente):
    return entrar(cliente, ANA)


def dados_validos(**mudancas):
    dados = {
        "titulo": "Quarto aconchegante na Gávea",
        "descricao": "Quarto com cama de casal, perto do Jardim Botânico e da PUC.",
        "precoNoite": "200,00",
        "capacidadeMaxima": "2",
        "quartos": "1",
        "banheiros": "1",
        "camas": "1",
        "regras": "Proibido fumar.",
        "cep": "22451-900",
        "rua": "",
        "numero": "100",
        "bairro": "",
        "cidade": "",
        "estado": "RJ",
    }
    dados.update(mudancas)
    return dados


def arquivos_png(n, prefixo="foto"):
    return [(io.BytesIO(png_numerado(i)), f"{prefixo}{i}.png") for i in range(n)]


def form_com_fotos(dados, fotos):
    corpo = dict(dados)
    corpo["fotos"] = fotos
    return corpo
