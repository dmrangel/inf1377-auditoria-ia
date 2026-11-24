"""Validação dos dados da acomodação (RF-07), das fotos (RF-08, 3.3) e de datas (RF-10).

Os limites numéricos e de tamanho de texto NÃO estão na ERS; os valores abaixo
são decisões registradas em AMBIGUIDADES.md (A11).
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from servicos_externos.cep import CepInvalido, normalizar_cep, formatar_cep
from servicos_externos.armazenamento import TAMANHO_MAXIMO_BYTES

from .erros import ErroValidacao

# RF-08: "de 5 a 30 fotos por acomodação".
MIN_FOTOS = 5
MAX_FOTOS = 30

# Bloqueio de datas: limite por pedido para evitar pedidos gigantes (decisão A07).
MAX_NOITES_POR_BLOQUEIO = 366

UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

# campo -> (rótulo, mínimo, máximo) de caracteres
LIMITES_TEXTO = {
    "titulo": ("Título", 5, 100),
    "descricao": ("Descrição", 20, 5000),
    "regras": ("Regras da casa", 1, 2000),
    "rua": ("Rua", 1, 200),
    "numero": ("Número", 1, 20),
    "bairro": ("Bairro", 1, 100),
    "cidade": ("Cidade", 1, 100),
}

# campo -> (rótulo, mínimo, máximo)
LIMITES_INTEIROS = {
    "capacidadeMaxima": ("Capacidade máxima", 1, 50),
    "quartos": ("Quartos", 0, 50),       # 0 = estúdio/quarto e sala conjugados
    "banheiros": ("Banheiros", 1, 50),
    "camas": ("Camas", 1, 100),
}

PRECO_MAXIMO_CENTAVOS = 100_000_00  # R$ 100.000,00 por noite


def _texto(valor):
    return "" if valor is None else str(valor).strip()


def preco_para_centavos(valor):
    """Aceita 350, "350", "350.5", "350,50" ou "1.234,56". Devolve inteiro em centavos."""
    texto = _texto(valor).replace("R$", "").replace(" ", "")
    if not texto:
        raise ValueError("Informe o preço por noite.")
    if "," in texto:  # formato brasileiro: ponto = milhar, vírgula = decimal
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        raise ValueError("Preço inválido. Use apenas números, por exemplo 350,00.")
    if not numero.is_finite():
        raise ValueError("Preço inválido.")
    if numero.as_tuple().exponent < -2:
        raise ValueError("O preço pode ter no máximo 2 casas decimais.")
    centavos = int((numero * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if centavos <= 0:
        raise ValueError("O preço por noite deve ser maior que zero.")
    if centavos > PRECO_MAXIMO_CENTAVOS:
        raise ValueError("O preço por noite não pode passar de R$ 100.000,00.")
    return centavos


def validar_dados_acomodacao(dados):
    """Valida os campos de RF-07. Devolve dict limpo ou lança ErroValidacao com
    TODOS os campos inválidos de uma vez (a tela destaca todos)."""
    erros = {}
    limpo = {}

    for campo, (rotulo, minimo, maximo) in LIMITES_TEXTO.items():
        valor = _texto(dados.get(campo))
        if not valor:
            erros[campo] = f"{rotulo} é obrigatório."
        elif len(valor) < minimo:
            erros[campo] = f"{rotulo} deve ter pelo menos {minimo} caracteres."
        elif len(valor) > maximo:
            erros[campo] = f"{rotulo} deve ter no máximo {maximo} caracteres."
        else:
            limpo[campo] = valor

    for campo, (rotulo, minimo, maximo) in LIMITES_INTEIROS.items():
        bruto = dados.get(campo)
        valor = _texto(bruto)
        # Aceita inteiro do JSON ou texto só com dígitos; recusa "2.5", "abc", true/false.
        if isinstance(bruto, bool) or not re.fullmatch(r"\d{1,6}", valor):
            erros[campo] = f"{rotulo} deve ser um número inteiro."
            continue
        numero = int(valor)
        if numero < minimo or numero > maximo:
            erros[campo] = f"{rotulo} deve estar entre {minimo} e {maximo}."
        else:
            limpo[campo] = numero

    try:
        limpo["precoNoite"] = preco_para_centavos(dados.get("precoNoite"))
    except ValueError as e:
        erros["precoNoite"] = str(e)

    try:
        limpo["cep"] = formatar_cep(normalizar_cep(dados.get("cep")))
    except CepInvalido as e:
        erros["cep"] = str(e)

    estado = _texto(dados.get("estado")).upper()
    if estado not in UFS:
        erros["estado"] = "Estado deve ser a sigla de uma UF brasileira, por exemplo RJ."
    else:
        limpo["estado"] = estado

    if erros:
        raise ErroValidacao("Corrija os campos destacados.", campos=erros)
    return limpo


def detectar_tipo_imagem(conteudo):
    """Identifica JPEG ou PNG pelos primeiros bytes (assinatura do arquivo),
    sem confiar na extensão nem no Content-Type enviados pelo navegador."""
    if conteudo[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if conteudo[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return None


def validar_foto(nome, conteudo):
    """ERS 3.3: imagens JPEG/PNG de até 10 MB. Devolve o tipo detectado."""
    rotulo = nome or "arquivo sem nome"
    if not conteudo:
        raise ErroValidacao(f"A foto \"{rotulo}\" está vazia.", campos={"fotos": "Arquivo vazio."})
    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        raise ErroValidacao(
            f"A foto \"{rotulo}\" tem mais de 10 MB.",
            campos={"fotos": "Cada foto pode ter no máximo 10 MB."},
        )
    tipo = detectar_tipo_imagem(conteudo)
    if tipo is None:
        raise ErroValidacao(
            f"A foto \"{rotulo}\" não é JPEG nem PNG.",
            campos={"fotos": "Só são aceitas fotos JPEG ou PNG."},
        )
    return tipo


def validar_quantidade_fotos(total):
    """RF-08 / UC05 fluxo 5a."""
    if total < MIN_FOTOS:
        raise ErroValidacao(
            f"O anúncio precisa de no mínimo {MIN_FOTOS} fotos. Você enviou {total}.",
            campos={"fotos": f"Envie pelo menos {MIN_FOTOS} fotos."},
        )
    if total > MAX_FOTOS:
        raise ErroValidacao(
            f"O anúncio pode ter no máximo {MAX_FOTOS} fotos. Você enviou {total}.",
            campos={"fotos": f"Envie no máximo {MAX_FOTOS} fotos."},
        )


def ler_data(valor, rotulo):
    try:
        return date.fromisoformat(_texto(valor))
    except ValueError:
        raise ErroValidacao(
            f"{rotulo} inválida. Use o formato AAAA-MM-DD.", campos={rotulo.lower(): "Data inválida."}
        )


def validar_periodo_bloqueio(inicio, fim, hoje):
    """RF-10. inicio e fim são NOITES (inclusive). Ver decisão A07."""
    d_inicio = ler_data(inicio, "Data inicial")
    d_fim = ler_data(fim, "Data final")
    if d_fim < d_inicio:
        raise ErroValidacao("A data final não pode ser anterior à data inicial.")
    if d_inicio < hoje:
        raise ErroValidacao("Não é possível bloquear ou desbloquear datas que já passaram.")
    noites = (d_fim - d_inicio).days + 1
    if noites > MAX_NOITES_POR_BLOQUEIO:
        raise ErroValidacao(
            f"Bloqueie no máximo {MAX_NOITES_POR_BLOQUEIO} noites por vez."
        )
    return d_inicio, d_fim
