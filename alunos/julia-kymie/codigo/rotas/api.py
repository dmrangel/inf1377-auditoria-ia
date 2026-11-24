"""API REST em JSON (ERS 3.4). Cada rota só traduz HTTP <-> funções do domínio."""

import calendar
from datetime import date

from flask import Blueprint, Response, abort, current_app, jsonify, request

import autenticacao
from banco import obter_db
from dominio import acomodacoes as acom
from dominio.erros import ErroNegocio, ErroValidacao
from servicos_externos.cep import CepInvalido, CepNaoEncontrado, ServicoCepIndisponivel

api = Blueprint("api", __name__)


def _servicos():
    return current_app.extensions["servico_cep"], current_app.extensions["armazenamento"]


def _hoje():
    return current_app.config["HOJE"]()


def _corpo():
    """Aceita JSON ou formulário (multipart), para o mesmo endpoint servir à
    tela (que envia fotos) e a testes via curl."""
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def _fotos_enviadas():
    return [(f.filename or "", f.read()) for f in request.files.getlist("fotos") if f]


@api.errorhandler(ErroNegocio)
def _erro_negocio(e):
    return jsonify(e.para_json()), e.status


@api.errorhandler(413)
def _muito_grande(_e):
    erro = ErroValidacao("O envio passou do tamanho máximo permitido (fotos de até 10 MB, 30 por anúncio).")
    return jsonify(erro.para_json()), 413


# ---------------------------------------------------------------- sessão (simulada)

@api.get("/sessao")
def sessao_atual():
    u = autenticacao.usuario_atual()
    return jsonify({"id": u["id"], "nome": u["nome"], "ehAnfitriao": bool(u["ehAnfitriao"])})


@api.post("/sessao")
def sessao_entrar():
    u = autenticacao.entrar_como(_corpo().get("usuarioId"))
    return jsonify({"id": u["id"], "nome": u["nome"], "ehAnfitriao": bool(u["ehAnfitriao"])})


@api.delete("/sessao")
def sessao_sair():
    autenticacao.sair()
    return "", 204


@api.get("/usuarios-teste")
def usuarios_teste():
    """Lista para o seletor de login simulado."""
    linhas = obter_db().execute("SELECT id, nome, ehAnfitriao FROM usuario ORDER BY id").fetchall()
    return jsonify([{"id": r["id"], "nome": r["nome"], "ehAnfitriao": bool(r["ehAnfitriao"])}
                    for r in linhas])


# ---------------------------------------------------------------- CEP (UC05 passo 3)

@api.get("/cep/<cep>")
def consultar_cep(cep):
    autenticacao.usuario_atual()
    servico_cep, _ = _servicos()
    try:
        return jsonify(servico_cep.buscar(cep))
    except CepInvalido as e:
        return jsonify({"erro": str(e), "codigo": "CEP_INVALIDO"}), 400
    except CepNaoEncontrado as e:
        return jsonify({"erro": str(e), "codigo": "CEP_NAO_ENCONTRADO"}), 404
    except ServicoCepIndisponivel as e:
        return jsonify({"erro": str(e), "codigo": "SERVICO_INDISPONIVEL"}), 503


# ---------------------------------------------------------------- acomodações

@api.get("/minhas-acomodacoes")
def minhas_acomodacoes():
    usuario = autenticacao.usuario_atual()
    return jsonify(acom.listar_do_anfitriao(obter_db(), usuario))


@api.post("/acomodacoes")
def criar():
    usuario = autenticacao.usuario_atual()
    servico_cep, armazenamento = _servicos()
    novo_id, origem = acom.criar_acomodacao(
        obter_db(), usuario, _corpo(), _fotos_enviadas(), servico_cep, armazenamento
    )
    return jsonify({"id": novo_id, "mensagem": "Anúncio publicado.", "origemEndereco": origem}), 201


@api.get("/acomodacoes/<int:acomodacao_id>")
def obter(acomodacao_id):
    usuario = autenticacao.usuario_atual()
    return jsonify(acom.detalhe(obter_db(), usuario, acomodacao_id))


@api.put("/acomodacoes/<int:acomodacao_id>")
def atualizar(acomodacao_id):
    usuario = autenticacao.usuario_atual()
    servico_cep, _ = _servicos()
    origem = acom.atualizar_acomodacao(
        obter_db(), usuario, acomodacao_id, _corpo(), servico_cep, _hoje()
    )
    return jsonify({"mensagem": "Alterações salvas.", "origemEndereco": origem})


@api.post("/acomodacoes/<int:acomodacao_id>/fotos")
def adicionar_fotos(acomodacao_id):
    usuario = autenticacao.usuario_atual()
    _, armazenamento = _servicos()
    total = acom.adicionar_fotos(obter_db(), usuario, acomodacao_id, _fotos_enviadas(), armazenamento)
    return jsonify({"mensagem": "Fotos adicionadas.", "totalFotos": total}), 201


@api.delete("/acomodacoes/<int:acomodacao_id>/fotos/<int:foto_id>")
def remover_foto(acomodacao_id, foto_id):
    usuario = autenticacao.usuario_atual()
    _, armazenamento = _servicos()
    total = acom.remover_foto(obter_db(), usuario, acomodacao_id, foto_id, armazenamento)
    return jsonify({"mensagem": "Foto removida.", "totalFotos": total})


@api.post("/acomodacoes/<int:acomodacao_id>/desativar")
def desativar(acomodacao_id):
    usuario = autenticacao.usuario_atual()
    confirmar = bool(_corpo().get("confirmar"))
    mantidas = acom.desativar(obter_db(), usuario, acomodacao_id, confirmar, _hoje())
    msg = "Anúncio desativado. Ele não aparece mais nas buscas."
    if mantidas:
        msg += f" As {mantidas} reserva(s) futura(s) foram mantidas."
    return jsonify({"mensagem": msg, "reservasMantidas": mantidas})


@api.post("/acomodacoes/<int:acomodacao_id>/reativar")
def reativar(acomodacao_id):
    usuario = autenticacao.usuario_atual()
    acom.reativar(obter_db(), usuario, acomodacao_id)
    return jsonify({"mensagem": "Anúncio publicado novamente."})


@api.get("/acomodacoes/<int:acomodacao_id>/reservas")
def reservas(acomodacao_id):
    usuario = autenticacao.usuario_atual()
    return jsonify(acom.reservas_da_acomodacao(obter_db(), usuario, acomodacao_id))


# ---------------------------------------------------------------- calendário (RF-10)

@api.get("/acomodacoes/<int:acomodacao_id>/calendario")
def ver_calendario(acomodacao_id):
    usuario = autenticacao.usuario_atual()
    mes = request.args.get("mes") or _hoje().strftime("%Y-%m")
    try:
        ano, m = (int(p) for p in mes.split("-"))
        inicio = date(ano, m, 1)
    except (ValueError, TypeError):
        raise ErroValidacao("Mês inválido. Use o formato AAAA-MM.")
    fim = date(ano, m, calendar.monthrange(ano, m)[1])
    dados = acom.calendario(obter_db(), usuario, acomodacao_id, inicio, fim)
    dados.update({"mes": inicio.strftime("%Y-%m"), "hoje": _hoje().isoformat()})
    return jsonify(dados)


@api.post("/acomodacoes/<int:acomodacao_id>/bloqueios")
def bloquear(acomodacao_id):
    usuario = autenticacao.usuario_atual()
    corpo = _corpo()
    n = acom.bloquear_datas(obter_db(), usuario, acomodacao_id,
                            corpo.get("inicio"), corpo.get("fim"), _hoje())
    return jsonify({"mensagem": f"{n} noite(s) bloqueada(s).", "noitesBloqueadas": n}), 201


@api.delete("/acomodacoes/<int:acomodacao_id>/bloqueios")
def desbloquear(acomodacao_id):
    usuario = autenticacao.usuario_atual()
    corpo = _corpo() or request.args.to_dict()
    n = acom.desbloquear_datas(obter_db(), usuario, acomodacao_id,
                               corpo.get("inicio"), corpo.get("fim"), _hoje())
    return jsonify({"mensagem": f"{n} noite(s) desbloqueada(s).", "noitesDesbloqueadas": n})


# ---------------------------------------------------------------- vitrine pública

@api.get("/anuncios")
def anuncios():
    """Sem login: só anúncios ativos, sem rua nem número (RNF-05)."""
    return jsonify(acom.anuncios_publicos(obter_db()))


# ---------------------------------------------------------------- arquivos

arquivos = Blueprint("arquivos", __name__)


@arquivos.get("/arquivos/<chave>")
def servir_arquivo(chave):
    """Faz o papel da URL pública do serviço de armazenamento."""
    _, armazenamento = _servicos()
    try:
        dados, tipo = armazenamento.ler(chave)
    except FileNotFoundError:
        abort(404)
    resposta = Response(dados, mimetype=tipo)
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    return resposta
