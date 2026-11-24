"""
rotas_avaliacao.py - Rotas (telas e API REST) da Avaliação de Estadia
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
UC18 (Avaliar estadia), UC19 (Avaliar hóspede), RF-15, RF-29 a RF-32, RN-06.

Todas as regras de permissão são verificadas no servidor (avaliacoes.py);
a tela só repete as mensagens.
"""

from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

import avaliacoes

avaliacao_bp = Blueprint("avaliacao", __name__)


def login_obrigatorio(f):
    """
    Exige usuário autenticado (verificado no servidor). Não reaproveita
    app.login_required por dois motivos: importar app.py daqui criaria uma
    importação circular, e app.login_required redireciona para /resumo, que também
    exige login e por isso redireciona para si mesmo em laço quando não há usuário.
    Aqui as telas respondem 401 com uma página explicativa.
    """
    @wraps(f)
    def decorada(*args, **kwargs):
        if not session.get("usuario_id"):
            if request.path.startswith("/api/"):
                return jsonify({"sucesso": False, "mensagem": "Você precisa estar conectado para avaliar."}), 401
            return render_template(
                "aviso_avaliacao.html",
                titulo="Entre para continuar",
                mensagem="Você precisa estar conectado para ver e enviar avaliações. "
                         "Escolha um usuário de teste no seletor do topo da página.",
            ), 401
        return f(*args, **kwargs)
    return decorada


@avaliacao_bp.app_template_filter("nota_br")
def nota_br(valor):
    """4.666 -> '4,7' (uma casa decimal, vírgula)."""
    if valor is None:
        return "-"
    return f"{valor:.1f}".replace(".", ",")


@avaliacao_bp.app_template_filter("data_br")
def data_br(valor):
    """'2026-11-18' ou '2026-11-18T10:00:00' -> '18/11/2026'."""
    if not valor:
        return ""
    ano, mes, dia = valor[:10].split("-")
    return f"{dia}/{mes}/{ano}"


@avaliacao_bp.app_template_global("resumo_notas_acomodacao")
def resumo_notas_global(acomodacao_id):
    """
    Usada pela Tela 1 (resumo.html) para mostrar a nota média (RF-15) sem mexer em
    app.view_resumo. Em caso de erro devolve "sem avaliações" para não quebrar o fluxo.
    """
    try:
        return avaliacoes.resumo_notas_acomodacao(acomodacao_id)
    except Exception as erro:  # pragma: no cover - proteção defensiva
        print(f"[rotas_avaliacao] Falha ao calcular nota média: {erro}")
        return {"media": None, "total": 0}


@avaliacao_bp.app_context_processor
def injetar_pendencias():
    """
    Quantidade de avaliações pendentes para o link do cabeçalho (o convite na interface).
    Nunca pode derrubar uma tela do fluxo de reserva: em caso de erro mostra 0.
    """
    try:
        return {"avaliacoes_pendentes_qtd": avaliacoes.contar_pendentes(session.get("usuario_id"))}
    except Exception as erro:  # pragma: no cover - proteção defensiva
        print(f"[rotas_avaliacao] Falha ao contar pendências: {erro}")
        return {"avaliacoes_pendentes_qtd": 0}


# ---------------------------------------------------------------------------
# Telas
# ---------------------------------------------------------------------------

@avaliacao_bp.route("/avaliacoes", methods=["GET"])
@login_obrigatorio
def view_avaliacoes():
    """Avaliações pendentes, enviadas e recebidas do usuário logado."""
    painel = avaliacoes.painel_do_usuario(session["usuario_id"])
    return render_template("avaliacoes_pendentes.html", **painel)


@avaliacao_bp.route("/reservas/<int:reserva_id>/avaliar", methods=["GET"])
@login_obrigatorio
def view_avaliar(reserva_id: int):
    """Formulário de UC18 (hóspede avalia a acomodação) ou UC19 (anfitrião avalia o hóspede)."""
    try:
        situacao = avaliacoes.situacao_para_usuario(reserva_id, session["usuario_id"])
    except avaliacoes.ErroAvaliacao as erro:
        flash(erro.mensagem, "error")
        return redirect(url_for("avaliacao.view_avaliacoes"))
    return render_template(
        "avaliar.html",
        s=situacao,
        nota_minima=avaliacoes.NOTA_MINIMA,
        nota_maxima=avaliacoes.NOTA_MAXIMA,
        comentario_max=avaliacoes.COMENTARIO_MAX_CARACTERES,
    )


@avaliacao_bp.route("/acomodacoes/<int:acomodacao_id>/avaliacoes", methods=["GET"])
def view_avaliacoes_acomodacao(acomodacao_id: int):
    """RF-15: nota média e comentários publicados. Visível também a visitantes (seção 2.3)."""
    try:
        dados = avaliacoes.avaliacoes_publicadas_acomodacao(acomodacao_id)
    except avaliacoes.ErroAvaliacao as erro:
        # Sem redirecionar para /resumo: essa página é pública e /resumo exige login.
        return render_template("aviso_avaliacao.html", titulo="Acomodação não encontrada",
                               mensagem=erro.mensagem), erro.http_status
    return render_template("avaliacoes_acomodacao.html", **dados)


# ---------------------------------------------------------------------------
# API REST (JSON)
# ---------------------------------------------------------------------------

@avaliacao_bp.route("/api/reservas/<int:reserva_id>/avaliacoes", methods=["POST"])
@login_obrigatorio
def api_registrar_avaliacao(reserva_id: int):
    """
    Corpo: {"nota": 1..5, "comentario": "texto opcional"}.
    Respostas: 201 gravada; 400 regra de negócio ou dado inválido; 401 sem login;
    403 não participa da reserva; 404 reserva inexistente; 409 já avaliou (RF-31).
    """
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"sucesso": False, "mensagem": "Envie os dados da avaliação em JSON."}), 400
    try:
        resultado = avaliacoes.registrar_avaliacao(
            reserva_id, session.get("usuario_id"), dados.get("nota"), dados.get("comentario")
        )
    except avaliacoes.ErroAvaliacao as erro:
        return jsonify({"sucesso": False, "mensagem": erro.mensagem}), erro.http_status

    if resultado["publicada"]:
        mensagem = "Avaliação enviada e publicada, porque as duas partes já avaliaram."
    else:
        mensagem = ("Avaliação enviada. Ela será publicada quando a outra parte avaliar "
                    "ou quando o prazo de 14 dias terminar.")
    return jsonify({"sucesso": True, "mensagem": mensagem, "avaliacao": resultado}), 201


@avaliacao_bp.route("/api/acomodacoes/<int:acomodacao_id>/avaliacoes", methods=["GET"])
def api_avaliacoes_acomodacao(acomodacao_id: int):
    """RF-15 em JSON: nota média e avaliações publicadas da acomodação."""
    try:
        dados = avaliacoes.avaliacoes_publicadas_acomodacao(acomodacao_id)
    except avaliacoes.ErroAvaliacao as erro:
        return jsonify({"sucesso": False, "mensagem": erro.mensagem}), erro.http_status
    return jsonify({"sucesso": True, **dados})
