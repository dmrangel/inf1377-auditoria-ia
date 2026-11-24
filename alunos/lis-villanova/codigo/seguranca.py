"""
seguranca.py - Sessão, expiração por inatividade e controle de acesso.

Tudo aqui roda no servidor, antes de cada requisição. O navegador só guarda o
cookie de sessão assinado; quem é o usuário e se ele pode fazer algo é
decidido aqui e nas rotas, nunca no JavaScript.
"""

from functools import wraps

from flask import g, jsonify, redirect, request, session, url_for

import tempo
import usuarios
from database import get_db

MENSAGENS_SAIDA = {
    "NAO_AUTENTICADO": "Entre na sua conta para continuar.",
    "SESSAO_EXPIRADA": "Sua sessão expirou após 30 minutos sem atividade. Entre novamente.",
    "SESSAO_INVALIDADA": "Sua sessão foi encerrada porque a senha foi alterada. Entre novamente.",
}

METODOS_QUE_ALTERAM = {"POST", "PUT", "PATCH", "DELETE"}


def iniciar_sessao(usuario):
    """Abre uma sessão nova para o usuário (descarta qualquer conteúdo anterior)."""
    session.clear()
    session["usuario_id"] = usuario["id"]
    session["versao_sessao"] = usuario["versaoSessao"]
    session["ultima_atividade"] = tempo.agora_utc().timestamp()


def encerrar_sessao():
    session.clear()


def registrar(app):
    @app.before_request
    def exigir_json_nas_alteracoes():
        # Proteção contra CSRF (A-21): um formulário de outro site só consegue
        # enviar form-data ou texto, nunca application/json sem a permissão de
        # CORS, que este servidor não concede. Junto com SameSite=Lax no cookie,
        # isso impede que outro site altere a conta do usuário logado.
        if request.path.startswith("/api/") and request.method in METODOS_QUE_ALTERAM:
            if not request.is_json:
                return jsonify(
                    erro="Envie os dados em JSON.", codigo="CONTENT_TYPE_INVALIDO"
                ), 415
        return None

    @app.before_request
    def carregar_usuario():
        g.usuario = None
        g.motivo_saida = None
        if request.endpoint == "static":
            return
        usuario_id = session.get("usuario_id")
        if usuario_id is None:
            return

        # RNF-09: a sessão expira após 30 minutos sem requisições (A-13).
        agora = tempo.agora_utc().timestamp()
        limite = app.config["TEMPO_INATIVIDADE"].total_seconds()
        if agora - session.get("ultima_atividade", 0) > limite:
            encerrar_sessao()
            g.motivo_saida = "SESSAO_EXPIRADA"
            return

        # Conta excluída ou senha trocada em outro aparelho: a sessão deixa de valer.
        usuario = usuarios.obter(get_db(), usuario_id)
        if usuario is None or usuario["versaoSessao"] != session.get("versao_sessao"):
            encerrar_sessao()
            g.motivo_saida = "SESSAO_INVALIDADA"
            return

        session["ultima_atividade"] = agora
        g.usuario = usuario

    @app.context_processor
    def usuario_nos_templates():
        return {"usuario_atual": g.get("usuario")}


def login_obrigatorio(rota):
    """Recusa a requisição se não houver usuário autenticado e com sessão válida."""

    @wraps(rota)
    def verificada(*args, **kwargs):
        if g.get("usuario") is None:
            codigo = g.get("motivo_saida") or "NAO_AUTENTICADO"
            if request.path.startswith("/api/"):
                return jsonify(erro=MENSAGENS_SAIDA[codigo], codigo=codigo), 401
            return redirect(url_for("paginas.login", motivo=codigo.lower()))
        return rota(*args, **kwargs)

    return verificada
