"""RF-10 (bloquear datas), RF-11 (listar acomodações e reservas), RNF-05, sessão."""

from datetime import timedelta

from conftest import (BRUNO, CARLA, COPA, GAVEA, HOJE, OURO, PAULISTA, entrar)


def d(dias):
    return (HOJE + timedelta(days=dias)).isoformat()


# ------------------------------------------------------------------ RF-10

def test_bloquear_periodo_livre(ana):
    r = ana.post(f"/api/acomodacoes/{GAVEA}/bloqueios", json={"inicio": d(20), "fim": d(22)})
    assert r.status_code == 201 and r.json["noitesBloqueadas"] == 3
    cal = ana.get(f"/api/acomodacoes/{GAVEA}/calendario?mes={d(20)[:7]}").json
    assert d(20) in cal["bloqueadas"]


def test_bloquear_de_novo_nao_duplica(ana):
    """GAVEA já tem d(5)..d(7) bloqueadas nos dados de exemplo."""
    r = ana.post(f"/api/acomodacoes/{GAVEA}/bloqueios", json={"inicio": d(6), "fim": d(8)})
    assert r.status_code == 201 and r.json["noitesBloqueadas"] == 1


def test_uma_noite_so(ana):
    r = ana.post(f"/api/acomodacoes/{GAVEA}/bloqueios", json={"inicio": d(1), "fim": d(1)})
    assert r.json["noitesBloqueadas"] == 1


def test_nao_bloqueia_noite_com_reserva_ativa(ana):
    """COPA: reserva CONFIRMADA de d(10) a d(14) (noites 10..13)."""
    r = ana.post(f"/api/acomodacoes/{COPA}/bloqueios", json={"inicio": d(13), "fim": d(15)})
    assert r.status_code == 409
    assert r.json["detalhes"][0]["status"] == "CONFIRMADA"


def test_dia_do_checkout_pode_ser_bloqueado(ana):
    """A noite do dia do check-out (d(14)) não pertence à reserva."""
    assert ana.post(f"/api/acomodacoes/{COPA}/bloqueios", json={"inicio": d(14), "fim": d(14)}).status_code == 201


def test_nao_bloqueia_noite_com_reserva_pendente(ana):
    """COPA: reserva PENDENTE de d(20) a d(23)."""
    assert ana.post(f"/api/acomodacoes/{COPA}/bloqueios", json={"inicio": d(19), "fim": d(20)}).status_code == 409


def test_reserva_cancelada_nao_impede_bloqueio(ana):
    """COPA: reserva CANCELADA de d(30) a d(32)."""
    assert ana.post(f"/api/acomodacoes/{COPA}/bloqueios", json={"inicio": d(30), "fim": d(31)}).status_code == 201


def test_nao_bloqueia_data_passada(ana):
    r = ana.post(f"/api/acomodacoes/{GAVEA}/bloqueios", json={"inicio": d(-1), "fim": d(2)})
    assert r.status_code == 400


def test_fim_antes_do_inicio(ana):
    assert ana.post(f"/api/acomodacoes/{GAVEA}/bloqueios", json={"inicio": d(5), "fim": d(4)}).status_code == 400


def test_data_invalida(ana):
    assert ana.post(f"/api/acomodacoes/{GAVEA}/bloqueios", json={"inicio": "31/12/2026", "fim": d(4)}).status_code == 400
    assert ana.post(f"/api/acomodacoes/{GAVEA}/bloqueios", json={}).status_code == 400


def test_limite_de_366_noites(ana):
    assert ana.post(f"/api/acomodacoes/{GAVEA}/bloqueios", json={"inicio": d(0), "fim": d(365)}).status_code == 201
    assert ana.post(f"/api/acomodacoes/{GAVEA}/bloqueios", json={"inicio": d(0), "fim": d(366)}).status_code == 400


def test_desbloquear(ana):
    r = ana.delete(f"/api/acomodacoes/{GAVEA}/bloqueios", json={"inicio": d(5), "fim": d(7)})
    assert r.status_code == 200 and r.json["noitesDesbloqueadas"] == 3


def test_bloquear_em_anuncio_desativado(ana):
    assert ana.post(f"/api/acomodacoes/{OURO}/bloqueios", json={"inicio": d(1), "fim": d(2)}).status_code == 201


def test_calendario_mostra_reservadas(ana):
    cal = ana.get(f"/api/acomodacoes/{COPA}/calendario?mes={d(10)[:7]}").json
    assert cal["reservadas"][d(10)]["status"] == "CONFIRMADA"
    assert d(14) not in cal["reservadas"]  # dia do check-out livre


def test_calendario_mes_invalido(ana):
    assert ana.get(f"/api/acomodacoes/{COPA}/calendario?mes=2026-13").status_code == 400


# ------------------------------------------------------------------ RF-11

def test_lista_traz_todas_as_acomodacoes_do_anfitriao_e_so_dele(ana):
    lista = ana.get("/api/minhas-acomodacoes").json
    assert sorted(a["id"] for a in lista) == [COPA, GAVEA, OURO]
    assert PAULISTA not in [a["id"] for a in lista]


def test_lista_traz_reservas_em_todos_os_status(ana):
    copa = next(a for a in ana.get("/api/minhas-acomodacoes").json if a["id"] == COPA)
    assert {r["status"] for r in copa["reservas"]} == {"CONFIRMADA", "PENDENTE", "CONCLUIDA", "CANCELADA"}


def test_lista_nao_expoe_contato_do_hospede(ana):
    copa = next(a for a in ana.get("/api/minhas-acomodacoes").json if a["id"] == COPA)
    reserva = copa["reservas"][0]
    assert "hospede" in reserva
    assert not any(k in reserva for k in ("email", "telefone", "hospede_id"))


def test_bruno_ve_so_as_dele(cliente):
    entrar(cliente, BRUNO)
    lista = cliente.get("/api/minhas-acomodacoes").json
    assert [a["id"] for a in lista] == [PAULISTA]


def test_hospede_sem_papel_de_anfitriao_recebe_403_na_lista(cliente):
    entrar(cliente, CARLA)
    assert cliente.get("/api/minhas-acomodacoes").status_code == 403


# ------------------------------------------------------------------ RNF-05 e vitrine

def test_vitrine_nao_mostra_endereco_exato_nem_inativos(cliente):
    anuncios = cliente.get("/api/anuncios").json  # sem login
    assert OURO not in [a["id"] for a in anuncios]
    for a in anuncios:
        assert "rua" not in a and "numero" not in a and "cep" not in a
        assert a["bairro"]


# ------------------------------------------------------------------ CEP e sessão

def test_consulta_cep(ana):
    assert ana.get("/api/cep/22451900").json["bairro"] == "Gávea"
    assert ana.get("/api/cep/20000123").status_code == 404
    assert ana.get("/api/cep/99999999").status_code == 503
    assert ana.get("/api/cep/123").status_code == 400


def test_consulta_cep_exige_login(cliente):
    assert cliente.get("/api/cep/22451900").status_code == 401


def test_sessao_e_sair(ana):
    assert ana.get("/api/sessao").json["nome"] == "Ana Souza"
    assert ana.delete("/api/sessao").status_code == 204
    assert ana.get("/api/sessao").status_code == 401


def test_sessao_expira_em_30_minutos(app):
    """RNF-09."""
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(minutes=30)
    assert app.config["SESSION_REFRESH_EACH_REQUEST"] is True


def test_entrar_com_usuario_inexistente(cliente):
    assert cliente.post("/api/sessao", json={"usuarioId": 999}).status_code == 404


def test_paginas_abrem_e_fazem_login_de_teste(cliente):
    for url in ["/anfitriao/acomodacoes", "/anfitriao/acomodacoes/nova",
                f"/anfitriao/acomodacoes/{COPA}/editar", f"/anfitriao/acomodacoes/{COPA}/calendario", "/anuncios"]:
        assert cliente.get(url).status_code == 200
    assert cliente.get("/api/sessao").json["id"] == 1  # Ana, usuário de teste padrão


def test_senhas_dos_exemplos_tem_hash(app):
    """RNF-07 (só para os dados de exemplo; cadastro de usuário está fora da tarefa)."""
    import sqlite3
    con = sqlite3.connect(app.config["DATABASE"])
    for (senha,) in con.execute("SELECT senhaHash FROM usuario"):
        assert senha != "senha123" and ":" in senha
    con.close()
