"""
tests/test_cancelamento.py - Testes do cancelamento de reserva e do reembolso (pytest)
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
ERS v1.2: RF-21, RF-25, RF-27, Seção 4.4.2 (seq. 4), Seção 4.5.1, RN-05, UC12, RNF-11, RNF-22.

Os testes rodam num banco temporário separado do banco do app (ver tests/conftest.py).
"""

import re
from datetime import date, datetime, timedelta

import pytest

import cancelamento
import database
import models
from app import app
from cancelamento import CancelamentoErro
from services.email_service import EmailService
from services.payment_gateway import PaymentGateway

# Usuários do seed (database.seed_test_data)
LUCAS, ANA, CARLOS, MARIANA = 1, 2, 3, 4
# Acomodações do seed do cancelamento: 5 = Carlos (R$ 300, comum), 6 = Mariana (R$ 400, superhost)
ACOM_COMUM, ACOM_SUPERHOST = 5, 6
# Reservas do seed do cancelamento (database.seed_cancelamento), na ordem de criação
C1_INTEGRAL, C2_TARDIA_PIX, C3_SUPERHOST, C4_FALHA_GATEWAY = 2, 3, 4, 5
C5_PENDENTE, C6_CANCELADA, C7_CONCLUIDA, C8_CHECKOUT_PASSOU, C9_EM_ANDAMENTO = 6, 7, 8, 9, 10


@pytest.fixture(autouse=True)
def banco_limpo():
    database.init_db(force_recreate=True)
    EmailService.clear()
    PaymentGateway.reiniciar_simulacao()
    yield
    PaymentGateway.reiniciar_simulacao()


def _cliente(usuario_id):
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = usuario_id
        sess["usuario_nome"] = f"Usuário {usuario_id}"
    return client


@pytest.fixture
def lucas():
    return _cliente(LUCAS)


def _dia(delta):
    return (date.today() + timedelta(days=delta)).strftime("%Y-%m-%d")


def _reserva_paga(acomodacao_id=ACOM_COMUM, inicio=100, noites=3, hospede_id=LUCAS,
                  metodo="CARTAO_CREDITO", txid=None):
    """Cria uma reserva pelo fluxo de reserva existente e a confirma com um pagamento aprovado."""
    res = models.criar_reserva(hospede_id, acomodacao_id, _dia(inicio), _dia(inicio + noites), 2)
    rid = res["reserva_id"]
    models.registrar_tentativa_pagamento(
        reserva_id=rid, txid=txid or f"TX-TESTE-{rid}", metodo=metodo, valor=res["valor_total"],
        status="APROVADO", codigo_autorizacao="AUTH-TESTE", token_cartao=None, responsavel_id=hospede_id)
    models.confirmar_reserva_apos_pagamento(rid)
    return rid, res


def _pagamentos(reserva_id):
    conn = database.get_db_connection()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM pagamento WHERE reserva_id = ? ORDER BY id", (reserva_id,)).fetchall()]
    finally:
        conn.close()


def _historico_reserva(reserva_id):
    conn = database.get_db_connection()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM historico_status_reserva WHERE reserva_id = ? ORDER BY id", (reserva_id,)).fetchall()]
    finally:
        conn.close()


def _status(reserva_id):
    return models.obter_reserva_completa(reserva_id)["status"]


def _instante_checkin(reserva_id):
    return cancelamento.instante_checkin(models.obter_reserva_completa(reserva_id)["checkIn"])


# ===========================================================================
# 1. Política de reembolso (RN-05, UC12 2a) - função pura
# ===========================================================================

CHECKIN = "2027-01-10"            # instante do check-in: 10/01/2027 14:00 (AMB-01)
LIMITE_48H = datetime(2027, 1, 8, 14, 0, 0)


def test_rn05_hospede_com_48h_ou_mais_recebe_reembolso_integral():
    r = cancelamento.calcular_reembolso("HOSPEDE", CHECKIN, 1026.00, 900.00, agora=datetime(2027, 1, 1, 9, 0))
    assert r["regra"] == "HOSPEDE_INTEGRAL"
    assert r["valor_reembolso"] == 1026.00      # AMB-02: integral inclui a taxa de serviço
    assert r["valor_retido"] == 0.00


def test_rn05_limite_exato_de_48h_ainda_e_integral():
    """RN-05 diz "até 48 horas antes": exatamente 48 h ainda dá reembolso integral."""
    r = cancelamento.calcular_reembolso("HOSPEDE", CHECKIN, 1026.00, 900.00, agora=LIMITE_48H)
    assert r["regra"] == "HOSPEDE_INTEGRAL"
    assert r["valor_reembolso"] == 1026.00


def test_rn05_hospede_com_menos_de_48h_recebe_50_por_cento_das_diarias():
    r = cancelamento.calcular_reembolso("HOSPEDE", CHECKIN, 1026.00, 900.00,
                                        agora=LIMITE_48H + timedelta(seconds=1))
    assert r["regra"] == "HOSPEDE_PARCIAL"
    assert r["valor_reembolso"] == 450.00       # 50% de R$ 900 de diárias
    assert r["valor_retido"] == 576.00          # outros 50% das diárias + a taxa de R$ 126


def test_rn05_superhost_50_por_cento_das_diarias_cheias():
    """O desconto do superhost (RN-07) é na taxa; as diárias são cheias, então 50% de R$ 800."""
    r = cancelamento.calcular_reembolso("HOSPEDE", CHECKIN, 900.80, 800.00,
                                        agora=LIMITE_48H + timedelta(hours=1))
    assert r["valor_reembolso"] == 400.00


def test_uc12_2a_anfitriao_cancela_hospede_recebe_integral_mesmo_em_cima_da_hora():
    r = cancelamento.calcular_reembolso("ANFITRIAO", CHECKIN, 1026.00, 900.00,
                                        agora=datetime(2027, 1, 10, 13, 0))
    assert r["regra"] == "ANFITRIAO_INTEGRAL"
    assert r["valor_reembolso"] == 1026.00


def test_sem_pagamento_aprovado_nao_ha_reembolso():
    for papel in ("HOSPEDE", "ANFITRIAO"):
        r = cancelamento.calcular_reembolso(papel, CHECKIN, 0, 900.00, agora=datetime(2027, 1, 1))
        assert r["regra"] == "SEM_PAGAMENTO"
        assert r["valor_reembolso"] == 0.00


def test_reembolso_nunca_passa_do_valor_pago_e_arredonda_centavos():
    r = cancelamento.calcular_reembolso("HOSPEDE", CHECKIN, 30.00, 100.00, agora=LIMITE_48H + timedelta(hours=1))
    assert r["valor_reembolso"] == 30.00
    r = cancelamento.calcular_reembolso("HOSPEDE", CHECKIN, 500.00, 100.01, agora=LIMITE_48H + timedelta(hours=1))
    assert r["valor_reembolso"] == 50.01        # 50,005 arredonda para cima


def test_papel_do_usuario_rf21_rnf11():
    reserva = {"hospede_id": LUCAS, "anfitriao_id": CARLOS}
    assert cancelamento.papel_do_usuario(reserva, LUCAS) == "HOSPEDE"
    assert cancelamento.papel_do_usuario(reserva, CARLOS) == "ANFITRIAO"
    assert cancelamento.papel_do_usuario(reserva, ANA) is None
    assert cancelamento.papel_do_usuario(reserva, None) is None
    # AMB-11: a mesma pessoa nos dois papéis é tratada como hóspede
    assert cancelamento.papel_do_usuario({"hospede_id": CARLOS, "anfitriao_id": CARLOS}, CARLOS) == "HOSPEDE"


# ===========================================================================
# 2. Pré-condições do UC12 e permissões (RF-21, RNF-11)
# ===========================================================================

@pytest.mark.parametrize("usuario", [ANA, MARIANA])
def test_rf21_rnf11_quem_nao_e_parte_da_reserva_nao_cancela(usuario):
    rid, _ = _reserva_paga()
    with pytest.raises(CancelamentoErro) as e:
        cancelamento.cancelar_reserva(rid, usuario)
    assert e.value.http_status == 403
    assert _status(rid) == "CONFIRMADA"
    assert len(_pagamentos(rid)) == 1


@pytest.mark.parametrize("reserva_id,status", [(C6_CANCELADA, "CANCELADA"), (C7_CONCLUIDA, "CONCLUIDA")])
def test_uc12_so_pendente_ou_confirmada_pode_ser_cancelada(reserva_id, status):
    with pytest.raises(CancelamentoErro) as e:
        cancelamento.obter_previa_cancelamento(reserva_id, LUCAS)
    assert e.value.http_status == 409
    assert e.value.codigo == "STATUS_NAO_CANCELAVEL"
    assert _status(reserva_id) == status


def test_reserva_com_checkout_passado_nao_pode_ser_cancelada():
    with pytest.raises(CancelamentoErro) as e:
        cancelamento.cancelar_reserva(C8_CHECKOUT_PASSOU, LUCAS)
    assert e.value.codigo == "ESTADIA_ENCERRADA"
    assert _status(C8_CHECKOUT_PASSOU) == "CONFIRMADA"


def test_reserva_inexistente():
    with pytest.raises(CancelamentoErro) as e:
        cancelamento.obter_previa_cancelamento(9999, LUCAS)
    assert e.value.http_status == 404


def test_rn04_pendente_vencida_ja_foi_cancelada_e_nao_cancela_de_novo():
    conn = database.get_db_connection()
    cur = conn.execute("""
        INSERT INTO reserva (hospede_id, acomodacao_id, checkIn, checkOut, numHospedes, valorTotal, status, dataCriacao)
        VALUES (?, ?, ?, ?, 2, 684.0, 'PENDENTE', ?)
    """, (LUCAS, ACOM_COMUM, _dia(120), _dia(122), (datetime.now() - timedelta(minutes=35)).isoformat()))
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    with pytest.raises(CancelamentoErro) as e:
        cancelamento.cancelar_reserva(rid, LUCAS)
    assert e.value.codigo == "STATUS_NAO_CANCELAVEL"
    assert _historico_reserva(rid)[-1]["responsavel_id"] is None   # cancelada pela RN-04, não pelo usuário


# ===========================================================================
# 3. Fluxo principal do UC12 (passos 4 e 5), RF-25, RF-27, Seção 4.5.1, RNF-22
# ===========================================================================

def test_uc12_hospede_cancela_com_antecedencia_reembolso_integral_registrado():
    rid, res = _reserva_paga(inicio=100, noites=3)       # 3 x 300 + 14% = 1026,00
    resultado = cancelamento.cancelar_reserva(rid, LUCAS)

    assert resultado["status"] == "CANCELADA"
    assert resultado["cancelado_por"] == "HOSPEDE"
    assert resultado["reembolso"]["valor_reembolso"] == res["valor_total"] == 1026.00
    assert _status(rid) == "CANCELADA"

    # Seção 4.5.1 e RF-25: o reembolso é um novo pagamento da reserva, com status REEMBOLSADO
    original, reembolso = _pagamentos(rid)
    assert original["status"] == "APROVADO"                    # original preservado (RNF-19)
    assert reembolso["status"] == "REEMBOLSADO"
    assert reembolso["valor"] == 1026.00
    assert reembolso["metodo"] == original["metodo"]
    assert reembolso["txid"].startswith(f"REF-{rid}-")
    assert reembolso["codigoAutorizacao"].startswith("EST-")
    assert reembolso["tokenCartao"] is None

    # RNF-22: histórico com data, hora e responsável
    ultimo = _historico_reserva(rid)[-1]
    assert (ultimo["statusAnterior"], ultimo["statusNovo"], ultimo["responsavel_id"]) == ("CONFIRMADA", "CANCELADA", LUCAS)
    assert ultimo["dataHora"]
    conn = database.get_db_connection()
    hist_pag = conn.execute("SELECT * FROM historico_status_pagamento WHERE pagamento_id = ?",
                            (reembolso["id"],)).fetchall()
    conn.close()
    assert [(h["statusAnterior"], h["statusNovo"], h["responsavel_id"]) for h in hist_pag] == [(None, "REEMBOLSADO", LUCAS)]

    # UC12 passo 5: o anfitrião (outra parte) é notificado; o hóspede recebe o comprovante (RF-28)
    emails = EmailService.get_sent_emails()
    assert {(e["destinatario"], e["tipo"]) for e in emails} == {
        ("carlos_anfitriao@exemplo.com", "CANCELAMENTO_RESERVA_ANFITRIAO"),
        ("hospede_teste@exemplo.com", "COMPROVANTE_REEMBOLSO_HOSPEDE"),
    }
    comprovante = next(e for e in emails if e["tipo"] == "COMPROVANTE_REEMBOLSO_HOSPEDE")
    assert "R$ 1026.00" in comprovante["corpo"] and reembolso["txid"] in comprovante["corpo"]


def test_uc12_hospede_cancela_em_cima_da_hora_recebe_50_por_cento_das_diarias():
    rid, _ = _reserva_paga(inicio=100, noites=3)
    agora = _instante_checkin(rid) - timedelta(hours=47)
    resultado = cancelamento.cancelar_reserva(rid, LUCAS, agora=agora)
    assert resultado["reembolso"]["regra"] == "HOSPEDE_PARCIAL"
    assert resultado["reembolso"]["valor_reembolso"] == 450.00
    assert _pagamentos(rid)[-1]["valor"] == 450.00


def test_uc12_2a_anfitriao_cancela_e_hospede_recebe_tudo_e_e_notificado():
    rid, res = _reserva_paga(acomodacao_id=ACOM_SUPERHOST, inicio=100, noites=2)   # 800 + 100,80
    agora = _instante_checkin(rid) - timedelta(hours=2)
    resultado = cancelamento.cancelar_reserva(rid, MARIANA, agora=agora)
    assert resultado["cancelado_por"] == "ANFITRIAO"
    assert resultado["reembolso"]["valor_reembolso"] == res["valor_total"] == 900.80
    assert _historico_reserva(rid)[-1]["responsavel_id"] == MARIANA
    emails = EmailService.get_sent_emails()
    assert [(e["destinatario"], e["tipo"]) for e in emails] == [
        ("hospede_teste@exemplo.com", "CANCELAMENTO_RESERVA_HOSPEDE")]
    assert "R$ 900.80" in emails[0]["corpo"]


def test_cancelar_pendente_nao_chama_o_gateway_e_nao_gera_reembolso(monkeypatch):
    def gateway_nao_deveria_ser_chamado(*args, **kwargs):
        raise AssertionError("process_refund chamado para reserva sem pagamento")
    monkeypatch.setattr(PaymentGateway, "process_refund", gateway_nao_deveria_ser_chamado)

    res = models.criar_reserva(LUCAS, ACOM_COMUM, _dia(130), _dia(132), 2)
    resultado = cancelamento.cancelar_reserva(res["reserva_id"], LUCAS)
    assert resultado["pagamento_reembolso"] is None
    assert resultado["reembolso"]["regra"] == "SEM_PAGAMENTO"
    assert _status(res["reserva_id"]) == "CANCELADA"
    assert _pagamentos(res["reserva_id"]) == []
    assert [e["tipo"] for e in EmailService.get_sent_emails()] == ["CANCELAMENTO_RESERVA_ANFITRIAO"]


def test_cancelamento_libera_as_datas_e_esconde_o_endereco():
    rid, _ = _reserva_paga(inicio=100, noites=3)
    assert models.obter_reserva_completa(rid)["acomodacao_rua"] is not None
    ok, _, _ = models.validar_disponibilidade_e_regras(ACOM_COMUM, _dia(100), _dia(103), 2)
    assert not ok                                              # RF-19: datas ocupadas
    cancelamento.cancelar_reserva(rid, LUCAS)
    ok, _, _ = models.validar_disponibilidade_e_regras(ACOM_COMUM, _dia(100), _dia(103), 2)
    assert ok                                                  # datas livres de novo
    assert models.obter_reserva_completa(rid)["acomodacao_rua"] is None   # RNF-05*


# ===========================================================================
# 4. Cenários de erro: gateway, cancelamento duplo, valor alterado
# ===========================================================================

def test_gateway_recusa_estorno_nada_e_alterado():
    rid, _ = _reserva_paga(txid="TX-CC-FALHAESTORNO-1")
    with pytest.raises(CancelamentoErro) as e:
        cancelamento.cancelar_reserva(rid, LUCAS)
    assert e.value.http_status == 502
    assert _status(rid) == "CONFIRMADA"
    assert [p["status"] for p in _pagamentos(rid)] == ["APROVADO"]
    assert _historico_reserva(rid)[-1]["statusNovo"] == "CONFIRMADA"
    assert EmailService.get_sent_emails() == []


def test_gateway_indisponivel_nada_e_alterado_e_depois_funciona():
    rid, _ = _reserva_paga()
    PaymentGateway.definir_modo_reembolso("INDISPONIVEL")
    with pytest.raises(CancelamentoErro) as e:
        cancelamento.cancelar_reserva(rid, LUCAS)
    assert e.value.http_status == 503
    assert _status(rid) == "CONFIRMADA"
    assert len(_pagamentos(rid)) == 1

    PaymentGateway.definir_modo_reembolso("NORMAL")
    cancelamento.cancelar_reserva(rid, LUCAS)
    assert _status(rid) == "CANCELADA"


def test_nao_cancela_duas_vezes_nem_reembolsa_duas_vezes():
    rid, _ = _reserva_paga()
    cancelamento.cancelar_reserva(rid, LUCAS)
    with pytest.raises(CancelamentoErro) as e:
        cancelamento.cancelar_reserva(rid, CARLOS)
    assert e.value.codigo == "STATUS_NAO_CANCELAVEL"
    assert [p["status"] for p in _pagamentos(rid)].count("REEMBOLSADO") == 1


def test_valor_exibido_diferente_interrompe_sem_alterar_nada():
    """AMB-12: a tela mostrou o reembolso integral, mas o prazo de 48 h venceu antes da confirmação."""
    rid, res = _reserva_paga(inicio=100, noites=3)
    agora = _instante_checkin(rid) - timedelta(hours=47)
    with pytest.raises(CancelamentoErro) as e:
        cancelamento.cancelar_reserva(rid, LUCAS, valor_exibido=res["valor_total"], agora=agora)
    assert e.value.codigo == "VALOR_ALTERADO"
    assert e.value.dados["reembolso"]["valor_reembolso"] == 450.00
    assert _status(rid) == "CONFIRMADA"
    # Com o valor certo, segue normalmente
    cancelamento.cancelar_reserva(rid, LUCAS, valor_exibido=450.00, agora=agora)
    assert _status(rid) == "CANCELADA"


def test_gateway_simulado_idempotente_e_valida_valor():
    a = PaymentGateway.process_refund("TX-1", 100.0, reservation_id=1, idempotency_key="k1")
    b = PaymentGateway.process_refund("TX-1", 100.0, reservation_id=1, idempotency_key="k1")
    assert a["sucesso"] and a["refund_id"] == b["refund_id"]
    assert not PaymentGateway.process_refund("TX-2", 0)["sucesso"]
    with pytest.raises(ValueError):
        PaymentGateway.definir_modo_reembolso("QUALQUER")


# ===========================================================================
# 5. Dados de exemplo: cada cenário do README se comporta como descrito
# ===========================================================================

def test_dados_de_exemplo_cobrem_os_cenarios():
    esperado = [
        (C1_INTEGRAL, LUCAS, "HOSPEDE_INTEGRAL", 1026.00),
        (C2_TARDIA_PIX, LUCAS, "HOSPEDE_PARCIAL", 300.00),
        (C2_TARDIA_PIX, CARLOS, "ANFITRIAO_INTEGRAL", 684.00),
        (C3_SUPERHOST, MARIANA, "ANFITRIAO_INTEGRAL", 900.80),
        (C3_SUPERHOST, LUCAS, "HOSPEDE_PARCIAL", 400.00),
        (C5_PENDENTE, LUCAS, "SEM_PAGAMENTO", 0.00),
        (C9_EM_ANDAMENTO, LUCAS, "HOSPEDE_PARCIAL", 450.00),
    ]
    for rid, usuario, regra, valor in esperado:
        r = cancelamento.obter_previa_cancelamento(rid, usuario)["reembolso"]
        assert (rid, r["regra"], r["valor_reembolso"]) == (rid, regra, valor)
    with pytest.raises(CancelamentoErro) as e:
        cancelamento.cancelar_reserva(C4_FALHA_GATEWAY, LUCAS)
    assert e.value.codigo == "REEMBOLSO_RECUSADO"


# ===========================================================================
# 6. Camada HTTP: telas, API REST, login e CSRF
# ===========================================================================

def test_tela_fluxo_completo_do_uc12(lucas):
    lista = lucas.get("/reservas").data.decode()
    assert f"/reservas/{C1_INTEGRAL}/cancelar" in lista
    assert f"/reservas/{C6_CANCELADA}/cancelar" not in lista              # já cancelada: sem botão

    detalhe = lucas.get(f"/reservas/{C1_INTEGRAL}").data.decode()
    assert "Cancelar reserva" in detalhe                                  # passo 1

    tela = lucas.get(f"/reservas/{C1_INTEGRAL}/cancelar").data.decode()
    assert "R$ 1026.00" in tela and "Aplicada" in tela                    # passo 2
    token = re.search(r'name="csrf_token" value="([^"]+)"', tela).group(1)
    valor = re.search(r'name="valor_exibido" value="([^"]+)"', tela).group(1)

    resp = lucas.post(f"/reservas/{C1_INTEGRAL}/cancelar",                # passo 3
                      data={"csrf_token": token, "valor_exibido": valor}, follow_redirects=True)
    pagina = resp.data.decode()
    assert f"Reserva #{C1_INTEGRAL} cancelada" in pagina
    assert "REEMBOLSADO" in pagina
    assert _status(C1_INTEGRAL) == "CANCELADA"


def test_tela_post_sem_token_csrf_nao_cancela(lucas):
    resp = lucas.post(f"/reservas/{C1_INTEGRAL}/cancelar", data={"valor_exibido": "1026.00"}, follow_redirects=True)
    assert "A confirmação expirou" in resp.data.decode()
    assert _status(C1_INTEGRAL) == "CONFIRMADA"


def test_tela_erro_do_gateway_aparece_em_linguagem_simples(lucas):
    tela = lucas.get(f"/reservas/{C4_FALHA_GATEWAY}/cancelar").data.decode()
    token = re.search(r'name="csrf_token" value="([^"]+)"', tela).group(1)
    resp = lucas.post(f"/reservas/{C4_FALHA_GATEWAY}/cancelar",
                      data={"csrf_token": token, "valor_exibido": "684.00"}, follow_redirects=True)
    assert "recusou o reembolso" in resp.data.decode()
    assert _status(C4_FALHA_GATEWAY) == "CONFIRMADA"


def test_tela_terceiro_nao_ve_nem_cancela():
    ana = _cliente(ANA)
    assert ana.get(f"/reservas/{C1_INTEGRAL}").status_code == 302
    resp = ana.get(f"/reservas/{C1_INTEGRAL}/cancelar", follow_redirects=True)
    assert "não tem permissão" in resp.data.decode()


def test_tela_anfitriao_ve_reservas_recebidas_e_cancela():
    carlos = _cliente(CARLOS)
    lista = carlos.get("/reservas").data.decode()
    assert "Reservas recebidas" in lista and f"/reservas/{C2_TARDIA_PIX}/cancelar" in lista
    tela = carlos.get(f"/reservas/{C2_TARDIA_PIX}/cancelar").data.decode()
    assert "UC12, fluxo 2a" in tela and "R$ 684.00" in tela
    # Mariana é anfitriã, mas não desta acomodação (RNF-11)
    assert _cliente(MARIANA).get(f"/reservas/{C2_TARDIA_PIX}/cancelar").status_code == 302


def test_login_obrigatorio():
    anonimo = _cliente(None)
    assert anonimo.get("/reservas").status_code == 302
    assert anonimo.get(f"/api/reservas/{C1_INTEGRAL}/cancelamento").status_code == 401
    assert anonimo.post(f"/api/reservas/{C1_INTEGRAL}/cancelamento", json={}).status_code == 401


def test_api_rest_previa_e_cancelamento(lucas):
    previa = lucas.get(f"/api/reservas/{C2_TARDIA_PIX}/cancelamento").get_json()
    assert previa["sucesso"] and previa["reembolso"]["valor_reembolso"] == 300.00

    # Sem JSON (ex.: formulário de outro site) é recusado
    assert lucas.post(f"/api/reservas/{C2_TARDIA_PIX}/cancelamento", data="x",
                      content_type="text/plain").status_code == 415

    resp = lucas.post(f"/api/reservas/{C2_TARDIA_PIX}/cancelamento", json={"valor_exibido": 300.00})
    dados = resp.get_json()
    assert resp.status_code == 200 and dados["status"] == "CANCELADA"
    assert dados["pagamento_reembolso"]["metodo"] == "PIX"
    assert dados["pagamento_reembolso"]["valor"] == 300.00

    erro = lucas.post(f"/api/reservas/{C2_TARDIA_PIX}/cancelamento", json={})
    assert erro.status_code == 409 and erro.get_json()["codigo"] == "STATUS_NAO_CANCELAVEL"
    assert _cliente(ANA).get(f"/api/reservas/{C1_INTEGRAL}/cancelamento").status_code == 403


def test_rota_de_simulacao_do_gateway():
    c = _cliente(LUCAS)
    assert c.post("/api/dev/gateway-reembolso", json={"modo": "INDISPONIVEL"}).get_json()["modo"] == "INDISPONIVEL"
    resp = c.post(f"/api/reservas/{C1_INTEGRAL}/cancelamento", json={})
    assert resp.status_code == 503
    assert c.post("/api/dev/gateway-reembolso", json={"modo": "NORMAL"}).get_json()["modo"] == "NORMAL"
    assert c.post("/api/dev/gateway-reembolso", json={"modo": "X"}).status_code == 400


def test_fluxo_de_reserva_continua_igual(lucas):
    """As telas do fluxo de reserva continuam com a barra de 3 passos; os dados novos não ocupam as acomodações 1 a 4."""
    assert "flow-progress" in lucas.get("/resumo").data.decode()
    assert "flow-progress" not in lucas.get("/reservas").data.decode()
    ok, _, _ = models.validar_disponibilidade_e_regras(1, _dia(1), _dia(4), 2)   # datas padrão da Tela 1
    assert ok


# ===========================================================================
# 7. Lacuna conhecida (AMB-06): fica visível como xfail, sem mudar o fluxo de reserva
# ===========================================================================

@pytest.mark.xfail(strict=True, reason=(
    "AMB-06: um aviso de PIX que chega depois do cancelamento reconfirma a reserva. "
    "Corrigir exige mudar o webhook do fluxo de reserva, o que a tarefa proíbe; a ERS não "
    "diz o que fazer com pagamento recebido para reserva cancelada."))
def test_lacuna_pix_pago_depois_do_cancelamento_nao_deveria_reconfirmar(lucas):
    res = models.criar_reserva(LUCAS, ACOM_COMUM, _dia(140), _dia(142), 2)
    rid = res["reserva_id"]
    cobranca = lucas.post("/api/pagamento/pix/gerar", json={"reserva_id": rid}).get_json()["cobranca"]
    cancelamento.cancelar_reserva(rid, LUCAS)
    lucas.post("/api/webhook/pix", json={"txid": cobranca["txid"], "valor": cobranca["valor"]})
    assert _status(rid) == "CANCELADA"
