"""
api.py - Rotas JSON. Cada rota traduz HTTP <-> funções de usuarios.py.

Regras de acesso: toda rota que mexe numa conta usa o usuário da SESSÃO
(g.usuario). Nenhuma rota aceita um id de usuário vindo do navegador, então
não há como alterar a conta de outra pessoa.
"""

import json

from flask import Blueprint, Response, current_app, g, jsonify, request, session, url_for

import usuarios
from database import get_db
from seguranca import encerrar_sessao, iniciar_sessao, login_obrigatorio
from servicos.email import ErroEnvioEmail

bp = Blueprint("api", __name__, url_prefix="/api")


def _corpo():
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


def _enviar_email(destinatario, modelo, dados):
    """Envia pelo serviço externo. Falha do serviço não desfaz a operação (A-19)."""
    try:
        current_app.extensions["email"].enviar(destinatario, modelo, dados)
        return True
    except ErroEnvioEmail as e:
        current_app.logger.warning("Falha ao enviar e-mail %s para %s: %s", modelo, destinatario, e)
        return False


def _link_confirmacao(token):
    return url_for("paginas.confirmar_email", token=token, _external=True)


# ---------------------------------------------------------------------------
# UC01 - Cadastrar usuário
# ---------------------------------------------------------------------------

@bp.post("/cadastro")
def cadastrar():
    d = _corpo()
    conn = get_db()
    usuario_id, token = usuarios.cadastrar(
        conn, d.get("nome"), d.get("email"), d.get("senha"), d.get("telefone"),
        d.get("aceitouTermos"),
    )
    usuario = usuarios.obter(conn, usuario_id)
    # UC01 passo 5: e-mail de confirmação.
    enviado = _enviar_email(
        usuario["email"], "CONFIRMACAO_CADASTRO",
        {"nome": usuario["nome"], "link": _link_confirmacao(token)},
    )
    if enviado:
        mensagem = "Conta criada. Enviamos um e-mail de confirmação. Agora é só entrar."
    else:
        mensagem = ("Conta criada, mas não conseguimos enviar o e-mail de confirmação agora. "
                    "Você pode entrar e pedir um novo envio em Configurações.")
    # A-20: o cadastro não faz login automático.
    return jsonify(mensagem=mensagem, emailEnviado=enviado, email=usuario["email"]), 201


# ---------------------------------------------------------------------------
# UC02 - Efetuar login / sair
# ---------------------------------------------------------------------------

@bp.post("/login")
def login():
    d = _corpo()
    usuario = usuarios.autenticar(get_db(), d.get("email"), d.get("senha"))
    iniciar_sessao(usuario)
    return jsonify(mensagem="Login realizado.", usuario=usuarios.dados_publicos(usuario))


@bp.post("/logout")
def logout():
    encerrar_sessao()
    return jsonify(mensagem="Você saiu da sua conta.")


@bp.get("/me")
@login_obrigatorio
def eu():
    return jsonify(usuario=usuarios.dados_publicos(g.usuario))


# ---------------------------------------------------------------------------
# RF-04 - Recuperação de senha
# ---------------------------------------------------------------------------

@bp.post("/recuperar-senha")
def recuperar_senha():
    resultado = usuarios.solicitar_recuperacao(get_db(), _corpo().get("email"))
    if resultado is not None:
        usuario, token = resultado
        _enviar_email(
            usuario["email"], "RECUPERACAO_SENHA",
            {"nome": usuario["nome"],
             "link": url_for("paginas.redefinir_senha", token=token, _external=True)},
        )
    # A-12: mesma resposta exista ou não a conta, e mesmo que o e-mail falhe.
    return jsonify(mensagem="Se houver uma conta com este e-mail, enviamos um link para "
                            "redefinir a senha. O link vale por 1 hora.")


@bp.post("/redefinir-senha")
def redefinir_senha():
    d = _corpo()
    usuario = usuarios.redefinir_senha(get_db(), d.get("token"), d.get("novaSenha"))
    # Se quem redefiniu estava logado, a sessão antiga não vale mais (versaoSessao mudou).
    encerrar_sessao()
    _enviar_email(usuario["email"], "SENHA_ALTERADA", {"nome": usuario["nome"]})
    return jsonify(mensagem="Senha redefinida. Entre com a nova senha.")


# ---------------------------------------------------------------------------
# UC03 / RF-05 - Alterar dados cadastrais
# ---------------------------------------------------------------------------

@bp.put("/perfil")
@login_obrigatorio
def atualizar_perfil():
    d = _corpo()
    # Só nome e telefone são lidos; qualquer outro campo (email, id, ehAnfitriao...)
    # enviado pelo navegador é ignorado (A-09).
    usuario = usuarios.atualizar_perfil(get_db(), g.usuario["id"], d.get("nome"), d.get("telefone"))
    return jsonify(mensagem="Dados atualizados.", usuario=usuarios.dados_publicos(usuario))


@bp.put("/perfil/senha")
@login_obrigatorio
def alterar_senha():
    d = _corpo()
    nova_versao = usuarios.alterar_senha(
        get_db(), g.usuario["id"], d.get("senhaAtual"), d.get("novaSenha")
    )
    # Mantém esta sessão; as outras (outros aparelhos) passam a ser recusadas (A-10).
    session["versao_sessao"] = nova_versao
    _enviar_email(g.usuario["email"], "SENHA_ALTERADA", {"nome": g.usuario["nome"]})
    return jsonify(mensagem="Senha alterada. Outras sessões abertas foram encerradas.")


@bp.post("/perfil/reenviar-confirmacao")
@login_obrigatorio
def reenviar_confirmacao():
    usuario, token = usuarios.gerar_nova_confirmacao(get_db(), g.usuario["id"])
    enviado = _enviar_email(
        usuario["email"], "CONFIRMACAO_CADASTRO",
        {"nome": usuario["nome"], "link": _link_confirmacao(token)},
    )
    if not enviado:
        return jsonify(erro="Não foi possível enviar o e-mail agora. Tente mais tarde.",
                       codigo="EMAIL_INDISPONIVEL"), 503
    return jsonify(mensagem="Enviamos um novo e-mail de confirmação.")


# ---------------------------------------------------------------------------
# RF-06 / UC04 - Tornar-se anfitrião
# ---------------------------------------------------------------------------

@bp.post("/perfil/tornar-anfitriao")
@login_obrigatorio
def tornar_anfitriao():
    usuario = usuarios.ativar_anfitriao(get_db(), g.usuario["id"])
    _enviar_email(usuario["email"], "ANFITRIAO_ATIVADO", {"nome": usuario["nome"]})
    return jsonify(mensagem="Pronto! Sua conta agora também é de anfitrião.",
                   usuario=usuarios.dados_publicos(usuario))


# ---------------------------------------------------------------------------
# RNF-17 (LGPD) - exportar e excluir os próprios dados
# ---------------------------------------------------------------------------

@bp.get("/meus-dados")
@login_obrigatorio
def exportar_dados():
    dados = usuarios.exportar_dados(get_db(), g.usuario["id"])
    return Response(
        json.dumps(dados, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=meus-dados.json",
                 "Cache-Control": "no-store"},
    )


@bp.delete("/conta")
@login_obrigatorio
def excluir_conta():
    nome, email = usuarios.excluir_conta(get_db(), g.usuario["id"], _corpo().get("senha"))
    encerrar_sessao()
    _enviar_email(email, "CONTA_EXCLUIDA", {"nome": nome})
    return jsonify(mensagem="Sua conta e seus dados pessoais foram excluídos.")


# ---------------------------------------------------------------------------
# Controle da simulação do serviço de e-mail (só existe em modo de simulação)
# ---------------------------------------------------------------------------

@bp.get("/simulacao/emails")
def listar_emails_simulados():
    if not current_app.config["SIMULACAO_VISIVEL"]:
        return jsonify(erro="Não encontrado.", codigo="NAO_ENCONTRADO"), 404
    servico = current_app.extensions["email"]
    return jsonify(simularFalha=servico.simular_falha, mensagens=servico.listar())


@bp.post("/simulacao/email-falha")
def alternar_falha_email():
    if not current_app.config["SIMULACAO_VISIVEL"]:
        return jsonify(erro="Não encontrado.", codigo="NAO_ENCONTRADO"), 404
    servico = current_app.extensions["email"]
    servico.simular_falha = _corpo().get("falhar") is True
    return jsonify(simularFalha=servico.simular_falha)
