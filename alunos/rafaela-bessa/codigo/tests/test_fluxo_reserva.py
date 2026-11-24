"""
tests/test_fluxo_reserva.py - Testes Automatizados (pytest)
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
Cobertura exaustiva das regras do fluxo de reserva, pagamento e confirmação (ERS v1.2)
"""

import os
import pytest
from datetime import date, timedelta, datetime

import database
import models
from services.payment_gateway import PaymentGateway
from services.email_service import EmailService
from app import app


@pytest.fixture(autouse=True)
def setup_fresh_db():
    """Garante um banco SQLite limpo e populado antes de cada bateria de testes."""
    database.init_db(force_recreate=True)
    EmailService.clear()
    yield


@pytest.fixture
def client():
    """Cliente de teste Flask configurado."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        with client.session_transaction() as sess:
            # Hóspede logado por padrão (Lucas Hóspede - ID 1)
            sess["session_initialized"] = True
            sess["usuario_id"] = 1
            sess["usuario_nome"] = "Lucas Hóspede"
            sess["usuario_email"] = "hospede_teste@exemplo.com"
        yield client


# ===========================================================================
# 1. Testes de Regras de Negócio de Cálculo e Validação
# ===========================================================================

def test_rn01_checkout_posterior_checkin_minimo_uma_noite():
    """RN-01: O check-out deve ser posterior ao check-in, com estadia mínima de 1 noite."""
    # Cenário de erro: check-out igual ao check-in (0 noites)
    with pytest.raises(ValueError, match="estadia mínima de 1 noite"):
        models.calcular_valores_estadia(
            preco_noite=250.0,
            check_in_str="2026-12-01",
            check_out_str="2026-12-01",
            eh_superhost=False
        )

    # Cenário de erro: check-out anterior ao check-in (-1 noite)
    with pytest.raises(ValueError, match="estadia mínima de 1 noite"):
        models.calcular_valores_estadia(
            preco_noite=250.0,
            check_in_str="2026-12-05",
            check_out_str="2026-12-04",
            eh_superhost=False
        )

    # Cenário válido: 1 noite
    calc = models.calcular_valores_estadia(
        preco_noite=250.0,
        check_in_str="2026-12-01",
        check_out_str="2026-12-02",
        eh_superhost=False
    )
    assert calc["num_noites"] == 1


def test_rn02_capacidade_maxima():
    """RN-02: O número de hóspedes de uma reserva não pode ultrapassar a capacidadeMaxima."""
    # Acomodação 2 tem capacidade máxima de 2 hóspedes
    valido, msg, _ = models.validar_disponibilidade_e_regras(
        acomodacao_id=2,
        check_in_str="2026-12-10",
        check_out_str="2026-12-13",
        num_hospedes=3  # Ultrapassa 2
    )
    assert not valido
    assert "ultrapassa a capacidade máxima" in msg

    # Cenário inválido: menos de 1 hóspede
    valido_zero, msg_zero, _ = models.validar_disponibilidade_e_regras(
        acomodacao_id=2,
        check_in_str="2026-12-10",
        check_out_str="2026-12-13",
        num_hospedes=0
    )
    assert not valido_zero
    assert "pelo menos 1" in msg_zero

    # Cenário válido: 2 hóspedes em capacidade 2
    valido_ok, _, _ = models.validar_disponibilidade_e_regras(
        acomodacao_id=2,
        check_in_str="2026-12-10",
        check_out_str="2026-12-13",
        num_hospedes=2
    )
    assert valido_ok


def test_rn03_rn07_rf18_calculo_taxa_servico_e_superhost():
    """
    RN-03: Taxa de serviço de 14% sobre as diárias.
    RN-07 e RF-18: Desconto de 10% sobre o valor da taxa de serviço para acomodações de Superhost (taxa efetiva 12,6%).
    """
    # 1. Anfitrião Padrão (Sem Superhost)
    # 3 noites a R$ 250,00 = R$ 750,00 de diárias
    # Taxa 14%: 750 * 0.14 = R$ 105,00
    # Total: R$ 855,00
    calc_comum = models.calcular_valores_estadia(
        preco_noite=250.0,
        check_in_str="2026-12-01",
        check_out_str="2026-12-04",
        eh_superhost=False
    )
    assert calc_comum["num_noites"] == 3
    assert calc_comum["subtotal_diarias"] == 750.00
    assert calc_comum["taxa_servico_base"] == 105.00
    assert calc_comum["desconto_superhost"] == 0.00
    assert calc_comum["taxa_servico_final"] == 105.00
    assert calc_comum["valor_total"] == 855.00

    # 2. Anfitrião Superhost
    # 2 noites a R$ 400,00 = R$ 800,00 de diárias
    # Taxa de 14%: 800 * 0.14 = R$ 112,00
    # Desconto Superhost (10% de R$ 112,00) = R$ 11,20
    # Taxa final (12,6%): 112,00 - 11,20 = R$ 100,80
    # Total: 800 + 100,80 = R$ 900,80
    calc_super = models.calcular_valores_estadia(
        preco_noite=400.0,
        check_in_str="2026-12-01",
        check_out_str="2026-12-03",
        eh_superhost=True
    )
    assert calc_super["num_noites"] == 2
    assert calc_super["subtotal_diarias"] == 800.00
    assert calc_super["taxa_servico_base"] == 112.00
    assert calc_super["desconto_superhost"] == 11.20
    assert calc_super["taxa_servico_final"] == 100.80
    assert calc_super["valor_total"] == 900.80


def test_rf19_impedir_reservas_sobrepostas():
    """RF-19: O sistema deve impedir reservas sobrepostas para a mesma acomodação."""
    # No seed_data, a Acomodação 3 possui uma reserva CONFIRMADA de (hoje + 20 dias) a (hoje + 25 dias)
    hoje = date.today()
    checkin_ocupado = (hoje + timedelta(days=20)).strftime("%Y-%m-%d")
    checkout_ocupado = (hoje + timedelta(days=25)).strftime("%Y-%m-%d")

    # Tentativa com período exatamente sobreposto
    valido, msg, _ = models.validar_disponibilidade_e_regras(
        acomodacao_id=3,
        check_in_str=checkin_ocupado,
        check_out_str=checkout_ocupado,
        num_hospedes=2
    )
    assert not valido
    assert "já está reservada ou possui solicitação em andamento" in msg

    # Tentativa com sobreposição parcial (começa dentro do período)
    checkin_parcial = (hoje + timedelta(days=22)).strftime("%Y-%m-%d")
    checkout_parcial = (hoje + timedelta(days=27)).strftime("%Y-%m-%d")
    valido_parcial, _, _ = models.validar_disponibilidade_e_regras(
        acomodacao_id=3,
        check_in_str=checkin_parcial,
        check_out_str=checkout_parcial,
        num_hospedes=2
    )
    assert not valido_parcial

    # Tentativa em período livre (após o checkout)
    checkin_livre = (hoje + timedelta(days=26)).strftime("%Y-%m-%d")
    checkout_livre = (hoje + timedelta(days=30)).strftime("%Y-%m-%d")
    valido_livre, _, _ = models.validar_disponibilidade_e_regras(
        acomodacao_id=3,
        check_in_str=checkin_livre,
        check_out_str=checkout_livre,
        num_hospedes=2
    )
    assert valido_livre


def test_validar_acomodacao_inativa():
    """Valida rejeição de reserva para acomodação com ativo = 0."""
    valido, msg, _ = models.validar_disponibilidade_e_regras(
        acomodacao_id=4,  # Acomodação 4 está inativa no seed_data
        check_in_str="2026-12-01",
        check_out_str="2026-12-03",
        num_hospedes=1
    )
    assert not valido
    assert "temporariamente inativa" in msg


def test_rn04_expiracao_30_minutos_reserva_pendente():
    """RN-04: Uma reserva PENDENTE é cancelada automaticamente se o pagamento não for aprovado em 30 minutos."""
    # Criar uma reserva PENDENTE simulando ter sido criada há 35 minutos
    conn = database.get_db_connection()
    cursor = conn.cursor()
    passado_35min = (datetime.now() - timedelta(minutes=35)).isoformat()

    cursor.execute("""
        INSERT INTO reserva (hospede_id, acomodacao_id, checkIn, checkOut, numHospedes, valorTotal, status, dataCriacao)
        VALUES (1, 1, '2026-11-20', '2026-11-23', 2, 855.00, 'PENDENTE', ?);
    """, (passado_35min,))
    reserva_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Executar a verificação de expiração
    expiradas = models.expirar_reservas_pendentes()
    assert expiradas >= 1

    # Verificar que o status mudou para CANCELADA no banco
    reserva = models.obter_reserva_completa(reserva_id)
    assert reserva["status"] == "CANCELADA"

    # Verificar que a trilha de auditoria registrou a mudança (RNF-22)
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM historico_status_reserva WHERE reserva_id = ? AND statusNovo = 'CANCELADA';", (reserva_id,))
    historico = cursor.fetchone()
    conn.close()
    assert historico is not None
    assert historico["statusAnterior"] == "PENDENTE"
    assert historico["statusNovo"] == "CANCELADA"


# ===========================================================================
# 2. Testes de Pagamento (Cartão de Crédito e PIX)
# ===========================================================================

def test_rf20_rf23_rf24_rf25_pagamento_cartao_aprovado(client):
    """
    Testa fluxo completo de pagamento síncrono por cartão:
    Reserva PENDENTE -> Pagamento APROVADO -> Reserva CONFIRMADA automaticamente (RF-20, TBD-03).
    """
    # 1. Cria a reserva no banco
    hoje = date.today()
    c_in = (hoje + timedelta(days=2)).strftime("%Y-%m-%d")
    c_out = (hoje + timedelta(days=5)).strftime("%Y-%m-%d")

    res = models.criar_reserva(
        hospede_id=1,
        acomodacao_id=1,
        check_in=c_in,
        check_out=c_out,
        num_hospedes=2
    )
    reserva_id = res["reserva_id"]
    assert res["status"] == "PENDENTE"

    # 2. Submete pagamento via API com cartão de teste aprovado (final 4000)
    response = client.post("/api/pagamento/cartao", json={
        "reserva_id": reserva_id,
        "titular": "LUCAS HOSPEDE",
        "numero_cartao": "5555 4444 3333 4000",
        "validade": "12/28",
        "cvv": "123"
    })

    assert response.status_code == 200
    dados = response.get_json()
    assert dados["sucesso"] is True
    assert dados["status"] == "APROVADO"
    assert "AUTH-" in dados["codigoAutorizacao"]

    # 3. Verifica se a reserva passou para CONFIRMADA no banco (RF-20)
    reserva_atualizada = models.obter_reserva_completa(reserva_id)
    assert reserva_atualizada["status"] == "CONFIRMADA"

    # 4. Verifica RF-28: Comprovante por e-mail disparado
    emails = EmailService.get_sent_emails()
    assert len(emails) >= 1
    email_hospede = next(e for e in emails if e["destinatario"] == "hospede_teste@exemplo.com")
    assert "CONFIRMADA" in email_hospede["assunto"]
    assert f"#{reserva_id}" in email_hospede["assunto"]


def test_rf26_pagamento_cartao_recusado_permite_nova_tentativa(client):
    """
    RF-26: O sistema deve permitir nova tentativa de pagamento quando o anterior for recusado.
    Garante que a reserva continue PENDENTE e registre a tentativa RECUSADA.
    """
    hoje = date.today()
    c_in = (hoje + timedelta(days=6)).strftime("%Y-%m-%d")
    c_out = (hoje + timedelta(days=8)).strftime("%Y-%m-%d")

    res = models.criar_reserva(hospede_id=1, acomodacao_id=1, check_in=c_in, check_out=c_out, num_hospedes=2)
    reserva_id = res["reserva_id"]

    # 1. Primeira tentativa com cartão terminado em 0002 (simula recusa de saldo)
    resp_recusa = client.post("/api/pagamento/cartao", json={
        "reserva_id": reserva_id,
        "titular": "LUCAS HOSPEDE",
        "numero_cartao": "4000 0000 0000 0002",
        "validade": "12/28",
        "cvv": "999"
    })

    assert resp_recusa.status_code == 400
    dados_recusa = resp_recusa.get_json()
    assert dados_recusa["sucesso"] is False
    assert dados_recusa["status"] == "RECUSADO"

    # Verifica que a reserva permaneceu PENDENTE
    reserva = models.obter_reserva_completa(reserva_id)
    assert reserva["status"] == "PENDENTE"
    assert len(reserva["pagamentos"]) == 1
    assert reserva["pagamentos"][0]["status"] == "RECUSADO"

    # 2. Nova tentativa com cartão válido (RF-26)
    resp_sucesso = client.post("/api/pagamento/cartao", json={
        "reserva_id": reserva_id,
        "titular": "LUCAS HOSPEDE",
        "numero_cartao": "5555 4444 3333 4000",
        "validade": "12/28",
        "cvv": "123"
    })
    assert resp_sucesso.status_code == 200
    assert resp_sucesso.get_json()["sucesso"] is True

    # Verifica que agora a reserva está CONFIRMADA e possui 2 pagamentos registrados
    reserva_confirmada = models.obter_reserva_completa(reserva_id)
    assert reserva_confirmada["status"] == "CONFIRMADA"
    assert len(reserva_confirmada["pagamentos"]) == 2
    assert reserva_confirmada["pagamentos"][0]["status"] == "RECUSADO"
    assert reserva_confirmada["pagamentos"][1]["status"] == "APROVADO"


def test_pagamento_cartao_erros_validacao_gateway():
    """Valida erros de validação no gateway simulado (CVV inválido, cartão expirado)."""
    # 1. CVV com tamanho incorreto
    res_cvv = PaymentGateway.authorize_credit_card(
        card_holder="TESTE", card_number="5555444433334000", expiration="12/28", cvv="1",
        amount=100.0, reservation_id=1
    )
    assert not res_cvv["sucesso"]
    assert "CVV" in res_cvv["motivo"]

    # 2. Cartão vencido
    res_exp = PaymentGateway.authorize_credit_card(
        card_holder="TESTE", card_number="5555444433334000", expiration="01/20", cvv="123",
        amount=100.0, reservation_id=1
    )
    assert not res_exp["sucesso"]
    assert "vencido" in res_exp["motivo"]


def test_rf23_rf24_pix_geracao_e_webhook_confirmacao(client):
    """
    Testa o fluxo assíncrono do PIX:
    1. Geração de cobrança com txid único vinculado à reserva (RF-23).
    2. Recebimento de webhook do banco confirmando o PIX (Seção 3.4).
    3. Confirmação automática da reserva e disparo de e-mails (RF-20, RF-28).
    """
    hoje = date.today()
    c_in = (hoje + timedelta(days=10)).strftime("%Y-%m-%d")
    c_out = (hoje + timedelta(days=13)).strftime("%Y-%m-%d")

    res = models.criar_reserva(hospede_id=1, acomodacao_id=2, check_in=c_in, check_out=c_out, num_hospedes=2)
    reserva_id = res["reserva_id"]
    valor_esperado = res["valor_total"]

    # 1. Gerar cobrança PIX
    resp_pix = client.post("/api/pagamento/pix/gerar", json={"reserva_id": reserva_id})
    assert resp_pix.status_code == 200
    dados_pix = resp_pix.get_json()
    assert dados_pix["sucesso"] is True
    txid = dados_pix["cobranca"]["txid"]
    assert f"PIX-{reserva_id}-" in txid

    # 2. Simular o Webhook enviado pelo Banco / Gateway (Seção 3.4)
    resp_webhook = client.post("/api/webhook/pix", json={
        "txid": txid,
        "valor": valor_esperado,
        "status": "APROVADO"
    })
    assert resp_webhook.status_code == 200
    assert resp_webhook.get_json()["sucesso"] is True

    # 3. Conferir se a reserva foi ativada para CONFIRMADA
    reserva = models.obter_reserva_completa(reserva_id)
    assert reserva["status"] == "CONFIRMADA"
    assert reserva["pagamento_aprovado"]["status"] == "APROVADO"
    assert reserva["pagamento_aprovado"]["txid"] == txid


def test_webhook_pix_cenarios_de_erro(client):
    """Testa rejeição do webhook de PIX em caso de txid inexistente ou valor divergente."""
    # 1. txid desconhecido
    resp_desconhecido = client.post("/api/webhook/pix", json={
        "txid": "TX-INEXISTENTE-1234",
        "valor": 100.0,
        "status": "APROVADO"
    })
    assert resp_desconhecido.status_code == 404

    # 2. txid válido mas valor divergente
    res = models.criar_reserva(hospede_id=1, acomodacao_id=1, check_in="2026-12-10", check_out="2026-12-12", num_hospedes=2)
    resp_pix = client.post("/api/pagamento/pix/gerar", json={"reserva_id": res["reserva_id"]})
    txid = resp_pix.get_json()["cobranca"]["txid"]

    resp_valor_errado = client.post("/api/webhook/pix", json={
        "txid": txid,
        "valor": 10.00,  # Valor bem menor que o real da reserva
        "status": "APROVADO"
    })
    assert resp_valor_errado.status_code == 400
    assert "divergente" in resp_valor_errado.get_json()["mensagem"]


# ===========================================================================
# 3. Testes de Segurança Física e da Informação (RNF-05*, RNF-08, RNF-11)
# ===========================================================================

def test_rnf05_seguranca_fisica_endereco_apenas_apos_confirmacao(client):
    """
    RNF-05*: O endereço exato da acomodação só deve ser exibido ao hóspede
    após a reserva ser CONFIRMADA; antes disso, mostra-se apenas o bairro.
    """
    # 1. Consulta inicial na Tela 1 ou Acomodação
    acomodacao = models.obter_acomodacao_detalhe(1)
    assert "bairro" in acomodacao and acomodacao["bairro"] == "Copacabana"
    # Campos de endereço exato não existem ou não são entregues
    assert "rua" not in acomodacao or acomodacao["rua"] is None
    assert "numero" not in acomodacao or acomodacao["numero"] is None
    assert "cep" not in acomodacao or acomodacao["cep"] is None

    # 2. Cria reserva PENDENTE
    res = models.criar_reserva(hospede_id=1, acomodacao_id=1, check_in="2026-12-15", check_out="2026-12-18", num_hospedes=2)
    reserva_pendente = models.obter_reserva_completa(res["reserva_id"])
    assert reserva_pendente["status"] == "PENDENTE"
    # Endereço exato ocultado (RNF-05*)
    assert reserva_pendente["acomodacao_rua"] is None
    assert reserva_pendente["acomodacao_numero"] is None
    assert reserva_pendente["acomodacao_cep"] is None
    assert reserva_pendente["acomodacao_bairro"] == "Copacabana"

    # 3. Aprova o pagamento -> Reserva CONFIRMADA
    models.confirmar_reserva_apos_pagamento(res["reserva_id"])
    reserva_confirmada = models.obter_reserva_completa(res["reserva_id"])
    assert reserva_confirmada["status"] == "CONFIRMADA"
    # Endereço completo agora revelado!
    assert reserva_confirmada["acomodacao_rua"] == "Avenida Atlântica"
    assert reserva_confirmada["acomodacao_numero"] == "1500, apto 402"
    assert reserva_confirmada["acomodacao_cep"] == "22021-001"


def test_rnf08_seguranca_informacao_nao_armazena_numero_completo_nem_cvv():
    """
    RNF-08: O sistema não deve armazenar número completo nem CVV de cartões;
    apenas o token devolvido pelo gateway.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()

    # Inspeciona as colunas da tabela pagamento no SQLite
    cursor.execute("PRAGMA table_info(pagamento);")
    colunas = [c["name"].lower() for c in cursor.fetchall()]

    # Garante que não existem colunas para número de cartão ou CVV
    assert "numerocartao" not in colunas
    assert "numero_cartao" not in colunas
    assert "cvv" not in colunas
    assert "codigoseguranca" not in colunas

    # Garante que possui coluna para token e txid
    assert "tokencartao" in colunas
    assert "txid" in colunas
    conn.close()


def test_rnf11_e_login_requerido(client):
    """
    Verifica regra 'o hóspede precisa estar logado' e RNF-11 (apenas dono da reserva acessa).
    """
    # 1. Teste de usuário deslogado tentando acessar API
    with client.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = None
        sess["usuario_nome"] = "Visitante"

    resp_nao_logado = client.post("/api/pagamento/cartao", json={"reserva_id": 1})
    assert resp_nao_logado.status_code == 401
    assert "precisa estar autenticado" in resp_nao_logado.get_json()["erro"]

    # 2. Teste de acesso cruzado (RNF-11)
    # Reserva pertence ao hóspede 1
    res = models.criar_reserva(hospede_id=1, acomodacao_id=1, check_in="2026-12-20", check_out="2026-12-22", num_hospedes=2)
    reserva_id = res["reserva_id"]

    # Logar como outro hóspede (ID 2)
    with client.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 2
        sess["usuario_nome"] = "Ana Outra Hóspede"

    # Tenta acessar a página de pagamento da reserva do hóspede 1
    resp_outro = client.get(f"/pagamento/{reserva_id}", follow_redirects=True)
    assert resp_outro.status_code == 200
    assert "Você não tem autorização para acessar esta reserva" in resp_outro.data.decode("utf-8")


def test_navegacao_telas_e_bloqueio_tela_confirmacao_reserva_pendente(client):
    """
    Garante que a Tela 3 (Confirmação) bloqueie acesso se a reserva ainda não for CONFIRMADA.
    """
    res = models.criar_reserva(hospede_id=1, acomodacao_id=1, check_in="2026-12-28", check_out="2026-12-30", num_hospedes=2)
    reserva_id = res["reserva_id"]

    # Tenta acessar /confirmacao com reserva PENDENTE -> Redireciona para /pagamento
    resp = client.get(f"/confirmacao/{reserva_id}", follow_redirects=False)
    assert resp.status_code == 302
    assert f"/pagamento/{reserva_id}" in resp.headers["Location"]
