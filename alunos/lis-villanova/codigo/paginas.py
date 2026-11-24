"""
paginas.py - Rotas que devolvem as telas HTML.

As telas só exibem formulários; os dados são enviados à API (api.py) pelo
JavaScript, e é lá que tudo é validado.
"""

from flask import Blueprint, abort, current_app, render_template, request

import usuarios
from database import get_db
from seguranca import MENSAGENS_SAIDA, login_obrigatorio

bp = Blueprint("paginas", __name__)


@bp.get("/")
def inicio():
    return render_template("inicio.html")


@bp.get("/cadastro")
def cadastro():
    return render_template("cadastro.html")


@bp.get("/login")
def login():
    # Só mensagens fixas do servidor são exibidas; o texto nunca vem da URL.
    aviso = MENSAGENS_SAIDA.get((request.args.get("motivo") or "").upper())
    return render_template("login.html", aviso=aviso, email=request.args.get("email", ""))


@bp.get("/recuperar-senha")
def recuperar_senha():
    return render_template("recuperar_senha.html", email=request.args.get("email", ""))


@bp.get("/redefinir-senha")
def redefinir_senha():
    # O token só é validado quando a nova senha é enviada (POST /api/redefinir-senha).
    return render_template("redefinir_senha.html", token=request.args.get("token", ""))


@bp.get("/confirmar-email")
def confirmar_email():
    # Link do e-mail de confirmação (UC01). Abrir o link já confirma.
    try:
        usuario = usuarios.confirmar_email(get_db(), request.args.get("token"))
        return render_template("confirmar_email.html", sucesso=True, nome=usuario["nome"])
    except usuarios.TokenInvalido as e:
        return render_template("confirmar_email.html", sucesso=False, erro=e.mensagem), 400


@bp.get("/configuracoes")
@login_obrigatorio
def configuracoes():
    return render_template("configuracoes.html")


@bp.get("/emails")
def emails():
    # Caixa de saída do serviço de e-mail simulado. Não existiria em produção.
    if not current_app.config["SIMULACAO_VISIVEL"]:
        abort(404)
    return render_template("emails.html")
