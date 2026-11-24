"""Telas (HTML puro). Os dados são buscados pela API em JavaScript."""

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

paginas = Blueprint("paginas", __name__)


@paginas.before_app_request
def _login_de_teste():
    """Simplificação permitida: na primeira visita a uma TELA, já entra como o
    usuário de teste padrão (Ana, anfitriã). A API não faz isso: sem sessão, ela
    responde 401, e as permissões são sempre conferidas no servidor."""
    if (current_app.config.get("LOGIN_AUTOMATICO") and "usuario_id" not in session
            and request.blueprint == "paginas"):
        session.permanent = True
        session["usuario_id"] = current_app.config["USUARIO_PADRAO_ID"]


@paginas.get("/")
def inicio():
    return redirect(url_for("paginas.lista"))


@paginas.get("/anfitriao/acomodacoes")
def lista():
    return render_template("lista.html")


@paginas.get("/anfitriao/acomodacoes/nova")
def nova():
    return render_template("formulario.html", modo="nova")


@paginas.get("/anfitriao/acomodacoes/<int:acomodacao_id>/editar")
def editar(acomodacao_id):
    return render_template("formulario.html", modo="editar", acomodacao_id=acomodacao_id)


@paginas.get("/anfitriao/acomodacoes/<int:acomodacao_id>/calendario")
def calendario(acomodacao_id):
    return render_template("calendario.html", acomodacao_id=acomodacao_id)


@paginas.get("/anuncios")
def vitrine():
    return render_template("vitrine.html")
