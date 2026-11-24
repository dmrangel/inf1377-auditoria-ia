"""Gerenciamento de acomodações — Plataforma de Hospedagem (ERS v1.2, seção 4.2).

Executar:  pip install -r requirements.txt  &&  python app.py
Abre em:   http://127.0.0.1:5000
"""

import os
import secrets
from datetime import date, timedelta

from flask import Flask

import banco
from rotas.api import api, arquivos
from rotas.paginas import paginas
from servicos_externos.armazenamento import ArmazenamentoSimulado, TAMANHO_MAXIMO_BYTES
from servicos_externos.cep import ServicoCepSimulado
from dominio.validacao import MAX_FOTOS

PASTA = os.path.dirname(os.path.abspath(__file__))


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.path.join(PASTA, "instancia", "hospedagem.db"),
        DIRETORIO_ARQUIVOS=os.path.join(PASTA, "instancia", "arquivos"),
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        # RNF-09: sessão expira após 30 min de inatividade (renovada a cada requisição).
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        SESSION_REFRESH_EACH_REQUEST=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",  # cookie não vai em POST de outro site (CSRF)
        # Teto do corpo da requisição: 30 fotos de 10 MB + folga para os campos.
        MAX_CONTENT_LENGTH=MAX_FOTOS * TAMANHO_MAXIMO_BYTES + 1024 * 1024,
        LOGIN_AUTOMATICO=True,
        USUARIO_PADRAO_ID=1,
        SEMEAR=True,
        HOJE=date.today,  # os testes trocam por uma data fixa
        FALHAR_ARMAZENAMENTO=os.environ.get("FALHAR_ARMAZENAMENTO") == "1",
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    # Sistemas externos simulados (ERS 3.3). Trocar aqui pelos clientes reais.
    app.extensions["servico_cep"] = ServicoCepSimulado()
    app.extensions["armazenamento"] = ArmazenamentoSimulado(
        app.config["DIRETORIO_ARQUIVOS"], falhar_sempre=app.config["FALHAR_ARMAZENAMENTO"]
    )

    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(arquivos)
    app.register_blueprint(paginas)
    app.teardown_appcontext(banco.fechar_db)

    banco.inicializar(app)
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
