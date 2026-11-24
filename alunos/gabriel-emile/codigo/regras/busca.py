"""Busca de acomodações (UC08; RF-12, RF-13, RF-14, RF-15, RF-16; RNF-01; RNF-05).

Fluxo: validar_parametros() -> buscar(). A validação devolve mensagens em
linguagem simples por campo (ERS 3.1: "mensagens de erro em linguagem simples").
"""
import math
from datetime import date

import relogio
from db import normalizar
from regras import avaliacoes, disponibilidade

ITENS_POR_PAGINA = 20  # A ERS não fala em paginação (AMBIGUIDADES.md, A15)
MAX_HOSPEDES = 50      # limite de sanidade para o campo, não é regra da ERS
MAX_TEXTO = 100

ORDENACOES = {
    # RF-16: ordenar por preço ou por nota. "relevancia" é o padrão
    # (AMBIGUIDADES.md, A14): melhor nota primeiro, anúncios sem nota no fim.
    "relevancia": "(n.notaMedia IS NULL), n.notaMedia DESC, COALESCE(n.totalAvaliacoes,0) DESC, a.precoNoite ASC, a.id ASC",
    "preco_asc": "a.precoNoite ASC, a.id ASC",
    "preco_desc": "a.precoNoite DESC, a.id ASC",
    "nota_desc": "(n.notaMedia IS NULL), n.notaMedia DESC, COALESCE(n.totalAvaliacoes,0) DESC, a.precoNoite ASC, a.id ASC",
}


class ErroValidacao(Exception):
    def __init__(self, erros):
        super().__init__("Parâmetros inválidos")
        self.erros = erros  # {campo: mensagem}


def _texto(args, campo):
    valor = (args.get(campo) or "").strip()
    return " ".join(valor.split())


def _data(args, campo, nome, erros):
    bruto = (args.get(campo) or "").strip()
    if not bruto:
        erros[campo] = f"Informe a data de {nome}."
        return None
    try:
        return date.fromisoformat(bruto)
    except ValueError:
        erros[campo] = f"A data de {nome} não é válida. Use o formato AAAA-MM-DD."
        return None


def ler_inteiro(args, campo, erros, minimo, maximo=None, obrigatorio=False, msg_obrigatorio=None):
    bruto = (args.get(campo) or "").strip()
    if not bruto:
        if obrigatorio:
            erros[campo] = msg_obrigatorio
        return None
    try:
        valor = int(bruto)
    except ValueError:
        erros[campo] = "Digite um número inteiro."
        return None
    if valor < minimo or (maximo is not None and valor > maximo):
        if maximo is None:
            erros[campo] = f"O valor deve ser {minimo} ou mais."
        else:
            erros[campo] = f"O valor deve estar entre {minimo} e {maximo}."
        return None
    return valor


def _decimal(args, campo, erros):
    bruto = (args.get(campo) or "").strip().replace(",", ".")
    if not bruto:
        return None
    try:
        valor = float(bruto)
    except ValueError:
        valor = None
    if valor is None or not math.isfinite(valor):
        erros[campo] = "Digite um valor em reais, por exemplo 250 ou 250,50."
        return None
    if valor < 0:
        erros[campo] = "O preço não pode ser negativo."
        return None
    return valor


def validar_datas(args, erros):
    """Valida check-in/check-out. Também usada pela página do anúncio."""
    checkin = _data(args, "checkin", "check-in", erros)
    checkout = _data(args, "checkout", "check-out", erros)
    if checkin and checkin < relogio.hoje():
        # A ERS não diz explicitamente; buscar estadia no passado não faz
        # sentido (AMBIGUIDADES.md, A13).
        erros["checkin"] = "A data de check-in não pode estar no passado."
    if checkin and checkout and checkout <= checkin:
        # RN-01: check-out posterior ao check-in, mínimo de 1 noite.
        erros["checkout"] = "A data de check-out deve ser depois do check-in (mínimo de 1 noite)."
    return checkin, checkout


def validar_parametros(args):
    """Converte e valida os parâmetros da busca. Lança ErroValidacao."""
    erros = {}
    p = {}

    # --- Localização (RF-12; ver AMBIGUIDADES.md, A01/A02/A03) -------------
    p["cidade"] = _texto(args, "cidade")
    p["bairro"] = _texto(args, "bairro")
    p["rua"] = _texto(args, "rua")
    p["estado"] = _texto(args, "estado").upper()
    if not p["cidade"]:
        erros["cidade"] = "Informe a cidade."
    if not p["bairro"] and not p["rua"]:
        erros["bairro"] = "Informe o bairro ou a rua desejada."
    for campo in ("cidade", "bairro", "rua"):
        if len(p[campo]) > MAX_TEXTO:
            erros[campo] = f"Use no máximo {MAX_TEXTO} caracteres."
    if p["estado"] and (len(p["estado"]) != 2 or not p["estado"].isalpha()):
        erros["estado"] = "Use a sigla do estado com 2 letras, por exemplo RJ."

    # --- Período (RF-12, RN-01) ---------------------------------------------
    p["checkin"], p["checkout"] = validar_datas(args, erros)

    # --- Hóspedes (RF-12, RF-13) --------------------------------------------
    p["hospedes"] = ler_inteiro(
        args, "hospedes", erros, 1, MAX_HOSPEDES, obrigatorio=True,
        msg_obrigatorio="Informe o número de hóspedes.",
    )

    # --- Filtros opcionais (RF-14; ver AMBIGUIDADES.md, A11/A12) -----------
    p["preco_min"] = _decimal(args, "preco_min", erros)
    p["preco_max"] = _decimal(args, "preco_max", erros)
    if p["preco_min"] is not None and p["preco_max"] is not None and p["preco_min"] > p["preco_max"]:
        erros["preco_max"] = "O preço máximo deve ser maior ou igual ao preço mínimo."
    for campo in ("quartos", "banheiros", "camas"):
        p[campo] = ler_inteiro(args, campo, erros, 0, 50)

    # --- Ordenação (RF-16) e página -----------------------------------------
    p["ordenar"] = (args.get("ordenar") or "relevancia").strip()
    if p["ordenar"] not in ORDENACOES:
        erros["ordenar"] = "Ordenação inválida."
    p["pagina"] = ler_inteiro(args, "pagina", erros, 1) or 1

    if erros:
        raise ErroValidacao(erros)
    return p


def _escapar_like(texto):
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def buscar(con, p, armazenamento):
    """Executa a busca já validada. Retorna dict com itens e paginação.

    Tudo em uma consulta (com subconsultas indexadas) para atender ao RNF-01.
    Nunca devolve rua, número ou CEP (RNF-05): mesmo que o usuário tenha
    buscado pela rua, o resultado mostra apenas bairro e cidade.
    """
    params = {
        "cidade": normalizar(p["cidade"]),
        "checkin": p["checkin"].isoformat(),
        "checkout": p["checkout"].isoformat(),
        "hospedes": p["hospedes"],
        "limite_pendente": disponibilidade.limite_pendente(),
        "limite_prazo": avaliacoes.data_limite_prazo(),
    }
    filtros = [
        "norm(a.cidade) = :cidade",
        disponibilidade.sql_publicado("a"),
        # RF-13: capacidadeMaxima >= número de hóspedes (RN-02).
        "a.capacidadeMaxima >= :hospedes",
        # RF-13: somente acomodações livres no período.
        disponibilidade.sql_livre_no_periodo("a"),
    ]
    if p["bairro"]:
        filtros.append("norm(a.bairro) = :bairro")
        params["bairro"] = normalizar(p["bairro"])
    if p["rua"]:
        # Rua: busca por trecho ("Atlântica" acha "Avenida Atlântica").
        filtros.append("norm(a.rua) LIKE :rua ESCAPE '\\'")
        params["rua"] = "%" + _escapar_like(normalizar(p["rua"])) + "%"
    if p["estado"]:
        filtros.append("UPPER(a.estado) = :estado")
        params["estado"] = p["estado"]
    if p["preco_min"] is not None:
        filtros.append("a.precoNoite >= :preco_min")
        params["preco_min"] = p["preco_min"]
    if p["preco_max"] is not None:
        filtros.append("a.precoNoite <= :preco_max")
        params["preco_max"] = p["preco_max"]
    for campo in ("quartos", "banheiros", "camas"):
        if p[campo] is not None:
            # Filtro por quantidade MÍNIMA (AMBIGUIDADES.md, A12).
            filtros.append(f"a.{campo} >= :{campo}")
            params[campo] = p[campo]

    where = " AND ".join(filtros)
    base = f"""
        FROM acomodacao a
        JOIN usuario u ON u.id = a.anfitriao_id
        LEFT JOIN ({avaliacoes.sql_notas_por_acomodacao()}) n ON n.acomodacao_id = a.id
        WHERE {where}
    """
    total = con.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]

    params["limite"] = ITENS_POR_PAGINA
    params["deslocamento"] = (p["pagina"] - 1) * ITENS_POR_PAGINA
    linhas = con.execute(
        f"""
        SELECT a.id, a.titulo, a.bairro, a.cidade, a.estado, a.precoNoite,
               a.capacidadeMaxima, a.quartos, a.banheiros, a.camas,
               u.superhost,
               n.notaMedia, COALESCE(n.totalAvaliacoes, 0) AS totalAvaliacoes,
               (SELECT f.chave FROM foto_acomodacao f WHERE f.acomodacao_id = a.id
                 ORDER BY f.ordem, f.id LIMIT 1) AS fotoCapa,
               (SELECT f.legenda FROM foto_acomodacao f WHERE f.acomodacao_id = a.id
                 ORDER BY f.ordem, f.id LIMIT 1) AS legendaCapa
        {base}
        ORDER BY {ORDENACOES[p['ordenar']]}
        LIMIT :limite OFFSET :deslocamento
        """,
        params,
    ).fetchall()

    noites = (p["checkout"] - p["checkin"]).days
    itens = [
        {
            "id": l["id"],
            "titulo": l["titulo"],
            "bairro": l["bairro"],
            "cidade": l["cidade"],
            "estado": l["estado"],
            "precoNoite": l["precoNoite"],
            "capacidadeMaxima": l["capacidadeMaxima"],
            "quartos": l["quartos"],
            "banheiros": l["banheiros"],
            "camas": l["camas"],
            "superhost": bool(l["superhost"]),
            "notaMedia": avaliacoes.arredondar_nota(l["notaMedia"]),
            "totalAvaliacoes": l["totalAvaliacoes"],
            "foto": {
                "url": armazenamento.url_publica(l["fotoCapa"]) if l["fotoCapa"] else None,
                "legenda": l["legendaCapa"] or l["titulo"],
            },
        }
        for l in linhas
    ]
    return {
        "itens": itens,
        "total": total,
        "pagina": p["pagina"],
        "itensPorPagina": ITENS_POR_PAGINA,
        "totalPaginas": max(1, -(-total // ITENS_POR_PAGINA)),
        "noites": noites,
    }
