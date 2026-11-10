"""
app.py - Servidor Web Flask da Plataforma de Hospedagem
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
Responsável: Fluxo de Reserva, Pagamento e Confirmação (ERS v1.2)
"""

import os
from functools import wraps
from datetime import date, timedelta
from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, session, flash, abort
)

from database import init_db, get_db_connection
import models
from services.payment_gateway import PaymentGateway
from services.email_service import EmailService

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "inf1377-ers-hospedagem-secret-key-2026")

# Inicialização automática do banco SQLite na primeira execução
with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Verificação de Autenticação / Sessão do Hóspede
# Regra: "o hóspede precisa estar logado deve ser verificada no servidor"
# ---------------------------------------------------------------------------

@app.before_request
def setup_default_user_session():
    """
    Garante que haja um hóspede autenticado de teste por padrão (id=1, Lucas Hóspede)
    na primeira visita, a menos que o usuário explicitamente alterne para deslogado.
    """
    if "session_initialized" not in session:
        session["session_initialized"] = True
        session["usuario_id"] = 1
        session["usuario_nome"] = "Lucas Hóspede (Teste)"
        session["usuario_email"] = "hospede_teste@exemplo.com"


def login_required(f):
    """Decorator para exigir autenticação no servidor."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("usuario_id"):
            if request.path.startswith("/api/"):
                return jsonify({
                    "sucesso": False,
                    "erro": "Acesso não autorizado. O hóspede precisa estar autenticado no sistema."
                }), 401
            flash("Você precisa estar conectado para realizar ou visualizar reservas.", "error")
            return redirect(url_for("view_resumo"))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Rotas Web do Fluxo (3 Telas conforme Seção 3.1)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Redireciona para o início do fluxo de reserva."""
    return redirect(url_for("view_resumo"))


@app.route("/resumo", methods=["GET", "POST"])
@login_required
def view_resumo():
    """
    Tela 1: Resumo da Estadia (UC10)
    Exibe dados da acomodação, calcula diárias e taxas (RN-03, RN-07, RF-18),
    valida datas (RN-01) e capacidade (RN-02) e protege o endereço exato (RNF-05*).
    Ao submeter via POST, cria a reserva PENDENTE e direciona para a Tela 2.
    """
    if request.method == "POST":
        try:
            hospede_id = session.get("usuario_id")
            acomodacao_id = int(request.form.get("acomodacao_id"))
            check_in = request.form.get("check_in")
            check_out = request.form.get("check_out")
            num_hospedes = int(request.form.get("num_hospedes", 1))

            resultado = models.criar_reserva(
                hospede_id=hospede_id,
                acomodacao_id=acomodacao_id,
                check_in=check_in,
                check_out=check_out,
                num_hospedes=num_hospedes
            )

            # Redireciona para a Tela 2: Pagamento
            return redirect(url_for("view_pagamento", reserva_id=resultado["reserva_id"]))

        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for(
                "view_resumo",
                acomodacao_id=request.form.get("acomodacao_id"),
                check_in=request.form.get("check_in"),
                check_out=request.form.get("check_out"),
                num_hospedes=request.form.get("num_hospedes")
            ))

    # Método GET: Renderiza Tela 1
    acomodacao_id = int(request.args.get("acomodacao_id", 1))
    hoje = date.today()
    check_in_default = (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
    check_out_default = (hoje + timedelta(days=4)).strftime("%Y-%m-%d")

    check_in = request.args.get("check_in", check_in_default)
    check_out = request.args.get("check_out", check_out_default)
    num_hospedes = int(request.args.get("num_hospedes", 2))

    # Obter dados da acomodação (com restrição RNF-05*: rua e número omitidos)
    acomodacao = models.obter_acomodacao_detalhe(acomodacao_id)
    if not acomodacao:
        flash("Acomodação solicitada não foi encontrada.", "error")
        acomodacao = models.obter_acomodacao_detalhe(1)

    # Cálculo inicial dos valores
    try:
        calculos = models.calcular_valores_estadia(
            acomodacao["precoNoite"], check_in, check_out, bool(acomodacao["superhost"])
        )
    except Exception:
        calculos = models.calcular_valores_estadia(
            acomodacao["precoNoite"], check_in_default, check_out_default, bool(acomodacao["superhost"])
        )
        check_in, check_out = check_in_default, check_out_default

    todas_acomodacoes = models.listar_acomodacoes_demonstracao()

    return render_template(
        "resumo.html",
        step=1,
        acomodacao=acomodacao,
        acomodacoes_disponiveis=todas_acomodacoes,
        check_in=check_in,
        check_out=check_out,
        num_hospedes=num_hospedes,
        calculos=calculos
    )


@app.route("/pagamento/<int:reserva_id>", methods=["GET"])
@login_required
def view_pagamento(reserva_id: int):
    """
    Tela 2: Pagamento (UC16)
    Exibe opções de pagamento (Cartão de Crédito e PIX) com contador de 30 minutos (RN-04).
    """
    usuario_id = session.get("usuario_id")
    reserva = models.obter_reserva_completa(reserva_id, usuario_logado_id=usuario_id)

    if not reserva:
        flash("Reserva não encontrada.", "error")
        return redirect(url_for("view_resumo"))

    # RNF-11: Apenas o hóspede dono da reserva pode acessá-la
    if reserva["hospede_id"] != usuario_id:
        flash("Você não tem autorização para acessar esta reserva (RNF-11).", "error")
        return redirect(url_for("view_resumo"))

    # Se já estiver confirmada, redireciona para Tela 3
    if reserva["status"] == "CONFIRMADA":
        return redirect(url_for("view_confirmacao", reserva_id=reserva_id))

    return render_template("pagamento.html", step=2, reserva=reserva)


@app.route("/confirmacao/<int:reserva_id>", methods=["GET"])
@login_required
def view_confirmacao(reserva_id: int):
    """
    Tela 3: Confirmação e Comprovante (UC16 passo 5, RF-20, RF-24, RF-28)
    Exibe o comprovante da estadia e libera o endereço completo apenas após confirmação (RNF-05*).
    """
    usuario_id = session.get("usuario_id")
    reserva = models.obter_reserva_completa(reserva_id, usuario_logado_id=usuario_id)

    if not reserva:
        flash("Reserva não encontrada.", "error")
        return redirect(url_for("view_resumo"))

    # RNF-11: Apenas o hóspede dono ou o anfitrião pode ver
    if reserva["hospede_id"] != usuario_id and reserva["anfitriao_id"] != usuario_id:
        flash("Você não tem permissão para visualizar este comprovante (RNF-11).", "error")
        return redirect(url_for("view_resumo"))

    # Só pode acessar tela 3 se status == CONFIRMADA
    if reserva["status"] != "CONFIRMADA":
        flash("O comprovante só é emitido após a confirmação do pagamento.", "warning")
        return redirect(url_for("view_pagamento", reserva_id=reserva_id))

    return render_template("confirmacao.html", step=3, reserva=reserva)


# ---------------------------------------------------------------------------
# Endpoints da API REST (JSON)
# ---------------------------------------------------------------------------

@app.route("/api/reservas/calcular", methods=["POST"])
def api_calcular_reserva():
    """Endpoint REST para cálculo dinâmico de diárias, taxa de serviço e superhost."""
    dados = request.get_json() or {}
    try:
        preco_noite = float(dados.get("preco_noite", 0))
        check_in = dados.get("check_in")
        check_out = dados.get("check_out")
        eh_superhost = bool(dados.get("eh_superhost", False))

        calculos = models.calcular_valores_estadia(preco_noite, check_in, check_out, eh_superhost)
        return jsonify({"sucesso": True, "calculos": calculos})
    except ValueError as e:
        return jsonify({"sucesso": False, "mensagem": str(e)}), 400


@app.route("/api/pagamento/cartao", methods=["POST"])
@login_required
def api_pagar_cartao():
    """
    Processa pagamento síncrono com Cartão de Crédito (RF-23, RF-24, RF-25, RNF-08).
    Se aprovado, confirma reserva (RF-20) e envia e-mails (RF-28).
    Se recusado, grava recusa e permite nova tentativa (RF-26).
    """
    dados = request.get_json() or {}
    reserva_id = int(dados.get("reserva_id", 0))
    titular = dados.get("titular", "").strip()
    numero_cartao = dados.get("numero_cartao", "").strip()
    validade = dados.get("validade", "").strip()
    cvv = dados.get("cvv", "").strip()

    usuario_id = session.get("usuario_id")
    reserva = models.obter_reserva_completa(reserva_id, usuario_logado_id=usuario_id)

    if not reserva:
        return jsonify({"sucesso": False, "mensagem": "Reserva não encontrada."}), 404

    if reserva["hospede_id"] != usuario_id:
        return jsonify({"sucesso": False, "mensagem": "Não autorizado."}), 403

    # RN-04: Verificar se a reserva já expirou (> 30 min)
    if reserva["status"] != "PENDENTE" or reserva["expirada"]:
        return jsonify({
            "sucesso": False,
            "mensagem": "Esta reserva não está mais pendente ou ultrapassou o limite de 30 minutos (RN-04)."
        }), 400

    # Chamada ao gateway externo simulado
    # RNF-08: O gateway autoriza sem que o sistema armazene número ou CVV no banco
    resultado_gateway = PaymentGateway.authorize_credit_card(
        card_holder=titular,
        card_number=numero_cartao,
        expiration=validade,
        cvv=cvv,
        amount=reserva["valorTotal"],
        reservation_id=reserva_id
    )

    if resultado_gateway["sucesso"]:
        # Pagamento Aprovado: registrar e confirmar reserva
        pagamento_id = models.registrar_tentativa_pagamento(
            reserva_id=reserva_id,
            txid=resultado_gateway["txid"],
            metodo="CARTAO_CREDITO",
            valor=reserva["valorTotal"],
            status="APROVADO",
            codigo_autorizacao=resultado_gateway["codigoAutorizacao"],
            token_cartao=resultado_gateway["tokenCartao"],
            responsavel_id=usuario_id
        )

        # RF-20: Mudança automática para CONFIRMADA sem intervenção manual do anfitrião
        models.confirmar_reserva_apos_pagamento(reserva_id)

        # Buscar dados atualizados para disparar comprovante (agora com endereço completo RNF-05*)
        reserva_atualizada = models.obter_reserva_completa(reserva_id)
        pagamento_registro = {
            "id": pagamento_id,
            "metodo": "Cartão de Crédito",
            "valor": reserva["valorTotal"],
            "txid": resultado_gateway["txid"],
            "codigoAutorizacao": resultado_gateway["codigoAutorizacao"]
        }
        acomodacao_info = {
            "titulo": reserva_atualizada["acomodacao_titulo"],
            "rua": reserva_atualizada["acomodacao_rua"],
            "numero": reserva_atualizada["acomodacao_numero"],
            "bairro": reserva_atualizada["acomodacao_bairro"],
            "cidade": reserva_atualizada["acomodacao_cidade"],
            "estado": reserva_atualizada["acomodacao_estado"],
            "cep": reserva_atualizada["acomodacao_cep"],
            "regras": reserva_atualizada["acomodacao_regras"]
        }

        # RF-28: Emissão de comprovante por e-mail ao hóspede e notificação ao anfitrião
        EmailService.send_reservation_confirmed(
            hospede_email=reserva_atualizada["hospede_email"],
            hospede_nome=reserva_atualizada["hospede_nome"],
            anfitriao_email=reserva_atualizada["anfitriao_email"],
            anfitriao_nome=reserva_atualizada["anfitriao_nome"],
            reserva=reserva_atualizada,
            acomodacao=acomodacao_info,
            pagamento=pagamento_registro
        )

        return jsonify({
            "sucesso": True,
            "status": "APROVADO",
            "mensagem": "Pagamento aprovado com sucesso!",
            "txid": resultado_gateway["txid"],
            "codigoAutorizacao": resultado_gateway["codigoAutorizacao"]
        })
    else:
        # RF-26: Pagamento recusado -> registra histórico RECUSADO e permite nova tentativa
        models.registrar_tentativa_pagamento(
            reserva_id=reserva_id,
            txid=resultado_gateway["txid"],
            metodo="CARTAO_CREDITO",
            valor=reserva["valorTotal"],
            status="RECUSADO",
            codigo_autorizacao=None,
            token_cartao=None,
            responsavel_id=usuario_id
        )

        return jsonify({
            "sucesso": False,
            "status": "RECUSADO",
            "mensagem": resultado_gateway["motivo"]
        }), 400


@app.route("/api/pagamento/pix/gerar", methods=["POST"])
@login_required
def api_gerar_pix():
    """Gera cobrança assíncrona PIX vinculada à reserva (RF-23, RF-24)."""
    dados = request.get_json() or {}
    reserva_id = int(dados.get("reserva_id", 0))

    usuario_id = session.get("usuario_id")
    reserva = models.obter_reserva_completa(reserva_id, usuario_logado_id=usuario_id)

    if not reserva:
        return jsonify({"sucesso": False, "mensagem": "Reserva não encontrada."}), 404

    if reserva["status"] != "PENDENTE" or reserva["expirada"]:
        return jsonify({
            "sucesso": False,
            "mensagem": "Reserva não está pendente ou expirou o prazo de 30 minutos."
        }), 400

    # Gerar cobrança no gateway simulado
    cobranca_pix = PaymentGateway.create_pix_charge(
        amount=reserva["valorTotal"],
        reservation_id=reserva_id
    )

    # Registrar pagamento com status PROCESSANDO
    models.registrar_tentativa_pagamento(
        reserva_id=reserva_id,
        txid=cobranca_pix["txid"],
        metodo="PIX",
        valor=reserva["valorTotal"],
        status="PROCESSANDO",
        codigo_autorizacao=None,
        token_cartao=None,
        responsavel_id=usuario_id
    )

    return jsonify({
        "sucesso": True,
        "cobranca": cobranca_pix
    })


@app.route("/api/webhook/pix", methods=["POST"])
def api_webhook_pix():
    """
    Webhook do Gateway / Banco para notificação assíncrona do PIX (Seção 3.4 e 4.5.2).
    Recebe txid e valor, confere e confirma a reserva automaticamente.
    """
    dados = request.get_json() or {}
    txid = dados.get("txid")
    valor = float(dados.get("valor", 0))

    if not txid:
        return jsonify({"sucesso": False, "mensagem": "txid obrigatório."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, reserva_id, valor, status FROM pagamento WHERE txid = ?;", (txid,))
    pagamento = cursor.fetchone()

    if not pagamento:
        conn.close()
        return jsonify({"sucesso": False, "mensagem": "Cobrança PIX não localizada para o txid informado."}), 404

    # Confere se o valor pago é equivalente
    if abs(pagamento["valor"] - valor) > 0.01:
        conn.close()
        return jsonify({"sucesso": False, "mensagem": "Valor divergente da cobrança."}), 400

    # Atualiza pagamento para APROVADO
    models.atualizar_status_pagamento(
        pagamento_id=pagamento["id"],
        novo_status="APROVADO",
        codigo_autorizacao=f"PIX-OK-{txid[-6:]}",
        responsavel_id=None,
        conn=conn
    )

    # Confirma a reserva
    reserva_id = pagamento["reserva_id"]
    models.confirmar_reserva_apos_pagamento(reserva_id, conn=conn)
    conn.commit()
    conn.close()

    # Envia e-mails de confirmação (RF-28)
    reserva_atualizada = models.obter_reserva_completa(reserva_id)
    pagamento_registro = {
        "id": pagamento["id"],
        "metodo": "PIX Instantâneo",
        "valor": pagamento["valor"],
        "txid": txid,
        "codigoAutorizacao": f"PIX-OK-{txid[-6:]}"
    }
    acomodacao_info = {
        "titulo": reserva_atualizada["acomodacao_titulo"],
        "rua": reserva_atualizada["acomodacao_rua"],
        "numero": reserva_atualizada["acomodacao_numero"],
        "bairro": reserva_atualizada["acomodacao_bairro"],
        "cidade": reserva_atualizada["acomodacao_cidade"],
        "estado": reserva_atualizada["acomodacao_estado"],
        "cep": reserva_atualizada["acomodacao_cep"],
        "regras": reserva_atualizada["acomodacao_regras"]
    }

    EmailService.send_reservation_confirmed(
        hospede_email=reserva_atualizada["hospede_email"],
        hospede_nome=reserva_atualizada["hospede_nome"],
        anfitriao_email=reserva_atualizada["anfitriao_email"],
        anfitriao_nome=reserva_atualizada["anfitriao_nome"],
        reserva=reserva_atualizada,
        acomodacao=acomodacao_info,
        pagamento=pagamento_registro
    )

    return jsonify({
        "sucesso": True,
        "mensagem": "Pagamento PIX confirmado com sucesso e reserva ativada!"
    })


@app.route("/api/reservas/<int:reserva_id>/status", methods=["GET"])
@login_required
def api_status_reserva(reserva_id: int):
    """Consulta rápida de status da reserva para polling do front-end."""
    reserva = models.obter_reserva_completa(reserva_id, usuario_logado_id=session.get("usuario_id"))
    if not reserva:
        return jsonify({"sucesso": False, "mensagem": "Reserva não encontrada"}), 404

    return jsonify({
        "sucesso": True,
        "reserva_id": reserva_id,
        "status": reserva["status"],
        "expirada": reserva["expirada"],
        "segundos_restantes": reserva["segundos_restantes"]
    })


# ---------------------------------------------------------------------------
# Rotas Auxiliares de Teste e Inspeção
# ---------------------------------------------------------------------------

@app.route("/api/dev/switch-user", methods=["POST"])
def api_switch_user():
    """Alterna o usuário logado para facilitar o teste de múltiplos perfis e regras de login."""
    novo_id = int(request.form.get("usuario_id", 1))
    session["session_initialized"] = True
    if novo_id == 0:
        session["usuario_id"] = None
        session["usuario_nome"] = "Visitante (Deslogado)"
        session["usuario_email"] = None
        flash("Você agora está deslogado (visitante).", "info")
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, email FROM usuario WHERE id = ?;", (novo_id,))
        usr = cursor.fetchone()
        conn.close()
        if usr:
            session["usuario_id"] = usr["id"]
            session["usuario_nome"] = usr["nome"]
            session["usuario_email"] = usr["email"]
            flash(f"Sessão alterada para: {usr['nome']}", "success")

    # Retorna para a página anterior ou resumo
    referer = request.headers.get("Referer")
    return redirect(referer or url_for("view_resumo"))


@app.route("/api/dev/emails", methods=["GET"])
def api_dev_emails():
    """Retorna os e-mails enviados em formato JSON para inspeção em testes manuais."""
    return jsonify(EmailService.get_sent_emails())


if __name__ == "__main__":
    print("==================================================================")
    print(" Plataforma de Hospedagem (Airbnb Clone) - INF1377")
    print(" Servidor rodando em: http://127.0.0.1:5000")
    print("==================================================================")
    app.run(debug=True, port=5000)
