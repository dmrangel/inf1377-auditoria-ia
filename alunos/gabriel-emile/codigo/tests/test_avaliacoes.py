"""Avaliações exibidas (RF-15, UC20, 4.6.2-3, RN-06)."""
from datetime import timedelta

import pytest

from conftest import AGORA


def avaliacoes(client, acomodacao_id):
    r = client.get(f"/api/acomodacoes/{acomodacao_id}/avaliacoes")
    assert r.status_code == 200
    return r.get_json()


def test_rf15_media_e_comentarios_da_acomodacao(client):
    r = avaliacoes(client, 1)
    assert r["notaMedia"] == pytest.approx(4.67)
    assert r["totalAvaliacoes"] == 3
    assert [a["nota"] for a in r["avaliacoes"]] == [5, 4, 5]  # mais recente primeiro


def test_avaliacao_do_anfitriao_sobre_hospede_nao_aparece(client):
    textos = [a["comentario"] for a in avaliacoes(client, 1)["avaliacoes"]]
    assert "Hóspede exemplar." not in textos
    assert "Recomendo a hóspede." not in textos


def test_so_avaliacao_do_anfitriao_nao_gera_nota(client):
    r = avaliacoes(client, 16)
    assert r["totalAvaliacoes"] == 0 and r["notaMedia"] is None and r["avaliacoes"] == []


def test_comentario_e_opcional(client):
    r = avaliacoes(client, 1)
    assert any(a["comentario"] is None for a in r["avaliacoes"])


def test_autor_exibido_so_pelo_primeiro_nome(client):
    autores = {a["autor"] for a in avaliacoes(client, 1)["avaliacoes"]}
    assert autores == {"Ana", "Elisa", "Diego"}


def test_avaliacao_nao_publicada_nao_aparece_nem_conta(client, buscar):
    """#13: só a hóspede avaliou e o check-out foi há 3 dias (prazo de 14 dias aberto)."""
    r = avaliacoes(client, 13)
    assert r["totalAvaliacoes"] == 0 and r["avaliacoes"] == []
    item = buscar(bairro="Leblon").get_json()["itens"][0]
    assert item["notaMedia"] is None


def test_avaliacao_publicada_apos_fim_do_prazo_de_14_dias(app, client):
    # Check-out do #13 foi em hoje-3: ainda dá para avaliar até hoje-3+14 = hoje+11.
    app.config["AGORA"] = AGORA + timedelta(days=11)
    assert avaliacoes(client, 13)["totalAvaliacoes"] == 0
    app.config["AGORA"] = AGORA + timedelta(days=12)
    r = avaliacoes(client, 13)
    assert r["totalAvaliacoes"] == 1 and r["notaMedia"] == 2


def test_avaliacao_publicada_quando_ambos_avaliam(client):
    # #12: reserva 106 tem avaliação do hóspede e do anfitrião
    r = avaliacoes(client, 12)
    assert r["totalAvaliacoes"] == 1 and r["notaMedia"] == 3


def test_nota_media_igual_na_busca_e_no_anuncio(client, buscar):
    item = next(i for i in buscar().get_json()["itens"] if i["id"] == 3)
    detalhe = client.get("/api/acomodacoes/3").get_json()
    assert item["notaMedia"] == detalhe["avaliacoes"]["notaMedia"] == 4.5


def test_avaliacoes_de_anuncio_oculto_retornam_404(client, entrar):
    entrar(None)
    assert client.get("/api/acomodacoes/9/avaliacoes").status_code == 404
