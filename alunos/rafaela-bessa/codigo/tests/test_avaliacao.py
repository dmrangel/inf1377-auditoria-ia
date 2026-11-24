"""
tests/test_avaliacao.py - Testes automatizados da Avaliação de Estadia (pytest)
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
Cobre RF-15, RF-29 a RF-32, RN-06, UC18, UC19, seção 4.4.2 passo 3, seção 4.6.2,
RNF-22 e a correção da Tela 3 para reservas CONCLUIDAS.

Usuários do seed: 1 Lucas (hóspede), 2 Ana (hóspede), 3 Carlos (anfitrião das
acomodações 1 e 3), 4 Mariana (anfitriã superhost da acomodação 2).
"""

from datetime import date, timedelta

import pytest

import avaliacoes
import database
import models
from app import app
from services.email_service import EmailService

LUCAS, ANA, CARLOS, MARIANA = 1, 2, 3, 4
COPACABANA, IPANEMA, CHALE = 1, 2, 3


@pytest.fixture(autouse=True)
def banco_novo():
    database.init_db(force_recreate=True)
    EmailService.clear()
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        entrar(c, LUCAS)
        yield c


def entrar(client, usuario_id):
    """Simula o seletor de usuário de teste (sessão autenticada)."""
    with client.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = usuario_id
        sess["usuario_nome"] = f"Usuário {usuario_id}"


def sair(client):
    with client.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = None


def reserva_seed(hospede_id, acomodacao_id, dias_checkout, status=None):
    """Id de uma reserva do seed pelo hóspede, acomodação e check-out relativo a hoje."""
    conn = database.get_db_connection()
    try:
        checkout = (date.today() + timedelta(days=dias_checkout)).isoformat()
        sql = "SELECT id FROM reserva WHERE hospede_id = ? AND acomodacao_id = ? AND checkOut = ?"
        params = [hospede_id, acomodacao_id, checkout]
        if status:
            sql += " AND status = ?"
            params.append(status)
        row = conn.execute(sql, params).fetchone()
        assert row, "cenário do seed não encontrado"
        return row["id"]
    finally:
        conn.close()


def status_reserva(reserva_id):
    conn = database.get_db_connection()
    try:
        return conn.execute("SELECT status FROM reserva WHERE id = ?", (reserva_id,)).fetchone()["status"]
    finally:
        conn.close()


def avaliar(client, reserva_id, nota, comentario=None):
    return client.post(f"/api/reservas/{reserva_id}/avaliacoes", json={"nota": nota, "comentario": comentario})


def mover_hoje(monkeypatch, dias):
    """Simula a passagem do tempo só no módulo de avaliação."""
    monkeypatch.setattr(avaliacoes, "hoje", lambda: date.today() + timedelta(days=dias))


def convites():
    return [e for e in EmailService.get_sent_emails() if e["tipo"] == "CONVITE_AVALIACAO"]


# Cenários do seed (ver seed_avaliacoes.py)
def cenario_a():   # Lucas em Copacabana, check-out D-2, CONFIRMADA
    return reserva_seed(LUCAS, COPACABANA, -2)


def cenario_b():   # Lucas em Ipanema, D-5, Mariana já avaliou
    return reserva_seed(LUCAS, IPANEMA, -5)


def cenario_c():   # Lucas no Chalé, D-14 (último dia do prazo)
    return reserva_seed(LUCAS, CHALE, -14)


def cenario_d():   # Lucas no Chalé, D-20 (prazo encerrado, só Lucas avaliou)
    return reserva_seed(LUCAS, CHALE, -20)


def cenario_e():   # Lucas em Copacabana, CANCELADA
    return reserva_seed(LUCAS, COPACABANA, -10, "CANCELADA")


def cenario_g():   # Carlos hospedado na própria acomodação
    return reserva_seed(CARLOS, COPACABANA, -7)


# ===========================================================================
# Seção 4.4.2 passo 3 e 4.6.2 passo 1: conclusão automática e convite
# ===========================================================================

def test_conclusao_automatica_apos_checkout_com_convite_e_auditoria():
    rid = cenario_a()
    assert status_reserva(rid) == "CONFIRMADA"

    concluidas = avaliacoes.concluir_reservas_encerradas()

    assert concluidas == [rid]
    assert status_reserva(rid) == "CONCLUIDA"

    # RNF-22: mudança registrada com data, hora e responsável nulo (automática)
    conn = database.get_db_connection()
    hist = conn.execute(
        "SELECT * FROM historico_status_reserva WHERE reserva_id = ? AND statusNovo = 'CONCLUIDA'", (rid,)
    ).fetchall()
    conn.close()
    assert len(hist) == 1
    assert hist[0]["statusAnterior"] == "CONFIRMADA"
    assert hist[0]["responsavel_id"] is None
    assert hist[0]["dataHora"]

    # Convite para hóspede e anfitrião, com o prazo da RN-06 e o link
    enviados = convites()
    assert {e["destinatario"] for e in enviados} == {"hospede_teste@exemplo.com", "carlos_anfitriao@exemplo.com"}
    prazo = (date.today() + timedelta(days=12)).isoformat()
    assert all(prazo in e["corpo"] and f"/reservas/{rid}/avaliar" in e["corpo"] for e in enviados)

    # Idempotente: a segunda chamada não conclui de novo nem reenvia convites
    assert avaliacoes.concluir_reservas_encerradas() == []
    assert len(convites()) == 2


def test_conclusao_so_depois_do_dia_do_checkout(monkeypatch):
    res = models.criar_reserva(LUCAS, COPACABANA, "2030-01-10", "2030-01-12", 2)
    models.confirmar_reserva_apos_pagamento(res["reserva_id"])
    data_checkout = date(2030, 1, 12)

    monkeypatch.setattr(avaliacoes, "hoje", lambda: data_checkout)
    avaliacoes.concluir_reservas_encerradas()
    assert status_reserva(res["reserva_id"]) == "CONFIRMADA"   # no dia do check-out ainda não passou

    monkeypatch.setattr(avaliacoes, "hoje", lambda: data_checkout + timedelta(days=1))
    avaliacoes.concluir_reservas_encerradas()
    assert status_reserva(res["reserva_id"]) == "CONCLUIDA"


def test_pendente_e_cancelada_nunca_viram_concluida(monkeypatch):
    res = models.criar_reserva(LUCAS, IPANEMA, "2030-02-01", "2030-02-03", 1)   # fica PENDENTE
    mover_hoje(monkeypatch, 3650)
    avaliacoes.concluir_reservas_encerradas()
    assert status_reserva(res["reserva_id"]) == "PENDENTE"
    assert status_reserva(cenario_e()) == "CANCELADA"


def test_sem_convite_se_o_prazo_ja_terminou_quando_a_reserva_e_concluida():
    conn = database.get_db_connection()
    checkout = (date.today() - timedelta(days=20)).isoformat()
    checkin = (date.today() - timedelta(days=22)).isoformat()
    cur = conn.execute(
        "INSERT INTO reserva (hospede_id, acomodacao_id, checkIn, checkOut, numHospedes, valorTotal, status, dataCriacao) "
        "VALUES (?, ?, ?, ?, 1, 100, 'CONFIRMADA', '2026-01-01T00:00:00')",
        (ANA, IPANEMA, checkin, checkout)
    )
    rid = cur.lastrowid
    conn.commit()
    conn.close()

    avaliacoes.concluir_reservas_encerradas()

    assert status_reserva(rid) == "CONCLUIDA"
    assert not [e for e in convites() if e["reserva_id"] == rid]


# ===========================================================================
# UC18 / UC19 - caminho feliz, publicação e nota média (RF-29, RF-32)
# ===========================================================================

def test_caminho_feliz_hospede_e_anfitriao_avaliam(client):
    rid = cenario_a()
    antes = avaliacoes.resumo_notas_acomodacao(COPACABANA)
    assert antes == {"media": 5.0, "total": 1}   # só a avaliação publicada da Ana

    resp = avaliar(client, rid, 3, "  Boa localização, mas o chuveiro falhou.  ")
    assert resp.status_code == 201
    dados = resp.get_json()["avaliacao"]
    assert dados["papel"] == "HOSPEDE"
    assert dados["publicada"] is False
    assert dados["comentario"] == "Boa localização, mas o chuveiro falhou."   # espaços removidos
    assert dados["dataAvaliacao"]
    # RF-32 + publicação: a média não muda enquanto a avaliação está oculta
    assert dados["nota_media_acomodacao"] == {"media": 5.0, "total": 1}

    entrar(client, CARLOS)
    resp = avaliar(client, rid, 5)
    assert resp.status_code == 201
    dados = resp.get_json()["avaliacao"]
    assert dados["papel"] == "ANFITRIAO"
    assert dados["publicada"] is True
    # Agora as duas estão publicadas: média da acomodação = (5 + 3) / 2
    assert dados["nota_media_acomodacao"] == {"media": 4.0, "total": 2}


def test_publicacao_quando_a_segunda_parte_avalia(client):
    rid = cenario_b()
    assert avaliacoes.resumo_notas_acomodacao(IPANEMA) == {"media": 4.0, "total": 1}

    # Antes: a avaliação da Mariana sobre Lucas está oculta
    painel = avaliacoes.painel_do_usuario(LUCAS)
    assert not [r for r in painel["recebidas"] if r["reserva_id"] == rid]
    situacao = avaliacoes.situacao_para_usuario(rid, LUCAS)
    assert situacao["outra_avaliacao"] is None
    assert situacao["outra_parte_ja_avaliou"] is True

    resp = avaliar(client, rid, 5, "Vista incrível.")
    assert resp.status_code == 201
    assert resp.get_json()["avaliacao"]["publicada"] is True
    assert avaliacoes.resumo_notas_acomodacao(IPANEMA) == {"media": 4.5, "total": 2}

    painel = avaliacoes.painel_do_usuario(LUCAS)
    recebida = [r for r in painel["recebidas"] if r["reserva_id"] == rid]
    assert recebida and recebida[0]["nota"] == 5
    assert avaliacoes.situacao_para_usuario(rid, LUCAS)["outra_avaliacao"]["autor_id"] == MARIANA


def test_avaliacao_oculta_nao_aparece_na_pagina_publica(client):
    rid = cenario_a()
    avaliar(client, rid, 1, "COMENTARIO-SECRETO")

    pagina = client.get(f"/acomodacoes/{COPACABANA}/avaliacoes").get_data(as_text=True)
    assert "COMENTARIO-SECRETO" not in pagina
    api = client.get(f"/api/acomodacoes/{COPACABANA}/avaliacoes").get_json()
    assert all(a["comentario"] != "COMENTARIO-SECRETO" for a in api["avaliacoes"])

    # Para o anfitrião, só aparece que o hóspede já avaliou, não o conteúdo
    situacao = avaliacoes.situacao_para_usuario(rid, CARLOS)
    assert situacao["outra_parte_ja_avaliou"] is True
    assert situacao["outra_avaliacao"] is None


def test_publicacao_pelo_fim_do_prazo(client, monkeypatch):
    # Cenário D: só Lucas avaliou e o prazo já terminou -> publicada e na média
    assert avaliacoes.resumo_notas_acomodacao(CHALE) == {"media": 4.0, "total": 1}

    # Cenário C: Lucas avalia no último dia; Carlos não avalia
    rid = cenario_c()
    assert avaliar(client, rid, 2).status_code == 201
    assert avaliacoes.resumo_notas_acomodacao(CHALE) == {"media": 4.0, "total": 1}

    mover_hoje(monkeypatch, 1)   # o prazo de C termina
    assert avaliacoes.resumo_notas_acomodacao(CHALE) == {"media": 3.0, "total": 2}


def test_nota_media_do_hospede_para_o_anfitriao(client):
    # UC19: Carlos, ao avaliar Lucas, vê a nota que Lucas recebeu de outros anfitriões.
    assert avaliacoes.situacao_para_usuario(cenario_a(), CARLOS)["nota_hospede"] == {"media": None, "total": 0}
    avaliar(client, cenario_b(), 4)   # publica a nota 5 que Mariana deu a Lucas
    assert avaliacoes.situacao_para_usuario(cenario_a(), CARLOS)["nota_hospede"] == {"media": 5.0, "total": 1}


# ===========================================================================
# RF-29: nota e comentário
# ===========================================================================

@pytest.mark.parametrize("nota", [0, 6, -1, 4.5, "abc", "", True, None, [5]])
def test_rf29_nota_invalida(client, nota):
    resp = avaliar(client, cenario_a(), nota)
    assert resp.status_code == 400
    assert "nota de 1 a 5" in resp.get_json()["mensagem"]


def test_rf29_nota_em_texto_e_comentario_vazio(client):
    resp = avaliar(client, cenario_a(), "4", "   ")
    assert resp.status_code == 201
    conn = database.get_db_connection()
    row = conn.execute("SELECT nota, comentario FROM avaliacao WHERE reserva_id = ? AND autor_id = ?",
                       (cenario_a(), LUCAS)).fetchone()
    conn.close()
    assert row["nota"] == 4 and row["comentario"] is None


def test_rf29_comentario_longo_ou_invalido(client):
    rid = cenario_a()
    resp = avaliar(client, rid, 4, "x" * (avaliacoes.COMENTARIO_MAX_CARACTERES + 1))
    assert resp.status_code == 400
    assert "no máximo" in resp.get_json()["mensagem"]
    assert avaliar(client, rid, 4, 123).status_code == 400
    assert avaliar(client, rid, 4, "x" * avaliacoes.COMENTARIO_MAX_CARACTERES).status_code == 201


def test_check_da_nota_no_banco():
    conn = database.get_db_connection()
    with pytest.raises(Exception):
        conn.execute("INSERT INTO avaliacao (reserva_id, autor_id, nota, dataAvaliacao) VALUES (?, ?, 9, 'x')",
                     (cenario_e(), LUCAS))
    conn.close()


def test_corpo_que_nao_e_json(client):
    resp = client.post(f"/api/reservas/{cenario_a()}/avaliacoes", data="nota=5")
    assert resp.status_code == 400


# ===========================================================================
# RF-30, RF-31, RN-06
# ===========================================================================

def test_rf30_reserva_nao_concluida(client):
    entrar(client, ANA)
    resp = avaliar(client, 1, 5)   # reserva do seed original: D+20, CONFIRMADA
    assert resp.status_code == 400
    assert "ainda não terminou" in resp.get_json()["mensagem"]


def test_rf30_reserva_cancelada(client):
    resp = avaliar(client, cenario_e(), 5)
    assert resp.status_code == 400
    assert "canceladas" in resp.get_json()["mensagem"]


def test_rf31_uma_avaliacao_por_participante(client):
    entrar(client, MARIANA)
    resp = avaliar(client, cenario_b(), 4)   # Mariana já avaliou no seed
    assert resp.status_code == 409

    entrar(client, LUCAS)
    rid = cenario_a()
    assert avaliar(client, rid, 4).status_code == 201
    assert avaliar(client, rid, 5).status_code == 409
    conn = database.get_db_connection()
    total = conn.execute("SELECT COUNT(*) FROM avaliacao WHERE reserva_id = ? AND autor_id = ?",
                         (rid, LUCAS)).fetchone()[0]
    conn.close()
    assert total == 1


def test_rn06_ultimo_dia_ainda_vale(client):
    assert avaliar(client, cenario_c(), 5).status_code == 201


def test_rn06_prazo_encerrado(client, monkeypatch):
    entrar(client, CARLOS)
    resp = avaliar(client, cenario_d(), 3)
    assert resp.status_code == 400
    assert "RN-06" in resp.get_json()["mensagem"]

    entrar(client, LUCAS)
    mover_hoje(monkeypatch, 1)   # o 15º dia depois do check-out de C
    assert avaliar(client, cenario_c(), 5).status_code == 400


# ===========================================================================
# Permissões (verificadas no servidor)
# ===========================================================================

def test_quem_nao_participa_nao_avalia(client):
    entrar(client, ANA)
    resp = avaliar(client, cenario_a(), 5)
    assert resp.status_code == 403

    resp = client.get(f"/reservas/{cenario_a()}/avaliar")
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/avaliacoes")


def test_visitante_ve_pagina_publica_da_acomodacao(client):
    sair(client)
    resp = client.get(f"/acomodacoes/{COPACABANA}/avaliacoes")
    assert resp.status_code == 200 and "5,0" in resp.get_data(as_text=True)


def test_sem_login_e_reserva_inexistente(client):
    assert avaliar(client, 99999, 5).status_code == 404
    sair(client)
    assert avaliar(client, cenario_a(), 5).status_code == 401
    resp = client.get("/avaliacoes")
    assert resp.status_code == 401 and "Entre para continuar" in resp.get_data(as_text=True)


def test_anfitriao_hospedado_na_propria_acomodacao(client):
    rid = cenario_g()
    entrar(client, CARLOS)
    resp = avaliar(client, rid, 5)
    assert resp.status_code == 400
    assert "anfitrião desta acomodação" in resp.get_json()["mensagem"]
    assert rid not in [p["id"] for p in avaliacoes.painel_do_usuario(CARLOS)["pendentes"]]


# ===========================================================================
# Telas
# ===========================================================================

def test_tela_minhas_avaliacoes_lista_convites(client):
    pagina = client.get("/avaliacoes").get_data(as_text=True)
    assert "Aguardando sua avaliação (3)" in pagina   # cenários A, B e C
    assert f"/reservas/{cenario_a()}/avaliar" in pagina
    assert "Hoje é o último dia para avaliar" in pagina   # cenário C
    assert 'class="contador-pendentes"' in pagina


def test_tela_avaliar_mostra_formulario_ou_bloqueio(client):
    pagina = client.get(f"/reservas/{cenario_a()}/avaliar").get_data(as_text=True)
    assert 'id="formAvaliacao"' in pagina and "Como foi sua estadia?" in pagina

    entrar(client, CARLOS)
    pagina = client.get(f"/reservas/{cenario_a()}/avaliar").get_data(as_text=True)
    assert "Como foi receber" in pagina

    pagina = client.get(f"/reservas/{cenario_d()}/avaliar").get_data(as_text=True)
    assert 'id="formAvaliacao"' not in pagina and "prazo para avaliar terminou" in pagina


def test_tela_avaliacoes_da_acomodacao_e_tela_1(client):
    pagina = client.get(f"/acomodacoes/{COPACABANA}/avaliacoes").get_data(as_text=True)
    assert "5,0" in pagina and "Apartamento impecável" in pagina

    pagina = client.get(f"/resumo?acomodacao_id={IPANEMA}").get_data(as_text=True)
    assert "4,0" in pagina and f"/acomodacoes/{IPANEMA}/avaliacoes" in pagina

    assert client.get("/acomodacoes/999/avaliacoes").status_code == 404
    assert client.get("/api/acomodacoes/999/avaliacoes").status_code == 404


# ===========================================================================
# Correção do fluxo de reserva: Tela 3 aceita reserva CONCLUIDA
# ===========================================================================

def test_confirmacao_aceita_reserva_concluida_com_endereco(client):
    rid = cenario_a()
    avaliacoes.concluir_reservas_encerradas()
    assert status_reserva(rid) == "CONCLUIDA"

    resp = client.get(f"/confirmacao/{rid}")
    assert resp.status_code == 200
    pagina = resp.get_data(as_text=True)
    assert "Avenida Atlântica" in pagina and "22021-001" in pagina   # RNF-05*: endereço completo
    assert "ESTADIA CONCLUÍDA" in pagina

    resp = client.get(f"/pagamento/{rid}")
    assert resp.status_code == 302 and f"/confirmacao/{rid}" in resp.headers["Location"]


def test_confirmacao_continua_bloqueando_cancelada(client):
    resp = client.get(f"/confirmacao/{cenario_e()}")
    assert resp.status_code == 302
