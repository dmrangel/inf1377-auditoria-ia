"""Login simulado e páginas HTML."""
from conftest import ANA

from db import normalizar


def test_usuario_padrao_e_o_hospede_de_teste(client):
    assert client.get("/api/sessao").get_json()["usuario"]["id"] == ANA


def test_trocar_para_visitante(client, entrar):
    entrar(None)
    assert client.get("/api/sessao").get_json()["usuario"] is None


def test_usuario_inexistente_ou_invalido(client):
    assert client.post("/api/sessao", json={"usuario_id": 999}).status_code == 404
    assert client.post("/api/sessao", json={"usuario_id": "1"}).status_code == 400
    assert client.post("/api/sessao", json={"usuario_id": True}).status_code == 400


def test_login_simulado_desligado_bloqueia_troca(app, client):
    app.config["LOGIN_SIMULADO"] = False
    assert client.post("/api/sessao", json={"usuario_id": 2}).status_code == 404
    assert client.get("/api/usuarios-teste").status_code == 404


def test_lista_de_usuarios_de_teste(client):
    nomes = [u["nome"] for u in client.get("/api/usuarios-teste").get_json()]
    assert "Ana Souza" in nomes and "Bruno Lima" in nomes


def test_paginas_html_respondem(client):
    for caminho in ("/", "/busca", "/acomodacao/1", "/ajuda"):
        r = client.get(caminho)
        assert r.status_code == 200
        assert b'class="botao-ajuda"' in r.data  # ERS 3.1: ajuda em todas as telas
        assert b'lang="pt-BR"' in r.data


def test_normalizar():
    assert normalizar("  São   PAULO ") == "sao paulo"
    assert normalizar("Gávea") == "gavea"
    assert normalizar(None) is None
