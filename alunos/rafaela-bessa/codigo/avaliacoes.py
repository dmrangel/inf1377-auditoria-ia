"""
avaliacoes.py - Regras de negócio da Avaliação de Estadia
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
Conforme ERS v1.2: seção 4.6 (RF-29 a RF-32), RN-06, UC18 (Avaliar estadia),
UC19 (Avaliar hóspede), seção 4.4.2 passo 3 (CONFIRMADA -> CONCLUIDA) e RNF-22.

Decisões tomadas onde a ERS é ambígua (detalhadas no README, seção "Ambiguidades"):
- A reserva passa para CONCLUIDA quando a data de hoje é POSTERIOR ao check-out,
  verificada sob demanda (mesmo padrão de models.expirar_reservas_pendentes).
- Quem é avaliado não é gravado: é deduzido do autor. Se o autor é o hóspede da
  reserva, a avaliação é da acomodação (UC18); se é o anfitrião, é do hóspede (UC19).
- Uma avaliação só é publicada quando as duas partes avaliaram ou quando o prazo
  da RN-06 terminou (seção 4.6.2, passo 3). Isso é calculado, não gravado.
- A nota média só considera avaliações publicadas e é calculada na consulta,
  por isso está sempre "recalculada" (RF-32) sem precisar de coluna nova.
"""

import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from database import get_db_connection
from services.email_service import EmailService

PRAZO_AVALIACAO_DIAS = 14      # RN-06
NOTA_MINIMA = 1                # RF-29
NOTA_MAXIMA = 5                # RF-29
COMENTARIO_MAX_CARACTERES = 1000   # não definido na ERS (ambiguidade AV-08)

# Endereço usado nos links dos e-mails de convite (o e-mail não tem contexto de requisição).
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

PAPEL_HOSPEDE = "HOSPEDE"
PAPEL_ANFITRIAO = "ANFITRIAO"
PAPEL_CONFLITO = "CONFLITO"    # o mesmo usuário é hóspede e anfitrião da reserva


class ErroAvaliacao(Exception):
    """Erro de regra de negócio com a mensagem em linguagem simples e o código HTTP."""

    def __init__(self, mensagem: str, http_status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.http_status = http_status


def hoje() -> date:
    """Data atual. Fica isolada numa função para os testes poderem simular a passagem do tempo."""
    return date.today()


def prazo_final(check_out_str: str) -> date:
    """
    Último dia (inclusive) para avaliar: check-out + 14 dias (RN-06).
    O check-out não tem hora na ERS, então a contagem é feita em dias de calendário.
    """
    check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    return check_out + timedelta(days=PRAZO_AVALIACAO_DIAS)


# Condição SQL de "avaliação publicada" para a reserva de alias r (seção 4.6.2, passo 3):
# as duas partes avaliaram OU o prazo da RN-06 terminou (hoje > check-out + 14 dias).
_SQL_PUBLICADA = (
    "((SELECT COUNT(*) FROM avaliacao x WHERE x.reserva_id = r.id) >= 2 "
    f"OR date(r.checkOut, '+{PRAZO_AVALIACAO_DIAS} days') < :hoje)"
)


def _abrir(conn):
    """Reaproveita a conexão recebida ou abre uma nova (mesmo padrão de models.py)."""
    if conn is None:
        return get_db_connection(), True
    return conn, False


# ---------------------------------------------------------------------------
# Seção 4.4.2 passo 3 e 4.6.2 passo 1: conclusão da reserva e convite
# ---------------------------------------------------------------------------

def concluir_reservas_encerradas(conn=None) -> List[int]:
    """
    Muda para CONCLUIDA as reservas CONFIRMADAS cujo check-out já passou e
    convida hóspede e anfitrião a avaliar (seção 4.6.2, passo 1).

    Só parte de CONFIRMADA: reservas PENDENTES ou CANCELADAS nunca viram estadia.
    A mudança é automática, por isso o histórico grava responsável nulo (RNF-22).
    Retorna os ids das reservas concluídas nesta chamada.
    """
    conn, fechar = _abrir(conn)
    try:
        cursor = conn.cursor()
        dia = hoje()
        cursor.execute("""
            SELECT r.id, r.hospede_id, r.checkOut, a.anfitriao_id, a.titulo,
                   h.nome AS hospede_nome, h.email AS hospede_email,
                   anf.nome AS anfitriao_nome, anf.email AS anfitriao_email
            FROM reserva r
            JOIN acomodacao a ON a.id = r.acomodacao_id
            JOIN usuario h ON h.id = r.hospede_id
            JOIN usuario anf ON anf.id = a.anfitriao_id
            WHERE r.status = 'CONFIRMADA' AND r.checkOut < ?;
        """, (dia.isoformat(),))
        candidatas = cursor.fetchall()

        agora = datetime.now().isoformat()
        concluidas = []
        for r in candidatas:
            # O WHERE com status protege contra duas requisições concluindo a mesma
            # reserva ao mesmo tempo (o convite seria enviado duas vezes).
            cursor.execute(
                "UPDATE reserva SET status = 'CONCLUIDA' WHERE id = ? AND status = 'CONFIRMADA';",
                (r["id"],)
            )
            if cursor.rowcount != 1:
                continue
            cursor.execute("""
                INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora, responsavel_id)
                VALUES (?, 'CONFIRMADA', 'CONCLUIDA', ?, NULL);
            """, (r["id"], agora))
            concluidas.append(r)

        if concluidas:
            conn.commit()

        # Os convites saem depois do commit: se a gravação falhar, ninguém é convidado.
        for r in concluidas:
            limite = prazo_final(r["checkOut"])
            # Sem convite se o prazo já terminou (sistema ficou sem acesso por mais de 14 dias)
            # ou se o hóspede é o próprio anfitrião (ninguém pode avaliar; ambiguidade AV-07).
            if dia > limite or r["hospede_id"] == r["anfitriao_id"]:
                continue
            link = f"{BASE_URL}/reservas/{r['id']}/avaliar"
            EmailService.send_review_invitation(
                r["hospede_email"], r["hospede_nome"], PAPEL_HOSPEDE, r["id"],
                r["titulo"], r["anfitriao_nome"], limite.isoformat(), link
            )
            EmailService.send_review_invitation(
                r["anfitriao_email"], r["anfitriao_nome"], PAPEL_ANFITRIAO, r["id"],
                r["titulo"], r["hospede_nome"], limite.isoformat(), link
            )

        return [r["id"] for r in concluidas]
    finally:
        if fechar:
            conn.close()


# ---------------------------------------------------------------------------
# Consulta da reserva e papel do usuário
# ---------------------------------------------------------------------------

def _carregar_reserva(conn, reserva_id: int) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.hospede_id, r.acomodacao_id, r.checkIn, r.checkOut, r.numHospedes, r.status,
               a.anfitriao_id, a.titulo AS acomodacao_titulo, a.bairro AS acomodacao_bairro,
               a.cidade AS acomodacao_cidade, a.estado AS acomodacao_estado,
               h.nome AS hospede_nome, anf.nome AS anfitriao_nome
        FROM reserva r
        JOIN acomodacao a ON a.id = r.acomodacao_id
        JOIN usuario h ON h.id = r.hospede_id
        JOIN usuario anf ON anf.id = a.anfitriao_id
        WHERE r.id = ?;
    """, (reserva_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def papel_do_usuario(reserva: Dict[str, Any], usuario_id: Optional[int]) -> Optional[str]:
    """
    Papel do usuário nesta reserva. Um mesmo usuário pode ser hóspede e anfitrião
    (seção 2.3); se ele reservou a própria acomodação, o papel é CONFLITO.
    """
    eh_hospede = usuario_id is not None and reserva["hospede_id"] == usuario_id
    eh_anfitriao = usuario_id is not None and reserva["anfitriao_id"] == usuario_id
    if eh_hospede and eh_anfitriao:
        return PAPEL_CONFLITO
    if eh_hospede:
        return PAPEL_HOSPEDE
    if eh_anfitriao:
        return PAPEL_ANFITRIAO
    return None


def _avaliacoes_da_reserva(conn, reserva_id: int) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT av.id, av.reserva_id, av.autor_id, av.nota, av.comentario, av.dataAvaliacao,
               u.nome AS autor_nome
        FROM avaliacao av JOIN usuario u ON u.id = av.autor_id
        WHERE av.reserva_id = ? ORDER BY av.id;
    """, (reserva_id,))
    return [dict(r) for r in cursor.fetchall()]


def _bloqueio(reserva: Dict[str, Any], papel: str, minha: Optional[Dict[str, Any]]) -> Optional[ErroAvaliacao]:
    """
    Verifica se o participante pode avaliar agora. A ordem das verificações
    define qual mensagem o usuário vê quando mais de uma regra falha.
    """
    if papel == PAPEL_CONFLITO:
        return ErroAvaliacao(
            "Você é o anfitrião desta acomodação e também o hóspede desta reserva, "
            "por isso não pode avaliá-la."
        )
    if reserva["status"] == "CANCELADA":
        return ErroAvaliacao("Reservas canceladas não podem ser avaliadas (RF-30).")
    if reserva["status"] != "CONCLUIDA":
        return ErroAvaliacao(
            "Esta estadia ainda não terminou. A avaliação fica disponível depois do check-out (RF-30)."
        )
    if minha is not None:
        return ErroAvaliacao("Você já avaliou esta estadia. Cada participante avalia uma única vez (RF-31).", 409)
    if hoje() > prazo_final(reserva["checkOut"]):
        return ErroAvaliacao(
            f"O prazo para avaliar terminou em {_data_br(prazo_final(reserva['checkOut']))}. "
            f"As avaliações podem ser feitas até 14 dias após o check-out (RN-06)."
        )
    return None


def _data_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def situacao_para_usuario(reserva_id: int, usuario_id: Optional[int]) -> Dict[str, Any]:
    """
    Tudo o que a tela "Avaliar" precisa saber sobre a reserva para este usuário.
    Lança ErroAvaliacao 404 (reserva não existe) ou 403 (não participa da reserva).
    """
    conn = get_db_connection()
    try:
        concluir_reservas_encerradas(conn)
        reserva = _carregar_reserva(conn, reserva_id)
        if reserva is None:
            raise ErroAvaliacao("Reserva não encontrada.", 404)
        papel = papel_do_usuario(reserva, usuario_id)
        if papel is None:
            # RNF-11 por analogia: só os participantes da reserva veem e avaliam.
            raise ErroAvaliacao("Você não participa desta reserva e não pode avaliá-la.", 403)

        avaliacoes = _avaliacoes_da_reserva(conn, reserva_id)
        minha = next((a for a in avaliacoes if a["autor_id"] == usuario_id), None)
        outra = next((a for a in avaliacoes if a["autor_id"] != usuario_id), None)
        limite = prazo_final(reserva["checkOut"])
        publicada = len(avaliacoes) >= 2 or hoje() > limite
        bloqueio = _bloqueio(reserva, papel, minha)

        situacao = {
            "reserva": reserva,
            "papel": papel,
            "prazo_final": limite.isoformat(),
            "prazo_final_br": _data_br(limite),
            "dias_restantes": (limite - hoje()).days,
            "pode_avaliar": bloqueio is None,
            "bloqueio": bloqueio.mensagem if bloqueio else None,
            "minha_avaliacao": minha,
            "publicada": publicada,
            # A avaliação da outra parte só aparece depois de publicada (seção 4.6.2, passo 3).
            "outra_avaliacao": outra if publicada else None,
            "outra_parte_ja_avaliou": outra is not None,
            "nota_hospede": None,
        }
        if papel == PAPEL_ANFITRIAO:
            # UC19: o anfitrião vê a nota média que o hóspede já recebeu de outros anfitriões.
            situacao["nota_hospede"] = resumo_notas_hospede(reserva["hospede_id"], conn)
        return situacao
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# RF-29 a RF-32: registro da avaliação
# ---------------------------------------------------------------------------

def _validar_nota(valor: Any) -> int:
    """RF-29: nota inteira de 1 a 5. Aceita número inteiro ou texto com dígitos (formulário)."""
    mensagem = f"Escolha uma nota de {NOTA_MINIMA} a {NOTA_MAXIMA} estrelas (RF-29)."
    if isinstance(valor, bool):          # True/False são int em Python; não são nota.
        raise ErroAvaliacao(mensagem)
    if isinstance(valor, int):
        nota = valor
    elif isinstance(valor, str) and valor.strip().isdigit():
        nota = int(valor.strip())
    else:
        raise ErroAvaliacao(mensagem)
    if not NOTA_MINIMA <= nota <= NOTA_MAXIMA:
        raise ErroAvaliacao(mensagem)
    return nota


def _validar_comentario(valor: Any) -> Optional[str]:
    """RF-29: comentário opcional. Texto vazio vira NULL."""
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ErroAvaliacao("O comentário deve ser um texto.")
    texto = valor.strip()
    if len(texto) > COMENTARIO_MAX_CARACTERES:
        raise ErroAvaliacao(
            f"O comentário pode ter no máximo {COMENTARIO_MAX_CARACTERES} caracteres "
            f"(o seu tem {len(texto)})."
        )
    return texto or None


def registrar_avaliacao(reserva_id: int, usuario_id: Optional[int], nota: Any, comentario: Any = None) -> Dict[str, Any]:
    """
    UC18/UC19, passos 2 a 4: valida, grava a avaliação com dataAvaliacao e devolve
    a nota média atualizada da acomodação. Lança ErroAvaliacao em qualquer violação.
    """
    if not usuario_id:
        raise ErroAvaliacao("Você precisa estar conectado para avaliar.", 401)

    conn = get_db_connection()
    try:
        concluir_reservas_encerradas(conn)
        reserva = _carregar_reserva(conn, reserva_id)
        if reserva is None:
            raise ErroAvaliacao("Reserva não encontrada.", 404)
        papel = papel_do_usuario(reserva, usuario_id)
        if papel is None:
            raise ErroAvaliacao("Você não participa desta reserva e não pode avaliá-la.", 403)

        avaliacoes = _avaliacoes_da_reserva(conn, reserva_id)
        minha = next((a for a in avaliacoes if a["autor_id"] == usuario_id), None)
        bloqueio = _bloqueio(reserva, papel, minha)
        if bloqueio:
            raise bloqueio

        nota_ok = _validar_nota(nota)
        comentario_ok = _validar_comentario(comentario)
        data_avaliacao = datetime.now().isoformat(timespec="seconds")

        try:
            conn.execute("""
                INSERT INTO avaliacao (reserva_id, autor_id, nota, comentario, dataAvaliacao)
                VALUES (?, ?, ?, ?, ?);
            """, (reserva_id, usuario_id, nota_ok, comentario_ok, data_avaliacao))
            conn.commit()
        except sqlite3.IntegrityError:
            # RF-31 garantido também pelo UNIQUE(reserva_id, autor_id), caso duas
            # requisições do mesmo usuário cheguem ao mesmo tempo.
            conn.rollback()
            raise ErroAvaliacao("Você já avaliou esta estadia. Cada participante avalia uma única vez (RF-31).", 409)

        total = len(avaliacoes) + 1
        publicada = total >= 2
        # RF-32: a média é recalculada aqui; ela só muda se esta avaliação foi publicada.
        media = resumo_notas_acomodacao(reserva["acomodacao_id"], conn)

        return {
            "reserva_id": reserva_id,
            "papel": papel,
            "nota": nota_ok,
            "comentario": comentario_ok,
            "dataAvaliacao": data_avaliacao,
            "publicada": publicada,
            "nota_media_acomodacao": media,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# RF-15 e RF-32: notas médias e avaliações publicadas
# ---------------------------------------------------------------------------

def resumo_notas_acomodacao(acomodacao_id: int, conn=None) -> Dict[str, Any]:
    """
    Nota média e quantidade de avaliações publicadas da acomodação.
    Só entram avaliações escritas pelo hóspede da reserva (UC18).
    media = None quando não há avaliações (a tela mostra "Sem avaliações", não 0).
    """
    conn, fechar = _abrir(conn)
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT AVG(av.nota) AS media, COUNT(*) AS total
            FROM avaliacao av
            JOIN reserva r ON r.id = av.reserva_id
            WHERE r.acomodacao_id = :acomodacao_id
              AND av.autor_id = r.hospede_id
              AND {_SQL_PUBLICADA};
        """, {"acomodacao_id": acomodacao_id, "hoje": hoje().isoformat()})
        row = cursor.fetchone()
        media = round(row["media"], 2) if row["media"] is not None else None
        return {"media": media, "total": row["total"]}
    finally:
        if fechar:
            conn.close()


def resumo_notas_hospede(hospede_id: int, conn=None) -> Dict[str, Any]:
    """Nota média publicada que o hóspede recebeu dos anfitriões (UC19)."""
    conn, fechar = _abrir(conn)
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT AVG(av.nota) AS media, COUNT(*) AS total
            FROM avaliacao av
            JOIN reserva r ON r.id = av.reserva_id
            JOIN acomodacao a ON a.id = r.acomodacao_id
            WHERE r.hospede_id = :hospede_id
              AND av.autor_id = a.anfitriao_id
              AND {_SQL_PUBLICADA};
        """, {"hospede_id": hospede_id, "hoje": hoje().isoformat()})
        row = cursor.fetchone()
        media = round(row["media"], 2) if row["media"] is not None else None
        return {"media": media, "total": row["total"]}
    finally:
        if fechar:
            conn.close()


def avaliacoes_publicadas_acomodacao(acomodacao_id: int) -> Dict[str, Any]:
    """Dados da página de avaliações da acomodação (RF-15): média e comentários publicados."""
    conn = get_db_connection()
    try:
        concluir_reservas_encerradas(conn)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.titulo, a.bairro, a.cidade, a.estado, u.nome AS anfitriao_nome, u.superhost
            FROM acomodacao a JOIN usuario u ON u.id = a.anfitriao_id
            WHERE a.id = ?;
        """, (acomodacao_id,))
        acomodacao = cursor.fetchone()
        if acomodacao is None:
            raise ErroAvaliacao("Acomodação não encontrada.", 404)

        cursor.execute(f"""
            SELECT av.nota, av.comentario, av.dataAvaliacao, u.nome AS autor_nome
            FROM avaliacao av
            JOIN reserva r ON r.id = av.reserva_id
            JOIN usuario u ON u.id = av.autor_id
            WHERE r.acomodacao_id = :acomodacao_id
              AND av.autor_id = r.hospede_id
              AND {_SQL_PUBLICADA}
            ORDER BY av.dataAvaliacao DESC, av.id DESC;
        """, {"acomodacao_id": acomodacao_id, "hoje": hoje().isoformat()})
        return {
            "acomodacao": dict(acomodacao),
            "resumo": resumo_notas_acomodacao(acomodacao_id, conn),
            "avaliacoes": [dict(r) for r in cursor.fetchall()],
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Painel "Avaliações" do usuário
# ---------------------------------------------------------------------------

_SQL_PENDENTES = """
    FROM reserva r
    JOIN acomodacao a ON a.id = r.acomodacao_id
    JOIN usuario h ON h.id = r.hospede_id
    JOIN usuario anf ON anf.id = a.anfitriao_id
    WHERE r.status = 'CONCLUIDA'
      AND (r.hospede_id = :u OR a.anfitriao_id = :u)
      AND NOT (r.hospede_id = :u AND a.anfitriao_id = :u)
      AND date(r.checkOut, '+14 days') >= :hoje
      AND NOT EXISTS (SELECT 1 FROM avaliacao x WHERE x.reserva_id = r.id AND x.autor_id = :u)
"""


def contar_pendentes(usuario_id: Optional[int]) -> int:
    """Quantas estadias o usuário ainda pode avaliar (aviso no cabeçalho = convite na interface)."""
    if not usuario_id:
        return 0
    conn = get_db_connection()
    try:
        concluir_reservas_encerradas(conn)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) AS n {_SQL_PENDENTES};", {"u": usuario_id, "hoje": hoje().isoformat()})
        return cursor.fetchone()["n"]
    finally:
        conn.close()


def painel_do_usuario(usuario_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """Pendentes (posso avaliar), enviadas (o que eu escrevi) e recebidas (publicadas sobre mim)."""
    conn = get_db_connection()
    try:
        concluir_reservas_encerradas(conn)
        cursor = conn.cursor()
        params = {"u": usuario_id, "hoje": hoje().isoformat()}

        cursor.execute(f"""
            SELECT r.id, r.checkIn, r.checkOut, a.titulo AS acomodacao_titulo,
                   h.nome AS hospede_nome, anf.nome AS anfitriao_nome,
                   CASE WHEN r.hospede_id = :u THEN 'HOSPEDE' ELSE 'ANFITRIAO' END AS papel
            {_SQL_PENDENTES}
            ORDER BY r.checkOut ASC;
        """, params)
        pendentes = []
        for r in cursor.fetchall():
            item = dict(r)
            limite = prazo_final(item["checkOut"])
            item["prazo_final_br"] = _data_br(limite)
            item["dias_restantes"] = (limite - hoje()).days
            pendentes.append(item)

        cursor.execute(f"""
            SELECT av.nota, av.comentario, av.dataAvaliacao, r.id AS reserva_id,
                   a.titulo AS acomodacao_titulo, h.nome AS hospede_nome,
                   CASE WHEN r.hospede_id = :u THEN 'HOSPEDE' ELSE 'ANFITRIAO' END AS papel,
                   {_SQL_PUBLICADA} AS publicada
            FROM avaliacao av
            JOIN reserva r ON r.id = av.reserva_id
            JOIN acomodacao a ON a.id = r.acomodacao_id
            JOIN usuario h ON h.id = r.hospede_id
            WHERE av.autor_id = :u
            ORDER BY av.dataAvaliacao DESC;
        """, params)
        enviadas = [dict(r) for r in cursor.fetchall()]

        # Recebidas: escritas pela outra parte de uma reserva minha, e já publicadas.
        cursor.execute(f"""
            SELECT av.nota, av.comentario, av.dataAvaliacao, r.id AS reserva_id,
                   a.titulo AS acomodacao_titulo, u.nome AS autor_nome,
                   CASE WHEN r.hospede_id = :u THEN 'HOSPEDE' ELSE 'ANFITRIAO' END AS papel
            FROM avaliacao av
            JOIN reserva r ON r.id = av.reserva_id
            JOIN acomodacao a ON a.id = r.acomodacao_id
            JOIN usuario u ON u.id = av.autor_id
            WHERE av.autor_id != :u
              AND (r.hospede_id = :u OR a.anfitriao_id = :u)
              AND {_SQL_PUBLICADA}
            ORDER BY av.dataAvaliacao DESC;
        """, params)
        recebidas = [dict(r) for r in cursor.fetchall()]

        return {"pendentes": pendentes, "enviadas": enviadas, "recebidas": recebidas}
    finally:
        conn.close()
