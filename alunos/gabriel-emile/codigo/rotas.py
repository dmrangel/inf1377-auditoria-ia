"""Rotas HTTP: API REST em JSON (ERS 3.4) e páginas HTML.

As páginas são HTML estático; todo dado vem da API, que é onde ficam as regras.
"""
import os
import time

from flask import Blueprint, Response, current_app, g, jsonify, request, send_from_directory

import sessao
from db import get_db
from regras import avaliacoes, busca, detalhe
from servicos_externos import armazenamento as arm

api = Blueprint("api", __name__, url_prefix="/api")
paginas = Blueprint("paginas", __name__)

PASTA_PAGINAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paginas")


def erro(mensagem, status, campos=None):
    corpo = {"erro": mensagem}
    if campos:
        corpo["campos"] = campos
    return jsonify(corpo), status


def _servicos():
    return current_app.extensions["servico_mapas"], current_app.extensions["armazenamento"]


# ---------------------------------------------------------------------------
# Sessão / usuário de teste
# ---------------------------------------------------------------------------
@api.get("/sessao")
def obter_sessao():
    uid = sessao.usuario_atual_id()
    usuario = None
    if uid is not None:
        linha = get_db().execute("SELECT id, nome, ehAnfitriao FROM usuario WHERE id = ?", (uid,)).fetchone()
        if linha:
            usuario = {"id": linha["id"], "nome": linha["nome"], "ehAnfitriao": bool(linha["ehAnfitriao"])}
    return jsonify({"usuario": usuario, "loginSimulado": current_app.config["LOGIN_SIMULADO"]})


@api.get("/usuarios-teste")
def usuarios_teste():
    if not current_app.config["LOGIN_SIMULADO"]:
        return erro("Recurso indisponível.", 404)
    linhas = get_db().execute(
        "SELECT id, nome, ehAnfitriao FROM usuario WHERE email LIKE '%@teste.local' ORDER BY id"
    ).fetchall()
    return jsonify([{"id": l["id"], "nome": l["nome"], "ehAnfitriao": bool(l["ehAnfitriao"])} for l in linhas])


@api.post("/sessao")
def trocar_sessao():
    """Troca o usuário de teste. Só existe com LOGIN_SIMULADO ligado."""
    if not current_app.config["LOGIN_SIMULADO"]:
        return erro("Recurso indisponível.", 404)
    dados = request.get_json(silent=True) or {}
    uid = dados.get("usuario_id")
    if uid is not None:
        if not isinstance(uid, int) or isinstance(uid, bool):
            return erro("Usuário inválido.", 400)
        existe = get_db().execute("SELECT 1 FROM usuario WHERE id = ?", (uid,)).fetchone()
        if not existe:
            return erro("Usuário de teste não encontrado.", 404)
    sessao.definir_usuario(uid)
    return obter_sessao()


# ---------------------------------------------------------------------------
# Busca (UC08)
# ---------------------------------------------------------------------------
@api.get("/acomodacoes/busca")
def buscar_acomodacoes():
    try:
        parametros = busca.validar_parametros(request.args)
    except busca.ErroValidacao as e:
        return erro("Confira os campos destacados.", 400, e.erros)
    _, armazenamento = _servicos()
    resultado = busca.buscar(get_db(), parametros, armazenamento)
    if resultado["total"] == 0:
        resultado["mensagem"] = (
            "Nenhuma acomodação disponível com esses critérios. "
            "Tente outras datas, menos filtros ou um bairro vizinho."
        )
    return jsonify(resultado)


# ---------------------------------------------------------------------------
# Anúncio (UC09, UC20)
# ---------------------------------------------------------------------------
def _carregar(acomodacao_id):
    return detalhe.carregar_acomodacao(get_db(), acomodacao_id, sessao.usuario_atual_id())


@api.get("/acomodacoes/<int:acomodacao_id>")
def detalhar_acomodacao(acomodacao_id):
    try:
        acomodacao, eh_dono = _carregar(acomodacao_id)
    except detalhe.NaoEncontrado:
        return erro("Anúncio não encontrado ou indisponível.", 404)
    mapas_srv, armazenamento = _servicos()
    con = get_db()
    resposta = detalhe.montar_detalhe(con, acomodacao, eh_dono, sessao.usuario_atual_id(), mapas_srv, armazenamento)

    # Período vindo da busca (opcional): se informado, precisa ser válido.
    if request.args.get("checkin") or request.args.get("checkout"):
        erros = {}
        checkin, checkout = busca.validar_datas(request.args, erros)
        hospedes = None
        if request.args.get("hospedes"):
            hospedes = busca.ler_inteiro(request.args, "hospedes", erros, 1, busca.MAX_HOSPEDES)
        if erros:
            resposta["periodo"] = {"erros": erros}
        else:
            resposta["periodo"] = detalhe.verificar_periodo(con, acomodacao, checkin, checkout, hospedes)
    return jsonify(resposta)


@api.get("/acomodacoes/<int:acomodacao_id>/avaliacoes")
def listar_avaliacoes(acomodacao_id):
    try:
        _carregar(acomodacao_id)
    except detalhe.NaoEncontrado:
        return erro("Anúncio não encontrado ou indisponível.", 404)
    con = get_db()
    return jsonify({
        **avaliacoes.resumo_notas(con, acomodacao_id),
        "avaliacoes": avaliacoes.listar_avaliacoes_publicas(con, acomodacao_id),
    })


@api.get("/acomodacoes/<int:acomodacao_id>/calendario")
def calendario(acomodacao_id):
    try:
        _carregar(acomodacao_id)
    except detalhe.NaoEncontrado:
        return erro("Anúncio não encontrado ou indisponível.", 404)
    inicio, meses, erros = detalhe.validar_calendario(request.args)
    if erros:
        return erro("Confira os campos destacados.", 400, erros)
    return jsonify(detalhe.montar_calendario(get_db(), acomodacao_id, inicio, meses))


# ---------------------------------------------------------------------------
# Armazenamento de arquivos simulado (fotos)
# ---------------------------------------------------------------------------
@paginas.get("/arquivos/<path:chave>")
def baixar_arquivo(chave):
    _, armazenamento = _servicos()
    try:
        conteudo, tipo = armazenamento.obter(chave)
    except arm.ArquivoNaoEncontrado:
        return Response("Arquivo não encontrado", status=404, mimetype="text/plain")
    except arm.ServicoIndisponivel:
        return Response("Armazenamento indisponível", status=503, mimetype="text/plain")
    resp = Response(conteudo, mimetype=tipo)
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


# ---------------------------------------------------------------------------
# Páginas HTML
# ---------------------------------------------------------------------------
@paginas.get("/")
def pagina_inicial():
    return send_from_directory(PASTA_PAGINAS, "index.html")


@paginas.get("/busca")
def pagina_resultados():
    return send_from_directory(PASTA_PAGINAS, "resultados.html")


@paginas.get("/acomodacao/<int:acomodacao_id>")
def pagina_anuncio(acomodacao_id):
    return send_from_directory(PASTA_PAGINAS, "anuncio.html")


@paginas.get("/ajuda")
def pagina_ajuda():
    return send_from_directory(PASTA_PAGINAS, "ajuda.html")


# ---------------------------------------------------------------------------
# Medição de tempo de resposta (RNF-01)
# ---------------------------------------------------------------------------
def iniciar_cronometro():
    g.inicio = time.perf_counter()


def registrar_tempo(resposta):
    if "inicio" in g:
        ms = (time.perf_counter() - g.inicio) * 1000
        # Cabeçalho padrão Server-Timing: aparece na aba Rede do navegador.
        resposta.headers["Server-Timing"] = f"app;dur={ms:.1f}"
        if request.path == "/api/acomodacoes/busca" and ms > current_app.config["RNF01_LIMITE_MS"]:
            current_app.logger.warning("RNF-01: busca levou %.0f ms (limite %s ms)", ms, current_app.config["RNF01_LIMITE_MS"])
    return resposta
