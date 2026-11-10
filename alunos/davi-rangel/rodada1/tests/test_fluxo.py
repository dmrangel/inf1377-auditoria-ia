import pytest
from app import app
from database import init_db, get_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    init_db()
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['usuario_id'] = 1
            sess['usuario_nome'] = "Hóspede Teste"
            sess['usuario_email'] = "hospede@teste.com"
        yield client

def test_rn01_estadia_minima(client):
    """RN-01: Check-out deve ser posterior ao check-in (mínimo 1 noite)"""
    payload = {
        "acomodacao_id": 1,
        "checkin": "2026-11-20",
        "checkout": "2026-11-20",
        "num_hospedes": 1
    }
    res = client.post('/api/reservas', json=payload)
    assert res.status_code == 400
    assert "RN-01" in res.get_json()['erro']

def test_rn02_capacidade_maxima(client):
    """RN-02: Hóspedes não podem ultrapassar a capacidade da acomodação"""
    # Acomodação 2 possui capacidade máxima igual a 2
    payload = {
        "acomodacao_id": 2,
        "checkin": "2026-11-20",
        "checkout": "2026-11-23",
        "num_hospedes": 5
    }
    res = client.post('/api/reservas', json=payload)
    assert res.status_code == 400
    assert "RN-02" in res.get_json()['erro']

def test_rf18_rn07_desconto_superhost(client):
    """RF-18 / RN-07: Taxa de serviço de 14% com 10% de desconto para Superhost"""
    # Acomodação 2 é Superhost: diária 300 x 2 noites = 600 diárias
    # Taxa regular (14%): 84.00
    # Desconto Superhost (10% sobre 84.00): 8.40
    # Total esperado: 600 + 84 - 8.40 = 675.60
    payload = {
        "acomodacao_id": 2,
        "checkin": "2026-12-01",
        "checkout": "2026-12-03",
        "num_hospedes": 2
    }
    res = client.post('/api/reservas', json=payload)
    assert res.status_code == 200
    reserva_id = res.get_json()['reserva_id']

    conn = get_db()
    r = conn.execute("SELECT * FROM reserva WHERE id = ?", (reserva_id,)).fetchone()
    conn.close()
    assert r['subtotalDiarias'] == 600.0
    assert r['taxaServico'] == 84.0
    assert r['descontoSuperhost'] == 8.4
    assert r['valorTotal'] == 675.6

def test_rf19_impedir_sobreposicao(client):
    """RF-19: Bloquear reservas sobrepostas na mesma acomodação"""
    payload = {
        "acomodacao_id": 1,
        "checkin": "2026-12-10",
        "checkout": "2026-12-15",
        "num_hospedes": 2
    }
    res1 = client.post('/api/reservas', json=payload)
    assert res1.status_code == 200

    payload_conflito = {
        "acomodacao_id": 1,
        "checkin": "2026-12-12",
        "checkout": "2026-12-18",
        "num_hospedes": 2
    }
    res2 = client.post('/api/reservas', json=payload_conflito)
    assert res2.status_code == 409
    assert "RF-19" in res2.get_json()['erro']

def test_rn04_expiracao_reserva_timeout(client):
    """RN-04: Cancelamento automático após 30 min sem pagamento"""
    res = client.post('/api/reservas', json={
        "acomodacao_id": 1, "checkin": "2026-12-28", "checkout": "2026-12-30", "num_hospedes": 1
    })
    reserva_id = res.get_json()['reserva_id']

    # Simula passagem de 31 minutos no SQLite (tempo UTC)
    conn = get_db()
    conn.execute("UPDATE reserva SET criadoEm = datetime('now', '-31 minutes') WHERE id = ?", (reserva_id,))
    conn.commit()
    conn.close()

    # Tentativa de pagamento com cartão após expirar deve falhar
    res_pagar = client.post(f'/api/reservas/{reserva_id}/pagar-cartao', json={"numero_cartao": "4111111111111234"})
    assert res_pagar.status_code == 400
    assert "expirada" in res_pagar.get_json()['erro']

    # Status no banco deve estar CANCELADA
    conn = get_db()
    r = conn.execute("SELECT status FROM reserva WHERE id = ?", (reserva_id,)).fetchone()
    conn.close()
    assert r['status'] == 'CANCELADA'

def test_fluxo_cartao_recusa_e_aprovacao(client):
    """RF-25 / RF-26: Trata recusa e autoriza nova tentativa mantendo a reserva"""
    res = client.post('/api/reservas', json={
        "acomodacao_id": 1, "checkin": "2026-12-20", "checkout": "2026-12-22", "num_hospedes": 1
    })
    reserva_id = res.get_json()['reserva_id']

    # 1. Cartão com final 0000 -> Simula recusa
    res_recusa = client.post(f'/api/reservas/{reserva_id}/pagar-cartao', json={"numero_cartao": "4111111111110000"})
    assert res_recusa.status_code == 422
    assert res_recusa.get_json()['status'] == 'RECUSADO'

    # 2. Nova tentativa com cartão válido -> Aprovado
    res_aprov = client.post(f'/api/reservas/{reserva_id}/pagar-cartao', json={"numero_cartao": "4111111111111234"})
    assert res_aprov.status_code == 200
    assert res_aprov.get_json()['status'] == 'APROVADO'

def test_fluxo_pix_assincrono(client):
    """RF-23: Cobrança PIX com txid único e compensação via Webhook"""
    res = client.post('/api/reservas', json={
        "acomodacao_id": 1, "checkin": "2026-12-25", "checkout": "2026-12-28", "num_hospedes": 1
    })
    reserva_id = res.get_json()['reserva_id']

    res_pix = client.post(f'/api/reservas/{reserva_id}/gerar-pix')
    txid = res_pix.get_json()['txid']

    # Disparo assíncrono simulado
    res_webhook = client.post('/api/webhook/pix', json={"txid": txid, "valor": 684.0})
    assert res_webhook.status_code == 200

    conn = get_db()
    r = conn.execute("SELECT status FROM reserva WHERE id = ?", (reserva_id,)).fetchone()
    conn.close()
    assert r['status'] == 'CONFIRMADA'

def test_rnf05_ocultacao_endereco_antes_confirmacao(client):
    """RNF-05: Endereço físico exato só deve ser exposto após status CONFIRMADA"""
    # 1. Resumo (Tela 1) não deve expor rua nem CEP
    res_resumo = client.get('/reservas/resumo?acomodacao_id=1&checkin=2026-12-05&checkout=2026-12-07&hospedes=2')
    assert res_resumo.status_code == 200
    html_resumo = res_resumo.get_data(as_text=True)
    assert "Copacabana" in html_resumo
    assert "Av. Atlântica" not in html_resumo
    assert "22041-001" not in html_resumo

    # 2. Tela de Confirmação (Tela 3) antes de confirmar deve redirecionar
    res = client.post('/api/reservas', json={
        "acomodacao_id": 1, "checkin": "2026-12-05", "checkout": "2026-12-07", "num_hospedes": 2
    })
    reserva_id = res.get_json()['reserva_id']
    res_conf_pendente = client.get(f'/reservas/{reserva_id}/confirmacao')
    assert res_conf_pendente.status_code == 302  # Redireciona para pagamento

    # 3. Pagar e aprovar
    client.post(f'/api/reservas/{reserva_id}/pagar-cartao', json={"numero_cartao": "4111111111111111"})

    # 4. Tela de Confirmação agora expõe rua e CEP
    res_conf_aprovada = client.get(f'/reservas/{reserva_id}/confirmacao')
    assert res_conf_aprovada.status_code == 200
    html_conf = res_conf_aprovada.get_data(as_text=True)
    assert "Av. Atlântica" in html_conf
    assert "22041-001" in html_conf

def test_rnf08_nao_armazenar_cartao_sensivel(client):
    """RNF-08: Número de cartão e CVV não devem ser persistidos no banco de dados"""
    numero_cartao_teste = "4111999988887777"
    res = client.post('/api/reservas', json={
        "acomodacao_id": 1, "checkin": "2026-12-08", "checkout": "2026-12-09", "num_hospedes": 1
    })
    reserva_id = res.get_json()['reserva_id']
    client.post(f'/api/reservas/{reserva_id}/pagar-cartao', json={"numero_cartao": numero_cartao_teste})

    conn = get_db()
    pag = conn.execute("SELECT * FROM pagamento WHERE reserva_id = ?", (reserva_id,)).fetchone()
    # Verifica que as colunas existentes não guardam o cartão completo
    cols = pag.keys()
    assert 'numero_cartao' not in cols
    assert 'cvv' not in cols
    for k in cols:
        assert str(pag[k]) != numero_cartao_teste
    conn.close()

def test_rnf22_auditoria_mudanca_status(client):
    """RNF-22: Auditoria de transições de status da reserva"""
    res = client.post('/api/reservas', json={
        "acomodacao_id": 1, "checkin": "2026-12-16", "checkout": "2026-12-17", "num_hospedes": 1
    })
    reserva_id = res.get_json()['reserva_id']

    client.post(f'/api/reservas/{reserva_id}/pagar-cartao', json={"numero_cartao": "4111111111111111"})

    conn = get_db()
    logs = conn.execute("SELECT * FROM auditoria WHERE entidade = 'reserva' AND entidade_id = ? ORDER BY id ASC", (reserva_id,)).fetchall()
    conn.close()

    assert len(logs) >= 2
    assert logs[0]['status_novo'] == 'PENDENTE'
    assert logs[1]['status_anterior'] == 'PENDENTE'
    assert logs[1]['status_novo'] == 'CONFIRMADA'
