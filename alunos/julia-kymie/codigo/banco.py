"""Conexão com o SQLite, criação automática do banco e dados de exemplo."""

import os
import sqlite3
from datetime import datetime, timedelta

from flask import current_app, g
from werkzeug.security import generate_password_hash

from imagens import png_numerado

ESQUEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def conectar(caminho):
    conexao = sqlite3.connect(caminho, detect_types=0)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def obter_db():
    """Uma conexão por requisição."""
    if "db" not in g:
        g.db = conectar(current_app.config["DATABASE"])
    return g.db


def fechar_db(_erro=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def inicializar(app):
    """Cria o banco na primeira execução e, se ele estava vazio, grava os dados
    de exemplo."""
    caminho = app.config["DATABASE"]
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    conexao = conectar(caminho)
    try:
        with open(ESQUEMA, encoding="utf-8") as f:
            conexao.executescript(f.read())
        vazio = conexao.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 0
        if vazio and app.config.get("SEMEAR", True):
            semear(conexao, app.extensions["armazenamento"], app.config["HOJE"]())
        conexao.commit()
    finally:
        conexao.close()


# --------------------------------------------------------------------------
# Dados de exemplo. As datas são relativas a "hoje" para os cenários
# (reserva futura, passada etc.) continuarem válidos em qualquer dia.
# --------------------------------------------------------------------------

USUARIOS = [
    # nome, email, telefone, ehAnfitriao, superhost, taxaResposta
    ("Ana Souza", "ana@exemplo.com", "(21) 99999-0001", 1, 1, 0.98),
    ("Bruno Lima", "bruno@exemplo.com", "(11) 99999-0002", 1, 0, 0.80),
    ("Carla Dias", "carla@exemplo.com", "(21) 99999-0003", 0, 0, None),
    ("Diego Rocha", "diego@exemplo.com", "(31) 99999-0004", 0, 0, None),
]

ACOMODACOES = [
    # chave, dono(índice), dados, ativo, nº fotos
    ("copa", 0, dict(
        titulo="Apartamento com vista para o mar em Copacabana",
        descricao="Apartamento de 2 quartos de frente para a praia, com varanda, ar-condicionado e Wi-Fi.",
        precoNoite=45000, capacidadeMaxima=4, quartos=2, banheiros=1, camas=3,
        regras="Proibido fumar. Sem festas. Silêncio após as 22h.",
        cep="22071-001", rua="Avenida Atlântica", numero="1702", bairro="Copacabana",
        cidade="Rio de Janeiro", estado="RJ"), 1, 6),
    ("gavea", 0, dict(
        titulo="Estúdio próximo à PUC na Gávea",
        descricao="Estúdio compacto e silencioso, a cinco minutos a pé da PUC-Rio.",
        precoNoite=18000, capacidadeMaxima=2, quartos=0, banheiros=1, camas=1,
        regras="Sem animais de estimação.",
        cep="22451-900", rua="Rua Marquês de São Vicente", numero="225", bairro="Gávea",
        cidade="Rio de Janeiro", estado="RJ"), 1, 5),
    ("ouro", 0, dict(
        titulo="Casa de campo em Ouro Preto",
        descricao="Casa colonial com lareira e quintal, perto do centro histórico.",
        precoNoite=32000, capacidadeMaxima=6, quartos=3, banheiros=2, camas=4,
        regras="Check-in após as 14h.",
        cep="35400-000", rua="Rua Direita", numero="50", bairro="Centro",
        cidade="Ouro Preto", estado="MG"), 0, 7),
    ("paulista", 1, dict(
        titulo="Loft no centro de São Paulo",
        descricao="Loft moderno perto da Avenida Paulista, com cozinha completa.",
        precoNoite=25000, capacidadeMaxima=2, quartos=1, banheiros=1, camas=1,
        regras="Proibido fumar.",
        cep="01310-100", rua="Avenida Paulista", numero="1000", bairro="Bela Vista",
        cidade="São Paulo", estado="SP"), 1, 5),
]

RESERVAS = [
    # acomodação, hóspede(índice), início(dias a partir de hoje), noites, nº hóspedes, status
    ("copa", 3, 10, 4, 4, "CONFIRMADA"),
    ("copa", 2, 20, 3, 2, "PENDENTE"),
    ("copa", 2, -40, 5, 2, "CONCLUIDA"),
    ("copa", 3, 30, 2, 1, "CANCELADA"),
    ("ouro", 3, -90, 3, 5, "CONCLUIDA"),
    ("ouro", 2, 15, 2, 3, "CONFIRMADA"),
    ("paulista", 2, 5, 3, 2, "CONFIRMADA"),
]

# Noites bloqueadas de exemplo (acomodação, início, fim em dias a partir de hoje)
BLOQUEIOS = [("gavea", 5, 7)]

TAXA_SERVICO = 0.14          # RN-03
DESCONTO_SUPERHOST = 0.10    # RN-07 (sobre a taxa)


def semear(conexao, armazenamento, hoje):
    agora = datetime.now().isoformat(timespec="seconds")
    ids_usuarios = []
    for nome, email, tel, anf, sh, taxa in USUARIOS:
        cur = conexao.execute(
            "INSERT INTO usuario (nome, email, senhaHash, telefone, dataCadastro, ehAnfitriao,"
            " superhost, taxaResposta) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            # RNF-07: senha com hash e salt. Login não faz parte desta tarefa.
            (nome, email, generate_password_hash("senha123"), tel, agora, anf, sh, taxa),
        )
        ids_usuarios.append(cur.lastrowid)

    ids_acom, precos, donos = {}, {}, {}
    n_foto = 0
    for chave, dono, d, ativo, n_fotos in ACOMODACOES:
        cur = conexao.execute(
            "INSERT INTO acomodacao (anfitriao_id, titulo, descricao, precoNoite, capacidadeMaxima,"
            " quartos, banheiros, camas, regras, cep, rua, numero, bairro, cidade, estado, ativo)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ids_usuarios[dono], d["titulo"], d["descricao"], d["precoNoite"], d["capacidadeMaxima"],
             d["quartos"], d["banheiros"], d["camas"], d["regras"], d["cep"], d["rua"], d["numero"],
             d["bairro"], d["cidade"], d["estado"], ativo),
        )
        ids_acom[chave], precos[chave], donos[chave] = cur.lastrowid, d["precoNoite"], dono
        for ordem in range(1, n_fotos + 1):
            conteudo = png_numerado(n_foto)
            n_foto += 1
            chave_arq = armazenamento.salvar(conteudo, "image/png", f"exemplo{n_foto}.png")
            conexao.execute(
                "INSERT INTO foto (acomodacao_id, chave, tipoConteudo, tamanhoBytes, ordem, dataEnvio)"
                " VALUES (?, ?, 'image/png', ?, ?, ?)",
                (cur.lastrowid, chave_arq, len(conteudo), ordem, agora),
            )

    for chave, hosp, inicio, noites, n_hosp, status in RESERVAS:
        check_in = hoje + timedelta(days=inicio)
        diarias = precos[chave] * noites
        taxa = TAXA_SERVICO * (1 - DESCONTO_SUPERHOST if USUARIOS[donos[chave]][4] else 1)
        cur = conexao.execute(
            "INSERT INTO reserva (hospede_id, acomodacao_id, checkIn, checkOut, numHospedes,"
            " valorTotal, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ids_usuarios[hosp], ids_acom[chave], check_in.isoformat(),
             (check_in + timedelta(days=noites)).isoformat(), n_hosp,
             round(diarias * (1 + taxa)), status),
        )
        conexao.execute(
            "INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora,"
            " responsavel_id) VALUES (?, NULL, ?, ?, NULL)",
            (cur.lastrowid, status, agora),
        )

    for chave, ini, fim in BLOQUEIOS:
        for dia in range(ini, fim + 1):
            conexao.execute(
                "INSERT INTO bloqueio_data (acomodacao_id, data) VALUES (?, ?)",
                (ids_acom[chave], (hoje + timedelta(days=dia)).isoformat()),
            )
