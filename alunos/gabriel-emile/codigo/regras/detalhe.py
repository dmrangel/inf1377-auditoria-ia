"""Página do anúncio (UC09 e UC20; RF-15; RNF-05; ERS 3.1).

Exibe fotos, descrição, capacidade, regras da casa, avaliações, calendário de
disponibilidade e a localização. A localização segue o RNF-05: o endereço
exato só aparece para quem tem direito a ele (ver pode_ver_endereco_exato).
"""
import calendar
from datetime import date, timedelta

import relogio
from regras import avaliacoes, disponibilidade
from servicos_externos import mapas

MAX_MESES_CALENDARIO = 6
MAX_MESES_FUTURO = 24  # até onde o calendário pode ser navegado


class NaoEncontrado(Exception):
    """Anúncio inexistente ou não visível para este usuário."""


def carregar_acomodacao(con, acomodacao_id, usuario_id):
    """Retorna a linha da acomodação se o usuário puder vê-la.

    Público em geral: só anúncios publicados (ativos, com 5+ fotos e sem
    denúncia de risco em análise). O dono vê o próprio anúncio sempre, para
    conferir como ele aparece (AMBIGUIDADES.md, A06 e A17).
    """
    linha = con.execute(
        """SELECT a.*, u.nome AS anfitriaoNome, u.superhost, u.dataCadastro AS anfitriaoDesde
             FROM acomodacao a JOIN usuario u ON u.id = a.anfitriao_id
            WHERE a.id = ?""",
        (acomodacao_id,),
    ).fetchone()
    if linha is None:
        raise NaoEncontrado()
    eh_dono = usuario_id is not None and linha["anfitriao_id"] == usuario_id
    if not eh_dono and not disponibilidade.acomodacao_publicada(con, acomodacao_id):
        raise NaoEncontrado()
    return linha, eh_dono


def pode_ver_endereco_exato(con, acomodacao, usuario_id):
    """RNF-05: endereço exato só para o hóspede com reserva CONFIRMADA.

    - Visitante (sem login): nunca.
    - Dono do anúncio: sempre (o endereço é dele).
    - Hóspede: se tiver reserva CONFIRMADA nesta acomodação. Reserva
      CONCLUIDA também conta, pois já passou por CONFIRMADA (AMBIGUIDADES.md,
      A07). PENDENTE e CANCELADA não contam.
    Verificado no servidor: o JSON de quem não tem direito NÃO contém rua,
    número nem CEP (não basta esconder na tela).
    """
    if usuario_id is None:
        return False
    if acomodacao["anfitriao_id"] == usuario_id:
        return True
    linha = con.execute(
        """SELECT 1 FROM reserva
            WHERE acomodacao_id = ? AND hospede_id = ?
              AND status IN ('CONFIRMADA', 'CONCLUIDA')
            LIMIT 1""",
        (acomodacao["id"], usuario_id),
    ).fetchone()
    return linha is not None


def montar_localizacao(acomodacao, exato, servico_mapas):
    local = {
        "bairro": acomodacao["bairro"],
        "cidade": acomodacao["cidade"],
        "estado": acomodacao["estado"],
        "enderecoExato": exato,
    }
    if exato:
        local.update({"rua": acomodacao["rua"], "numero": acomodacao["numero"], "cep": acomodacao["cep"]})
    # O serviço de mapas recebe só bairro e cidade: o mapa é sempre aproximado.
    try:
        local["mapa"] = {
            "disponivel": True,
            **servico_mapas.localizacao_aproximada(acomodacao["cidade"], acomodacao["bairro"], acomodacao["estado"]),
        }
    except mapas.LocalNaoEncontrado:
        local["mapa"] = {"disponivel": False, "mensagem": "Não encontramos este bairro no mapa."}
    except mapas.ServicoIndisponivel:
        local["mapa"] = {"disponivel": False, "mensagem": "O mapa está indisponível no momento. Tente mais tarde."}
    return local


def verificar_periodo(con, acomodacao, checkin, checkout, hospedes):
    """Quando o usuário chega da busca, confirma se o período ainda serve.

    Entre a busca e a abertura do anúncio alguém pode ter reservado; por isso
    a página repete as verificações do RF-13 para o período escolhido.
    """
    livre = disponibilidade.livre_no_periodo(con, acomodacao["id"], checkin, checkout)
    cabe = hospedes is None or hospedes <= acomodacao["capacidadeMaxima"]
    mensagens = []
    if not livre:
        mensagens.append("A acomodação não está livre nessas datas. Veja o calendário e escolha outro período.")
    if not cabe:
        mensagens.append(
            f"Esta acomodação recebe no máximo {acomodacao['capacidadeMaxima']} hóspede(s)."
        )
    return {
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "hospedes": hospedes,
        "noites": (checkout - checkin).days,
        "livre": livre,
        "cabe": cabe,
        "disponivel": livre and cabe,
        "mensagens": mensagens,
    }


def montar_detalhe(con, acomodacao, eh_dono, usuario_id, servico_mapas, armazenamento):
    fotos = con.execute(
        "SELECT chave, legenda FROM foto_acomodacao WHERE acomodacao_id = ? ORDER BY ordem, id",
        (acomodacao["id"],),
    ).fetchall()
    exato = pode_ver_endereco_exato(con, acomodacao, usuario_id)
    return {
        "id": acomodacao["id"],
        "titulo": acomodacao["titulo"],
        "descricao": acomodacao["descricao"],
        "precoNoite": acomodacao["precoNoite"],
        "capacidadeMaxima": acomodacao["capacidadeMaxima"],
        "quartos": acomodacao["quartos"],
        "banheiros": acomodacao["banheiros"],
        "camas": acomodacao["camas"],
        "regras": acomodacao["regras"],
        "ativo": bool(acomodacao["ativo"]),
        "ehDono": eh_dono,
        "anfitriao": {
            # Só o primeiro nome e o ano de cadastro: e-mail e telefone não
            # são expostos ao público (LGPD / minimização).
            "nome": avaliacoes.primeiro_nome(acomodacao["anfitriaoNome"]),
            "superhost": bool(acomodacao["superhost"]),
            "desde": (acomodacao["anfitriaoDesde"] or "")[:4],
        },
        "fotos": [{"url": armazenamento.url_publica(f["chave"]), "legenda": f["legenda"]} for f in fotos],
        "localizacao": montar_localizacao(acomodacao, exato, servico_mapas),
        "avaliacoes": avaliacoes.resumo_notas(con, acomodacao["id"]),
    }


def _somar_meses(primeiro_dia, meses):
    ano = primeiro_dia.year + (primeiro_dia.month - 1 + meses) // 12
    mes = (primeiro_dia.month - 1 + meses) % 12 + 1
    return date(ano, mes, 1)


def validar_calendario(args):
    """Parâmetros do calendário: mes=AAAA-MM (padrão: mês atual) e meses=1..6."""
    erros = {}
    hoje = relogio.hoje()
    mes_atual = date(hoje.year, hoje.month, 1)
    bruto = (args.get("mes") or "").strip()
    inicio = mes_atual
    if bruto:
        try:
            ano, mes = bruto.split("-")
            inicio = date(int(ano), int(mes), 1)
        except ValueError:
            erros["mes"] = "Mês inválido. Use o formato AAAA-MM."
    if "mes" not in erros and not (mes_atual <= inicio <= _somar_meses(mes_atual, MAX_MESES_FUTURO)):
        erros["mes"] = f"O calendário mostra do mês atual até {MAX_MESES_FUTURO} meses à frente."
    try:
        meses = int(args.get("meses") or 2)
        if not 1 <= meses <= MAX_MESES_CALENDARIO:
            raise ValueError
    except ValueError:
        erros["meses"] = f"Informe de 1 a {MAX_MESES_CALENDARIO} meses."
        meses = 1
    return inicio, meses, erros


def montar_calendario(con, acomodacao_id, inicio, meses):
    """Calendário de disponibilidade (ERS 3.1, 4.3.2-3).

    Cada dia representa a NOITE que começa nele: "ocupado" significa que não
    dá para dormir lá nessa noite. Um dia ocupado pode ser dia de check-out de
    uma nova reserva. Dias anteriores a hoje aparecem como "passado".
    """
    fim = _somar_meses(inicio, meses)
    ocupadas = disponibilidade.noites_ocupadas(con, acomodacao_id, inicio, fim)
    hoje = relogio.hoje()
    resultado = []
    mes_ini = inicio
    for _ in range(meses):
        _, ultimo = calendar.monthrange(mes_ini.year, mes_ini.month)
        dias = []
        for d in range(1, ultimo + 1):
            dia = date(mes_ini.year, mes_ini.month, d)
            if dia < hoje:
                situacao = "passado"
            elif dia in ocupadas:
                situacao = "ocupado"
            else:
                situacao = "livre"
            dias.append({"data": dia.isoformat(), "situacao": situacao})
        resultado.append({"mes": mes_ini.strftime("%Y-%m"), "dias": dias})
        mes_ini = _somar_meses(mes_ini, 1)
    return {"inicio": inicio.isoformat(), "fim": (fim - timedelta(days=1)).isoformat(), "meses": resultado}
