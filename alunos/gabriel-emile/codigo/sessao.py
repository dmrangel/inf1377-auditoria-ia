"""Login simulado (simplificação permitida pelo enunciado).

Não há tela de login: o app começa com um hóspede de teste já autenticado
(config USUARIO_TESTE_PADRAO) e o cabeçalho das páginas permite trocar de
usuário de teste ou navegar como visitante. A identidade fica na sessão
assinada do Flask (cookie), então o NAVEGADOR NÃO DECIDE o que pode ver: todas
as regras de acesso (por exemplo, RNF-05) são verificadas no servidor a partir
de usuario_atual_id().

O cadastro e a autenticação reais (RF-01 a RF-04) pertencem a outra
funcionalidade e não foram implementados aqui.
"""
from flask import current_app, session

CHAVE = "usuario_id"


def usuario_atual_id():
    if CHAVE not in session:
        return current_app.config.get("USUARIO_TESTE_PADRAO")
    return session[CHAVE]  # None = visitante


def definir_usuario(usuario_id):
    session[CHAVE] = usuario_id
