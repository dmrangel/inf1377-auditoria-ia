"""Calendário de disponibilidade (ERS 3.1, 4.3.2-3; RF-10; RN-04)."""
from datetime import date

from conftest import HOJE, dia


def situacoes(client, acomodacao_id, meses=3):
    r = client.get(f"/api/acomodacoes/{acomodacao_id}/calendario",
                   query_string={"mes": HOJE.strftime("%Y-%m"), "meses": meses})
    assert r.status_code == 200
    return {d["data"]: d["situacao"] for m in r.get_json()["meses"] for d in m["dias"]}


def test_reserva_confirmada_ocupa_noites_e_libera_dia_de_saida(client):
    s = situacoes(client, 2)  # CONFIRMADA +14..+18
    assert [s[dia(i)] for i in (13, 14, 17, 18)] == ["livre", "ocupado", "ocupado", "livre"]


def test_bloqueio_do_anfitriao_ocupa(client):
    s = situacoes(client, 1)  # bloqueio +25..+28
    assert [s[dia(i)] for i in (24, 25, 27, 28)] == ["livre", "ocupado", "ocupado", "livre"]


def test_pendente_valida_ocupa_e_vencida_nao(client):
    assert situacoes(client, 6)[dia(13)] == "ocupado"
    assert situacoes(client, 7)[dia(14)] == "livre"


def test_reserva_cancelada_nao_ocupa(client):
    assert situacoes(client, 2)[dia(10)] == "livre"


def test_dias_passados_marcados(client):
    s = situacoes(client, 1)
    primeiro = date(HOJE.year, HOJE.month, 1).isoformat()
    if primeiro < HOJE.isoformat():
        assert s[primeiro] == "passado"
    assert s[HOJE.isoformat()] in ("livre", "ocupado")


def test_calendario_nao_expoe_quem_reservou(client):
    corpo = client.get("/api/acomodacoes/2/calendario").get_json()
    for m in corpo["meses"]:
        for d in m["dias"]:
            assert set(d) == {"data", "situacao"}


def test_parametros_invalidos_do_calendario(client):
    base = "/api/acomodacoes/1/calendario"
    assert client.get(base, query_string={"mes": "2030-13"}).status_code == 400
    assert client.get(base, query_string={"mes": "abc"}).status_code == 400
    assert client.get(base, query_string={"mes": "2029-01"}).status_code == 400  # antes do mês atual
    assert client.get(base, query_string={"mes": "2035-01"}).status_code == 400  # além de 24 meses
    assert client.get(base, query_string={"meses": "7"}).status_code == 400
    assert client.get(base, query_string={"meses": "0"}).status_code == 400


def test_calendario_padrao_comeca_no_mes_atual(client):
    corpo = client.get("/api/acomodacoes/1/calendario").get_json()
    assert corpo["meses"][0]["mes"] == HOJE.strftime("%Y-%m")
    assert len(corpo["meses"]) == 2


def test_calendario_de_anuncio_oculto_404(client, entrar):
    entrar(None)
    assert client.get("/api/acomodacoes/8/calendario").status_code == 404
