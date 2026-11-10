from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime
from database import init_db, get_db
from models import (
    calcular_valores, validar_disponibilidade, 
    verificar_expiracao_reserva, registrar_auditoria
)
from services.payment_gateway import PaymentGatewaySimulado
from services.email_service import EmailServiceSimulado

app = Flask(__name__)
app.secret_key = "segredo_plataforma_ers_airbnb"

@app.before_request
def simular_autenticacao():
    # Garante hóspede de teste logado em conformidade com o escopo
    if 'usuario_id' not in session:
        session['usuario_id'] = 1
        session['usuario_nome'] = "Hóspede Teste"
        session['usuario_email'] = "hospede@teste.com"

@app.route('/')
def index():
    """Catálogo inicial simples para disparar a escolha de estadia"""
    conn = get_db()
    acomodacoes = conn.execute("SELECT * FROM acomodacao WHERE ativo = 1").fetchall()
    conn.close()
    return render_template("index.html", acomodacoes=acomodacoes)

# TELA 1: Resumo da Estadia (Seção 3.1)
@app.route('/reservas/resumo')
def tela_resumo():
    if not session.get('usuario_id'):
        return "Usuário não autenticado", 401
    
    acomodacao_id = request.args.get('acomodacao_id', type=int)
    checkin = request.args.get('checkin')
    checkout = request.args.get('checkout')
    hospedes = request.args.get('hospedes', default=1, type=int)

    conn = get_db()
    # RNF-05: Seleciona apenas bairro/cidade; rua e CEP não são enviados nesta rota
    acomodacao = conn.execute("""
        SELECT id, anfitriao_id, titulo, descricao, precoNoite, capacidadeMaxima, 
               bairro, cidade, estado, ehSuperhost 
        FROM acomodacao WHERE id = ?
    """, (acomodacao_id,)).fetchone()
    
    if not acomodacao:
        conn.close()
        return "Acomodação não encontrada", 404

    # RN-01: Check-out posterior ao check-in com no mínimo 1 noite
    try:
        d_in = datetime.strptime(checkin, "%Y-%m-%d")
        d_out = datetime.strptime(checkout, "%Y-%m-%d")
        noites = (d_out - d_in).days
        if noites < 1:
            conn.close()
            return "O check-out deve ser posterior ao check-in com estadia mínima de 1 noite (RN-01)", 400
    except (ValueError, TypeError):
        conn.close()
        return "Datas informadas em formato inválido", 400

    # RN-02: Capacidade máxima
    if hospedes > acomodacao['capacidadeMaxima']:
        conn.close()
        return f"Capacidade máxima excedida. Máximo permitido: {acomodacao['capacidadeMaxima']} hóspedes (RN-02)", 400

    # RF-19: Disponibilidade
    if not validar_disponibilidade(conn, acomodacao_id, checkin, checkout):
        conn.close()
        return "Acomodação já reservada para o período informado (RF-19).", 409

    valores = calcular_valores(acomodacao['precoNoite'], noites, acomodacao['ehSuperhost'])
    conn.close()

    return render_template(
        "resumo.html",
        acomodacao=acomodacao,
        checkin=checkin,
        checkout=checkout,
        noites=noites,
        hospedes=hospedes,
        valores=valores
    )

# Criação da reserva pendente (UC03 / RF-17 / RF-20)
@app.route('/api/reservas', methods=['POST'])
def criar_reserva():
    if not session.get('usuario_id'):
        return jsonify({"erro": "Não autenticado"}), 401
    
    data = request.get_json() or {}
    acomodacao_id = data.get('acomodacao_id')
    checkin = data.get('checkin')
    checkout = data.get('checkout')
    num_hospedes = data.get('num_hospedes')

    conn = get_db()
    acomodacao = conn.execute("SELECT * FROM acomodacao WHERE id = ?", (acomodacao_id,)).fetchone()
    if not acomodacao:
        conn.close()
        return jsonify({"erro": "Acomodação não encontrada"}), 404

    d_in = datetime.strptime(checkin, "%Y-%m-%d")
    d_out = datetime.strptime(checkout, "%Y-%m-%d")
    noites = (d_out - d_in).days
    if noites < 1:
        conn.close()
        return jsonify({"erro": "Estadia mínima de 1 noite (RN-01)"}), 400

    if num_hospedes > acomodacao['capacidadeMaxima']:
        conn.close()
        return jsonify({"erro": "Capacidade máxima excedida (RN-02)"}), 400

    if not validar_disponibilidade(conn, acomodacao_id, checkin, checkout):
        conn.close()
        return jsonify({"erro": "Acomodação indisponível neste período (RF-19)"}), 409

    valores = calcular_valores(acomodacao['precoNoite'], noites, acomodacao['ehSuperhost'])
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reserva (
            hospede_id, acomodacao_id, checkin, checkOut, numHospedes,
            subtotalDiarias, taxaServico, descontoSuperhost, valorTotal, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE')
    """, (
        session['usuario_id'], acomodacao_id, checkin, checkout, num_hospedes,
        valores['subtotal'], valores['taxaServico'], valores['descontoSuperhost'], valores['valorTotal']
    ))
    reserva_id = cursor.lastrowid
    registrar_auditoria(conn, 'reserva', reserva_id, None, 'PENDENTE', session['usuario_nome'])
    conn.commit()
    conn.close()

    return jsonify({"reserva_id": reserva_id, "redirect_url": url_for('tela_pagamento', id=reserva_id)})

# TELA 2: Pagamento (Seção 3.1)
@app.route('/reservas/<int:id>/pagamento')
def tela_pagamento(id):
    verificar_expiracao_reserva(id)
    conn = get_db()
    reserva = conn.execute("""
        SELECT r.*, a.titulo, a.bairro, a.cidade 
        FROM reserva r 
        JOIN acomodacao a ON r.acomodacao_id = a.id 
        WHERE r.id = ?
    """, (id,)).fetchone()
    conn.close()

    if not reserva:
        return "Reserva não encontrada", 404
    if reserva['status'] == 'CONFIRMADA':
        return redirect(url_for('tela_confirmacao', id=id))
    if reserva['status'] == 'CANCELADA':
        return "Esta reserva foi cancelada ou expirou o tempo limite de 30 minutos (RN-04).", 410

    return render_template("pagamento.html", reserva=reserva)

# Pagamento com Cartão (Síncrono - RF-23 / RF-25 / RF-26)
@app.route('/api/reservas/<int:id>/pagar-cartao', methods=['POST'])
def pagar_cartao(id):
    verificar_expiracao_reserva(id)
    conn = get_db()
    reserva = conn.execute("SELECT * FROM reserva WHERE id = ?", (id,)).fetchone()
    
    if not reserva or reserva['status'] != 'PENDENTE':
        conn.close()
        return jsonify({"erro": "Reserva indisponível ou já expirada"}), 400

    data = request.get_json() or {}
    numero_cartao = data.get('numero_cartao', '')
    
    # RNF-08: Número e CVV não são persistidos
    resp = PaymentGatewaySimulado.processar_cartao(numero_cartao, reserva['valorTotal'])
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pagamento (reserva_id, txid, metodo, valor, codigoAutorizacao, status)
        VALUES (?, ?, 'CARTAO', ?, ?, ?)
    """, (id, resp['txid'], reserva['valorTotal'], resp['codigoAutorizacao'], resp['status']))
    
    if resp['sucesso']:
        cursor.execute("UPDATE reserva SET status = 'CONFIRMADA' WHERE id = ?", (id,))
        registrar_auditoria(conn, 'reserva', id, 'PENDENTE', 'CONFIRMADA', session['usuario_nome'])
        conn.commit()
        # RF-28: Comprovante por e-mail
        EmailServiceSimulado.enviar_confirmacao_reserva(
            session['usuario_email'], id, reserva['valorTotal'], resp['codigoAutorizacao']
        )
        conn.close()
        return jsonify({"status": "APROVADO", "redirect_url": url_for('tela_confirmacao', id=id)})
    else:
        conn.commit()
        conn.close()
        # RF-26: Permite nova tentativa em caso de recusa
        return jsonify({"status": "RECUSADO", "mensagem": "Cartão recusado pela operadora. Tente novamente."}), 422

# Geração de cobrança PIX (RF-23 / RF-24)
@app.route('/api/reservas/<int:id>/gerar-pix', methods=['POST'])
def gerar_pix(id):
    verificar_expiracao_reserva(id)
    conn = get_db()
    reserva = conn.execute("SELECT * FROM reserva WHERE id = ?", (id,)).fetchone()
    if not reserva or reserva['status'] != 'PENDENTE':
        conn.close()
        return jsonify({"erro": "Reserva inválida ou expirada"}), 400

    pix_data = PaymentGatewaySimulado.gerar_cobranca_pix(id, reserva['valorTotal'])
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pagamento (reserva_id, txid, metodo, valor, status)
        VALUES (?, ?, 'PIX', ?, 'PROCESSANDO')
    """, (id, pix_data['txid'], reserva['valorTotal']))
    conn.commit()
    conn.close()

    return jsonify(pix_data)

# Polling de verificação de status
@app.route('/api/reservas/<int:id>/status')
def status_reserva(id):
    verificar_expiracao_reserva(id)
    conn = get_db()
    reserva = conn.execute("SELECT status FROM reserva WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not reserva:
        return jsonify({"erro": "Reserva não encontrada"}), 404
    return jsonify({"status": reserva['status']})

# Webhook assíncrono do Gateway (Seção 3.4 / RF-23)
@app.route('/api/webhook/pix', methods=['POST'])
def webhook_pix():
    data = request.get_json() or {}
    txid = data.get('txid')
    valor_pago = float(data.get('valor', 0.0))

    conn = get_db()
    pagamento = conn.execute("SELECT * FROM pagamento WHERE txid = ?", (txid,)).fetchone()
    if not pagamento:
        conn.close()
        return jsonify({"erro": "Cobrança não localizada"}), 404

    reserva_id = pagamento['reserva_id']
    verificar_expiracao_reserva(reserva_id)
    reserva = conn.execute("SELECT * FROM reserva WHERE id = ?", (reserva_id,)).fetchone()

    if not reserva or reserva['status'] == 'CANCELADA':
        conn.close()
        return jsonify({"erro": "A reserva associada já expirou (RN-04)"}), 400

    if valor_pago < pagamento['valor']:
        conn.close()
        return jsonify({"erro": "Valor pago insuficiente"}), 400

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE pagamento 
        SET status = 'APROVADO', codigoAutorizacao = ? 
        WHERE id = ?
    """, (f"PIX-AUTH-{txid[-6:]}", pagamento['id']))

    cursor.execute("UPDATE reserva SET status = 'CONFIRMADA' WHERE id = ?", (reserva_id,))
    registrar_auditoria(conn, 'reserva', reserva_id, 'PENDENTE', 'CONFIRMADA', 'WEBHOOK_PIX')
    conn.commit()

    EmailServiceSimulado.enviar_confirmacao_reserva(
        "hospede@teste.com", reserva_id, valor_pago, f"PIX-AUTH-{txid[-6:]}"
    )
    conn.close()
    return jsonify({"mensagem": "Pagamento PIX liquidado com sucesso"})

# TELA 3: Confirmação (Seção 3.1 / RNF-05)
@app.route('/reservas/<int:id>/confirmacao')
def tela_confirmacao(id):
    conn = get_db()
    # RNF-05: O endereço completo (rua, cep) é exposto unicamente após status CONFIRMADA
    reserva = conn.execute("""
        SELECT r.*, a.titulo, a.rua, a.bairro, a.cidade, a.estado, a.cep 
        FROM reserva r 
        JOIN acomodacao a ON r.acomodacao_id = a.id 
        WHERE r.id = ?
    """, (id,)).fetchone()
    
    pagamento = conn.execute("""
        SELECT * FROM pagamento 
        WHERE reserva_id = ? AND status = 'APROVADO' 
        ORDER BY id DESC LIMIT 1
    """, (id,)).fetchone()
    conn.close()

    if not reserva or reserva['status'] != 'CONFIRMADA':
        return redirect(url_for('tela_pagamento', id=id))

    return render_template("confirmacao.html", reserva=reserva, pagamento=pagamento)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
