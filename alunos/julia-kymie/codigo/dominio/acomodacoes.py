"""Casos de uso UC05 (Cadastrar), UC06 (Alterar) e UC07 (Remover = desativar)
acomodação, bloqueio de datas (RF-10) e listagem ao anfitrião (RF-11).

Todas as funções recebem o usuário autenticado e conferem no servidor se ele
pode fazer a operação (RNF-11). As rotas em rotas/api.py só traduzem HTTP.
"""

from datetime import datetime, timedelta

from servicos_externos.cep import (
    CepInvalido,
    CepNaoEncontrado,
    ServicoCepIndisponivel,
)
from servicos_externos.armazenamento import ArmazenamentoIndisponivel, ArquivoRecusado

from .erros import (
    AcessoNegado,
    Conflito,
    ConfirmacaoNecessaria,
    ErroValidacao,
    NaoEncontrado,
    ServicoIndisponivel,
)
from . import validacao as v

# Status de reserva que ocupam as noites da acomodação (RF-19/RF-20).
STATUS_QUE_OCUPAM = ("PENDENTE", "CONFIRMADA")

CAMPOS_EDITAVEIS = (
    "titulo", "descricao", "precoNoite", "capacidadeMaxima", "quartos", "banheiros",
    "camas", "regras", "cep", "rua", "numero", "bairro", "cidade", "estado",
)


# --------------------------------------------------------------------------
# Autorização (RNF-11)
# --------------------------------------------------------------------------

def exigir_anfitriao(usuario):
    """Só quem tem o papel de anfitrião (usuario.ehAnfitriao) anuncia espaços.
    Ativar o papel é o RF-06/UC04, fora desta funcionalidade (decisão A08)."""
    if not usuario["ehAnfitriao"]:
        raise AcessoNegado(
            "Sua conta ainda não tem o papel de anfitrião. Ative-o no seu perfil para anunciar espaços."
        )


def obter_do_dono(db, acomodacao_id, usuario):
    """RNF-11: apenas o anfitrião dono pode editar a acomodação ou ver suas reservas.
    Devolve 404 se não existe e 403 se existe mas é de outro anfitrião (decisão A09)."""
    exigir_anfitriao(usuario)
    linha = db.execute("SELECT * FROM acomodacao WHERE id = ?", (acomodacao_id,)).fetchone()
    if linha is None:
        raise NaoEncontrado("Acomodação não encontrada.")
    if linha["anfitriao_id"] != usuario["id"]:
        raise AcessoNegado("Você não é o anfitrião desta acomodação.")
    return linha


# --------------------------------------------------------------------------
# Endereço via serviço de CEP (ERS 3.3, UC05 passo 3 e fluxo 3a)
# --------------------------------------------------------------------------

def resolver_endereco(dados, servico_cep):
    """Consulta o CEP de novo no servidor (não confia no que o navegador preencheu).

    - CEP encontrado: rua, bairro, cidade e estado devolvidos pelo serviço
      prevalecem sobre o que veio do formulário ("validar o endereço", 3.3).
      Campos que o serviço devolve vazios (CEP geral de cidade) ficam com o
      valor digitado pelo anfitrião.
    - CEP não encontrado ou serviço fora do ar: vale o endereço digitado
      (UC05 fluxo 3a; queda do serviço tratada igual, decisão A10).
    Devolve (dados, origem) onde origem descreve de onde veio o endereço.
    """
    dados = dict(dados)
    try:
        endereco = servico_cep.buscar(dados.get("cep"))
    except CepInvalido:
        return dados, "invalido"  # o erro de formato é apontado na validação
    except CepNaoEncontrado:
        return dados, "manual_cep_nao_encontrado"
    except ServicoCepIndisponivel:
        return dados, "manual_servico_indisponivel"
    for campo in ("rua", "bairro", "cidade", "estado"):
        if endereco.get(campo):
            dados[campo] = endereco[campo]
    dados["cep"] = endereco["cep"]
    return dados, "servico_cep"


# --------------------------------------------------------------------------
# Fotos (RF-08, ERS 3.3)
# --------------------------------------------------------------------------

def _validar_arquivos(fotos):
    """fotos: lista de (nome_original, bytes). Devolve lista de (nome, bytes, tipo)."""
    return [(nome, conteudo, v.validar_foto(nome, conteudo)) for nome, conteudo in fotos]


def _gravar_fotos(db, acomodacao_id, fotos_validadas, armazenamento, ordem_inicial):
    """Envia cada foto ao armazenamento e registra a chave no banco.
    Se o armazenamento falhar no meio, apaga as que já foram enviadas para não
    deixar arquivos órfãos; quem chamou faz o rollback do banco."""
    gravadas = []
    agora = datetime.now().isoformat(timespec="seconds")
    try:
        for i, (nome, conteudo, tipo) in enumerate(fotos_validadas):
            chave = armazenamento.salvar(conteudo, tipo, nome)
            gravadas.append(chave)
            db.execute(
                "INSERT INTO foto (acomodacao_id, chave, tipoConteudo, tamanhoBytes, ordem, dataEnvio)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (acomodacao_id, chave, tipo, len(conteudo), ordem_inicial + i, agora),
            )
    except (ArmazenamentoIndisponivel, ArquivoRecusado) as e:
        for chave in gravadas:
            armazenamento.remover(chave)
        if isinstance(e, ArquivoRecusado):
            raise ErroValidacao(str(e), campos={"fotos": str(e)})
        raise ServicoIndisponivel(str(e))
    return gravadas


def _contar_fotos(db, acomodacao_id):
    return db.execute(
        "SELECT COUNT(*) FROM foto WHERE acomodacao_id = ?", (acomodacao_id,)
    ).fetchone()[0]


# --------------------------------------------------------------------------
# UC05 — Cadastrar acomodação (RF-07, RF-08)
# --------------------------------------------------------------------------

def criar_acomodacao(db, usuario, dados, fotos, servico_cep, armazenamento):
    """UC05 passos 3 a 6. Valida tudo ANTES de gravar qualquer coisa; se
    algo falha, nada fica salvo (nem acomodação, nem fotos).
    Publicação imediata: o anúncio nasce com ativo = 1 (decisão A04)."""
    exigir_anfitriao(usuario)

    dados, origem = resolver_endereco(dados, servico_cep)

    # Junta os erros de campos e de fotos para a tela mostrar tudo de uma vez.
    erros = {}
    mensagem = None
    limpo = None
    try:
        limpo = v.validar_dados_acomodacao(dados)
    except ErroValidacao as e:
        erros.update(e.campos)
        mensagem = e.mensagem
    fotos_validadas = []
    try:
        v.validar_quantidade_fotos(len(fotos))  # UC05 fluxo 5a
        fotos_validadas = _validar_arquivos(fotos)
    except ErroValidacao as e:
        erros.update(e.campos)
        mensagem = e.mensagem if not mensagem else mensagem
    if erros:
        if "fotos" in erros and len(erros) == 1:
            raise ErroValidacao(mensagem, campos=erros)
        raise ErroValidacao("Corrija os campos destacados.", campos=erros)

    try:
        cursor = db.execute(
            "INSERT INTO acomodacao (anfitriao_id, titulo, descricao, precoNoite, capacidadeMaxima,"
            " quartos, banheiros, camas, regras, cep, rua, numero, bairro, cidade, estado, ativo)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (usuario["id"], limpo["titulo"], limpo["descricao"], limpo["precoNoite"],
             limpo["capacidadeMaxima"], limpo["quartos"], limpo["banheiros"], limpo["camas"],
             limpo["regras"], limpo["cep"], limpo["rua"], limpo["numero"], limpo["bairro"],
             limpo["cidade"], limpo["estado"]),
        )
        acomodacao_id = cursor.lastrowid
        _gravar_fotos(db, acomodacao_id, fotos_validadas, armazenamento, ordem_inicial=1)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return acomodacao_id, origem


# --------------------------------------------------------------------------
# UC06 — Alterar acomodação (RF-09)
# --------------------------------------------------------------------------

def _reservas_futuras_ativas(db, acomodacao_id, hoje):
    """Reservas PENDENTE/CONFIRMADA que ainda não terminaram (inclui estadia em curso)."""
    return db.execute(
        "SELECT r.id, r.checkIn, r.checkOut, r.numHospedes, r.status, u.nome AS hospede"
        " FROM reserva r JOIN usuario u ON u.id = r.hospede_id"
        " WHERE r.acomodacao_id = ? AND r.status IN (?, ?) AND r.checkOut > ?"
        " ORDER BY r.checkIn",
        (acomodacao_id, *STATUS_QUE_OCUPAM, hoje.isoformat()),
    ).fetchall()


def atualizar_acomodacao(db, usuario, acomodacao_id, dados, servico_cep, hoje):
    """UC06. Recebe o formulário completo (mesmos campos e regras do cadastro).
    O novo preço vale só para reservas futuras: o valorTotal das reservas já
    criadas fica gravado nelas (decisão A12)."""
    obter_do_dono(db, acomodacao_id, usuario)
    dados, origem = resolver_endereco(dados, servico_cep)
    limpo = v.validar_dados_acomodacao(dados)

    # Decisão A12: não deixar a capacidade ficar menor que uma reserva já feita,
    # senão a reserva existente passaria a violar RN-02.
    reservas = _reservas_futuras_ativas(db, acomodacao_id, hoje)
    maior = max((r["numHospedes"] for r in reservas), default=0)
    if limpo["capacidadeMaxima"] < maior:
        raise Conflito(
            f"Há reserva ativa para {maior} hóspedes. A capacidade máxima não pode ficar menor que {maior}.",
            campos={"capacidadeMaxima": f"Mínimo de {maior} por causa de reservas já feitas."},
        )

    db.execute(
        "UPDATE acomodacao SET titulo=?, descricao=?, precoNoite=?, capacidadeMaxima=?, quartos=?,"
        " banheiros=?, camas=?, regras=?, cep=?, rua=?, numero=?, bairro=?, cidade=?, estado=?"
        " WHERE id = ?",
        tuple(limpo[c] for c in CAMPOS_EDITAVEIS) + (acomodacao_id,),
    )
    db.commit()
    return origem


def adicionar_fotos(db, usuario, acomodacao_id, fotos, armazenamento):
    """UC06 (fotos). O total depois da inclusão não pode passar de 30 (RF-08)."""
    obter_do_dono(db, acomodacao_id, usuario)
    if not fotos:
        raise ErroValidacao("Selecione ao menos uma foto.", campos={"fotos": "Nenhuma foto enviada."})
    atual = _contar_fotos(db, acomodacao_id)
    if atual + len(fotos) > v.MAX_FOTOS:
        raise ErroValidacao(
            f"O anúncio já tem {atual} fotos e o máximo é {v.MAX_FOTOS}. "
            f"Você pode adicionar no máximo {v.MAX_FOTOS - atual}.",
            campos={"fotos": f"Máximo de {v.MAX_FOTOS} fotos por acomodação."},
        )
    validadas = _validar_arquivos(fotos)
    ultima = db.execute(
        "SELECT COALESCE(MAX(ordem), 0) FROM foto WHERE acomodacao_id = ?", (acomodacao_id,)
    ).fetchone()[0]
    try:
        _gravar_fotos(db, acomodacao_id, validadas, armazenamento, ordem_inicial=ultima + 1)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return atual + len(fotos)


def remover_foto(db, usuario, acomodacao_id, foto_id, armazenamento):
    """UC06 (fotos). Não deixa o anúncio ficar com menos de 5 fotos (RF-08).
    Vale também para anúncio desativado, para que ele possa ser reativado (A14)."""
    obter_do_dono(db, acomodacao_id, usuario)
    foto = db.execute(
        "SELECT * FROM foto WHERE id = ? AND acomodacao_id = ?", (foto_id, acomodacao_id)
    ).fetchone()
    if foto is None:
        raise NaoEncontrado("Foto não encontrada nesta acomodação.")
    atual = _contar_fotos(db, acomodacao_id)
    if atual - 1 < v.MIN_FOTOS:
        raise Conflito(
            f"O anúncio precisa ter no mínimo {v.MIN_FOTOS} fotos. Adicione outra foto antes de remover esta."
        )
    db.execute("DELETE FROM foto WHERE id = ?", (foto_id,))
    db.commit()
    # Só apaga o arquivo depois do commit: se o banco falhar, a foto continua válida.
    armazenamento.remover(foto["chave"])
    return atual - 1


# --------------------------------------------------------------------------
# UC07 — Remover acomodação = desativar anúncio (RF-09, decisão A02/A03)
# --------------------------------------------------------------------------

def desativar(db, usuario, acomodacao_id, confirmar, hoje):
    """Exclusão lógica (ativo = 0). O anúncio some das buscas e não recebe novas
    reservas, mas as reservas existentes continuam valendo: cancelar é o UC12,
    com reembolso (RN-05), e não é feito aqui (decisão A03). Se houver reservas
    futuras ativas, o anfitrião precisa confirmar que está ciente."""
    acomodacao = obter_do_dono(db, acomodacao_id, usuario)
    if not acomodacao["ativo"]:
        raise Conflito("Este anúncio já está desativado.")
    reservas = _reservas_futuras_ativas(db, acomodacao_id, hoje)
    if reservas and not confirmar:
        raise ConfirmacaoNecessaria(
            f"Esta acomodação tem {len(reservas)} reserva(s) futura(s) ativa(s). "
            "Elas NÃO serão canceladas ao desativar o anúncio. Confirme para continuar.",
            detalhes=[_reserva_para_json(r) for r in reservas],
        )
    db.execute("UPDATE acomodacao SET ativo = 0 WHERE id = ?", (acomodacao_id,))
    db.commit()
    return len(reservas)


def reativar(db, usuario, acomodacao_id):
    """Volta a publicar. RF-09 não fala em reativar; ver decisão A14."""
    acomodacao = obter_do_dono(db, acomodacao_id, usuario)
    if acomodacao["ativo"]:
        raise Conflito("Este anúncio já está ativo.")
    if _contar_fotos(db, acomodacao_id) < v.MIN_FOTOS:  # defesa extra; remover_foto já impede
        raise Conflito(f"Adicione pelo menos {v.MIN_FOTOS} fotos antes de reativar.")
    db.execute("UPDATE acomodacao SET ativo = 1 WHERE id = ?", (acomodacao_id,))
    db.commit()


# --------------------------------------------------------------------------
# RF-10 — Bloquear datas no calendário
# --------------------------------------------------------------------------

def _noites(inicio, fim):
    d = inicio
    while d <= fim:
        yield d
        d += timedelta(days=1)


def bloquear_datas(db, usuario, acomodacao_id, inicio, fim, hoje):
    """Bloqueia as noites de `inicio` até `fim` (inclusive). Não deixa bloquear
    noite já ocupada por reserva PENDENTE/CONFIRMADA (decisão A07): para liberar
    essa noite seria preciso cancelar a reserva (UC12)."""
    obter_do_dono(db, acomodacao_id, usuario)
    d_inicio, d_fim = v.validar_periodo_bloqueio(inicio, fim, hoje)

    # Reserva ocupa as noites de checkIn até checkOut - 1.
    conflitos = db.execute(
        "SELECT id, checkIn, checkOut, status FROM reserva"
        " WHERE acomodacao_id = ? AND status IN (?, ?) AND checkIn <= ? AND checkOut > ?"
        " ORDER BY checkIn",
        (acomodacao_id, *STATUS_QUE_OCUPAM, d_fim.isoformat(), d_inicio.isoformat()),
    ).fetchall()
    if conflitos:
        raise Conflito(
            "Há reservas no período escolhido. Datas reservadas não podem ser bloqueadas.",
            detalhes=[dict(c) for c in conflitos],
        )

    novas = 0
    for d in _noites(d_inicio, d_fim):
        cur = db.execute(
            "INSERT OR IGNORE INTO bloqueio_data (acomodacao_id, data) VALUES (?, ?)",
            (acomodacao_id, d.isoformat()),
        )
        novas += cur.rowcount
    db.commit()
    return novas


def desbloquear_datas(db, usuario, acomodacao_id, inicio, fim, hoje):
    obter_do_dono(db, acomodacao_id, usuario)
    d_inicio, d_fim = v.validar_periodo_bloqueio(inicio, fim, hoje)
    cur = db.execute(
        "DELETE FROM bloqueio_data WHERE acomodacao_id = ? AND data BETWEEN ? AND ?",
        (acomodacao_id, d_inicio.isoformat(), d_fim.isoformat()),
    )
    db.commit()
    return cur.rowcount


def calendario(db, usuario, acomodacao_id, inicio, fim):
    """Noites bloqueadas e noites reservadas entre inicio e fim (datas)."""
    obter_do_dono(db, acomodacao_id, usuario)  # mostra reservas: só o dono (RNF-11)
    bloqueadas = [
        r["data"] for r in db.execute(
            "SELECT data FROM bloqueio_data WHERE acomodacao_id = ? AND data BETWEEN ? AND ?"
            " ORDER BY data",
            (acomodacao_id, inicio.isoformat(), fim.isoformat()),
        )
    ]
    reservas = db.execute(
        "SELECT r.id, r.checkIn, r.checkOut, r.numHospedes, r.status, u.nome AS hospede"
        " FROM reserva r JOIN usuario u ON u.id = r.hospede_id"
        " WHERE r.acomodacao_id = ? AND r.status IN (?, ?) AND r.checkIn <= ? AND r.checkOut > ?",
        (acomodacao_id, *STATUS_QUE_OCUPAM, fim.isoformat(), inicio.isoformat()),
    ).fetchall()
    reservadas = {}
    for r in reservas:
        d = datetime.fromisoformat(r["checkIn"]).date()
        saida = datetime.fromisoformat(r["checkOut"]).date()
        while d < saida:
            if inicio <= d <= fim:
                reservadas[d.isoformat()] = {"reservaId": r["id"], "status": r["status"]}
            d += timedelta(days=1)
    return {"bloqueadas": bloqueadas, "reservadas": reservadas}


# --------------------------------------------------------------------------
# RF-11 — Listar acomodações e reservas recebidas
# --------------------------------------------------------------------------

def _reserva_para_json(r):
    """Ao anfitrião mostramos só o nome do hóspede (minimização, LGPD; decisão A15)."""
    d = dict(r)
    if "valorTotal" in d:
        d["valorTotal"] = centavos_para_texto(d["valorTotal"])
    return d


def centavos_para_texto(centavos):
    return f"{centavos // 100}.{centavos % 100:02d}"


def _foto_para_json(f):
    return {"id": f["id"], "url": f"/arquivos/{f['chave']}", "ordem": f["ordem"],
            "tipo": f["tipoConteudo"], "tamanhoBytes": f["tamanhoBytes"]}


def acomodacao_para_json(a, fotos=None):
    d = dict(a)
    d["precoNoiteCentavos"] = d["precoNoite"]
    d["precoNoite"] = centavos_para_texto(d["precoNoite"])
    d["ativo"] = bool(d["ativo"])
    if fotos is not None:
        d["fotos"] = [_foto_para_json(f) for f in fotos]
    return d


def detalhe(db, usuario, acomodacao_id):
    a = obter_do_dono(db, acomodacao_id, usuario)
    fotos = db.execute(
        "SELECT * FROM foto WHERE acomodacao_id = ? ORDER BY ordem", (acomodacao_id,)
    ).fetchall()
    return acomodacao_para_json(a, fotos)


def reservas_da_acomodacao(db, usuario, acomodacao_id):
    obter_do_dono(db, acomodacao_id, usuario)
    linhas = db.execute(
        "SELECT r.id, r.checkIn, r.checkOut, r.numHospedes, r.valorTotal, r.status,"
        " u.nome AS hospede FROM reserva r JOIN usuario u ON u.id = r.hospede_id"
        " WHERE r.acomodacao_id = ? ORDER BY r.checkIn DESC",
        (acomodacao_id,),
    ).fetchall()
    return [_reserva_para_json(r) for r in linhas]


def listar_do_anfitriao(db, usuario):
    """RF-11: todas as acomodações do anfitrião (ativas e desativadas) com as
    reservas recebidas em cada uma, em todos os status (decisão A15)."""
    exigir_anfitriao(usuario)
    acomodacoes = db.execute(
        "SELECT * FROM acomodacao WHERE anfitriao_id = ? ORDER BY ativo DESC, id",
        (usuario["id"],),
    ).fetchall()
    resultado = []
    for a in acomodacoes:
        item = acomodacao_para_json(a)
        capa = db.execute(
            "SELECT chave FROM foto WHERE acomodacao_id = ? ORDER BY ordem LIMIT 1", (a["id"],)
        ).fetchone()
        item["capa"] = f"/arquivos/{capa['chave']}" if capa else None
        item["totalFotos"] = _contar_fotos(db, a["id"])
        item["reservas"] = reservas_da_acomodacao(db, usuario, a["id"])
        resultado.append(item)
    return resultado


def anuncios_publicos(db):
    """Vitrine mínima, só para demonstrar o efeito de publicar/desativar
    (pós-condição do UC05: "visível nas buscas"). A busca completa é RF-12,
    fora desta tarefa. Mostra só bairro e cidade, nunca rua e número (RNF-05)."""
    linhas = db.execute(
        "SELECT a.id, a.titulo, a.bairro, a.cidade, a.estado, a.precoNoite, a.capacidadeMaxima,"
        " (SELECT chave FROM foto f WHERE f.acomodacao_id = a.id ORDER BY ordem LIMIT 1) AS capa"
        " FROM acomodacao a WHERE a.ativo = 1 ORDER BY a.id"
    ).fetchall()
    return [
        {"id": r["id"], "titulo": r["titulo"], "bairro": r["bairro"], "cidade": r["cidade"],
         "estado": r["estado"], "precoNoite": centavos_para_texto(r["precoNoite"]),
         "capacidadeMaxima": r["capacidadeMaxima"],
         "capa": f"/arquivos/{r['capa']}" if r["capa"] else None}
        for r in linhas
    ]
