"""
app.py - Ponto de entrada da aplicação.

Módulo de Cadastro, Autenticação e Configurações de Usuário da Plataforma de
Hospedagem (ERS v1.1: Seções 4.1 e 5.3, UC01 a UC04).

Rodar:  pip install -r requirements.txt  e  python app.py
"""

import os
import secrets
from datetime import timedelta

from flask import Flask, jsonify, request

import seguranca
from api import bp as api_bp
from database import fechar_db, init_db
from paginas import bp as paginas_bp
from servicos.email import ServicoEmailSimulado
from usuarios import ErroNegocio

PASTA = os.path.dirname(os.path.abspath(__file__))
BANCO_PADRAO = os.path.join(PASTA, "hospedagem.db")


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=BANCO_PADRAO,
        POPULAR_DADOS_EXEMPLO=True,
        # Mostra a caixa de e-mails simulada (/emails). Desligar fora de testes locais.
        SIMULACAO_VISIVEL=True,
        # Sem SECRET_KEY no ambiente, gera uma aleatória a cada início: as
        # sessões não sobrevivem a um reinício, mas nenhuma chave fica no código.
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,  # JavaScript não lê o cookie de sessão
        SESSION_COOKIE_SAMESITE="Lax",
        # Seção 3.4 pede HTTPS; localmente roda em HTTP. Em produção: SESSION_COOKIE_SECURE=1.
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        TEMPO_INATIVIDADE=timedelta(minutes=30),  # RNF-09
        MAX_CONTENT_LENGTH=64 * 1024,  # nenhuma requisição deste módulo precisa de mais
    )
    if config:
        app.config.update(config)

    init_db(app.config["DATABASE"], popular=app.config["POPULAR_DADOS_EXEMPLO"])
    app.teardown_appcontext(fechar_db)
    app.extensions["email"] = ServicoEmailSimulado(
        simular_falha=os.environ.get("EMAIL_SIMULAR_FALHA") == "1"
    )

    seguranca.registrar(app)
    app.register_blueprint(paginas_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(ErroNegocio)
    def erro_de_negocio(e):
        return jsonify(erro=e.mensagem, codigo=e.codigo, campos=e.campos), e.status

    @app.errorhandler(413)
    def grande_demais(_e):
        return jsonify(erro="Requisição grande demais.", codigo="REQUISICAO_GRANDE"), 413

    @app.errorhandler(404)
    def nao_encontrado(e):
        if request.path.startswith("/api/"):
            return jsonify(erro="Não encontrado.", codigo="NAO_ENCONTRADO"), 404
        return e

    @app.errorhandler(405)
    def metodo_nao_permitido(e):
        if request.path.startswith("/api/"):
            return jsonify(erro="Método não permitido.", codigo="METODO_NAO_PERMITIDO"), 405
        return e

    @app.after_request
    def cabecalhos_de_seguranca(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        # Os links de e-mail levam tokens na URL; não vazar pelo Referer.
        resposta.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.path.startswith("/api/"):
            resposta.headers.setdefault("Cache-Control", "no-store")
        return resposta

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
