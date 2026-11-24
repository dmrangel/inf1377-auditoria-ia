"""Plataforma de Hospedagem -- Busca e visualização de acomodações.

ERS v1.2: seção 4.3 (RF-12 a RF-16), RNF-01, RNF-05, UC08 e UC09.

Rodar:
    pip install -r requirements.txt
    python app.py
e abrir http://127.0.0.1:5000
"""
import os
import secrets

from flask import Flask

import db
import rotas
from servicos_externos.armazenamento import ArmazenamentoSimulado
from servicos_externos.mapas import ServicoMapasSimulado

AQUI = os.path.dirname(os.path.abspath(__file__))


def _env_ligado(nome):
    return os.environ.get(nome, "").strip().lower() in ("1", "true", "sim", "yes")


def create_app(config=None):
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.update(
        DATABASE=os.path.join(AQUI, "instancia", "plataforma.db"),
        # Em produção a chave viria de variável de ambiente/cofre de segredos.
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        JSON_SORT_KEYS=False,
        LOGIN_SIMULADO=True,
        USUARIO_TESTE_PADRAO=1,  # Ana (hóspede), ver seed.py
        POPULAR_DADOS_EXEMPLO=True,
        SIMULAR_FALHA_MAPAS=_env_ligado("SIMULAR_FALHA_MAPAS"),
        SIMULAR_FALHA_ARMAZENAMENTO=_env_ligado("SIMULAR_FALHA_ARMAZENAMENTO"),
        RNF01_LIMITE_MS=2000,
        AGORA=None,  # testes fixam a data aqui (relogio.py)
    )
    if config:
        app.config.update(config)

    app.extensions["servico_mapas"] = ServicoMapasSimulado(falhar=app.config["SIMULAR_FALHA_MAPAS"])
    app.extensions["armazenamento"] = ArmazenamentoSimulado(falhar=app.config["SIMULAR_FALHA_ARMAZENAMENTO"])

    db.inicializar_se_preciso(app.config["DATABASE"], popular=app.config["POPULAR_DADOS_EXEMPLO"])

    app.register_blueprint(rotas.api)
    app.register_blueprint(rotas.paginas)
    app.teardown_appcontext(db.fechar_db)
    app.before_request(rotas.iniciar_cronometro)
    app.after_request(rotas.registrar_tempo)
    return app


if __name__ == "__main__":
    # debug desligado: o depurador do Werkzeug permite executar código.
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
