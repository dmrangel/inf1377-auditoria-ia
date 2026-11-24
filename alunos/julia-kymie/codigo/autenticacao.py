"""Login SIMULADO. O login de verdade (RF-03, UC02) não faz parte desta tarefa.

O usuário escolhe "quem está logado" num seletor da página; o servidor grava o
id na sessão (cookie assinado). TODAS as regras de permissão são conferidas no
servidor a partir desse id (ver dominio/acomodacoes.py), nunca no navegador.

RNF-09: a sessão expira após 30 minutos de inatividade
(PERMANENT_SESSION_LIFETIME em app.py, renovada a cada requisição).
"""

from flask import session

from banco import obter_db
from dominio.erros import NaoAutenticado, NaoEncontrado


def usuario_atual():
    """Devolve a linha do usuário logado ou lança 401."""
    usuario_id = session.get("usuario_id")
    if usuario_id is None:
        raise NaoAutenticado("Sua sessão expirou ou você não está logado. Entre novamente.")
    usuario = obter_db().execute(
        "SELECT id, nome, email, ehAnfitriao, superhost FROM usuario WHERE id = ?", (usuario_id,)
    ).fetchone()
    if usuario is None:
        session.clear()
        raise NaoAutenticado("Usuário da sessão não existe mais. Entre novamente.")
    return usuario


def entrar_como(usuario_id):
    usuario = obter_db().execute(
        "SELECT id, nome, ehAnfitriao FROM usuario WHERE id = ?", (usuario_id,)
    ).fetchone()
    if usuario is None:
        raise NaoEncontrado("Usuário de teste não encontrado.")
    session.clear()
    session.permanent = True
    session["usuario_id"] = usuario["id"]
    return usuario


def sair():
    session.clear()
