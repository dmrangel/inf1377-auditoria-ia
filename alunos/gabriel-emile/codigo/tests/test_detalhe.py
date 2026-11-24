"""Página do anúncio (UC09; RNF-05; ERS 3.1; serviços externos simulados)."""
import pytest

from conftest import ANA, BRUNO, CARLA, DIEGO, dia

CAMPOS_ENDERECO = {"rua", "numero", "cep"}


def detalhe(client, acomodacao_id, **query):
    return client.get(f"/api/acomodacoes/{acomodacao_id}", query_string=query)


# --------------------------------------------------------------------------- conteúdo
def test_detalhe_tem_fotos_descricao_capacidade_regras(client):
    d = detalhe(client, 1).get_json()
    assert d["titulo"] == "Apartamento com vista para o mar"
    assert d["descricao"] and d["regras"]
    assert d["capacidadeMaxima"] == 4 and d["quartos"] == 2 and d["banheiros"] == 1 and d["camas"] == 3
    assert len(d["fotos"]) == 6
    assert d["avaliacoes"]["notaMedia"] == pytest.approx(4.67)
    assert d["anfitriao"] == {"nome": "Bruno", "superhost": True, "desde": d["anfitriao"]["desde"]}


def test_detalhe_nao_expoe_email_nem_telefone_do_anfitriao(client):
    texto = detalhe(client, 1).get_data(as_text=True)
    assert "bruno@teste.local" not in texto
    assert "99999" not in texto


def test_anuncio_inexistente_404(client):
    r = detalhe(client, 999)
    assert r.status_code == 404
    assert r.get_json()["erro"]


# --------------------------------------------------------------------------- RNF-05
@pytest.mark.parametrize("usuario, acomodacao, ve_endereco", [
    (None, 1, False),   # visitante
    (ANA, 1, True),     # Ana tem reserva CONFIRMADA no #1
    (ANA, 3, True),     # Ana tem reserva CONCLUIDA no #3 (passou por CONFIRMADA)
    (ANA, 2, False),    # Ana só tem reserva CANCELADA no #2
    (DIEGO, 15, False), # Diego só tem PENDENTE no #15
    (DIEGO, 6, False),  # PENDENTE válida também não dá direito
    (BRUNO, 2, True),   # dono do anúncio
    (CARLA, 1, False),  # outra anfitriã
    (ANA, 10, False),   # nenhuma reserva
])
def test_rnf05_endereco_exato_so_apos_confirmacao(client, entrar, usuario, acomodacao, ve_endereco):
    entrar(usuario)
    loc = detalhe(client, acomodacao).get_json()["localizacao"]
    assert loc["enderecoExato"] is ve_endereco
    assert bool(CAMPOS_ENDERECO & set(loc)) is ve_endereco
    assert loc["bairro"] and loc["cidade"]


def test_rnf05_endereco_nao_vaza_em_nenhum_lugar_da_resposta(client, entrar):
    entrar(None)
    for caminho in ("/api/acomodacoes/1", "/api/acomodacoes/1/avaliacoes", "/api/acomodacoes/1/calendario"):
        texto = client.get(caminho).get_data(as_text=True)
        assert "Atl" not in texto and "1702" not in texto and "22021" not in texto


def test_rnf05_mapa_sempre_aproximado_mesmo_com_reserva_confirmada(client, entrar):
    entrar(ANA)
    mapa = detalhe(client, 1).get_json()["localizacao"]["mapa"]
    assert mapa["raio_metros"] > 0
    assert "Atl" not in mapa["descricao"]


# --------------------------------------------------------------------------- visibilidade
def test_anuncio_desativado_404_para_publico_e_visivel_para_dono(client, entrar):
    entrar(ANA)
    assert detalhe(client, 8).status_code == 404
    entrar(BRUNO)
    r = detalhe(client, 8)
    assert r.status_code == 200
    assert r.get_json()["ativo"] is False and r.get_json()["ehDono"] is True


def test_anuncio_sob_denuncia_de_risco_oculto_para_publico(client, entrar):
    entrar(None)
    assert detalhe(client, 9).status_code == 404
    entrar(CARLA)
    assert detalhe(client, 9).status_code == 200


def test_anuncio_com_menos_de_5_fotos_oculto(client, entrar):
    entrar(None)
    assert detalhe(client, 11).status_code == 404


# --------------------------------------------------------------------------- período vindo da busca
def test_periodo_disponivel(client):
    p = detalhe(client, 1, checkin=dia(14), checkout=dia(17), hospedes=2).get_json()["periodo"]
    assert p["disponivel"] is True and p["noites"] == 3


def test_periodo_ocupado_informa(client):
    p = detalhe(client, 2, checkin=dia(14), checkout=dia(17), hospedes=2).get_json()["periodo"]
    assert p["livre"] is False and p["disponivel"] is False
    assert "não está livre" in p["mensagens"][0]


def test_periodo_acima_da_capacidade_informa(client):
    p = detalhe(client, 4, checkin=dia(14), checkout=dia(17), hospedes=2).get_json()["periodo"]
    assert p["cabe"] is False and p["disponivel"] is False


def test_periodo_invalido_retorna_erros_sem_quebrar_a_pagina(client):
    r = detalhe(client, 1, checkin=dia(14), checkout=dia(10))
    assert r.status_code == 200
    assert "checkout" in r.get_json()["periodo"]["erros"]


# --------------------------------------------------------------------------- serviço de mapas simulado
def test_mapa_sucesso(client):
    mapa = detalhe(client, 1).get_json()["localizacao"]["mapa"]
    assert mapa["disponivel"] is True
    assert mapa["latitude"] == pytest.approx(-22.9711)


def test_mapa_local_nao_encontrado(client):
    mapa = detalhe(client, 17).get_json()["localizacao"]["mapa"]
    assert mapa["disponivel"] is False and mapa["mensagem"]


def test_mapa_fora_do_ar_nao_derruba_a_pagina(app, client):
    app.extensions["servico_mapas"].falhar = True
    r = detalhe(client, 1)
    assert r.status_code == 200
    assert r.get_json()["localizacao"]["mapa"]["disponivel"] is False


# --------------------------------------------------------------------------- armazenamento simulado
def test_foto_servida_pelo_armazenamento(client):
    url = detalhe(client, 1).get_json()["fotos"][0]["url"]
    r = client.get(url)
    assert r.status_code == 200 and r.mimetype == "image/svg+xml"


def test_foto_ausente_404(client):
    urls = [f["url"] for f in detalhe(client, 15).get_json()["fotos"]]
    ausente = next(u for u in urls if "ausente" in u)
    assert client.get(ausente).status_code == 404


def test_armazenamento_fora_do_ar_503(app, client):
    app.extensions["armazenamento"].falhar = True
    assert client.get("/arquivos/fotos/1/fachada.svg").status_code == 503
