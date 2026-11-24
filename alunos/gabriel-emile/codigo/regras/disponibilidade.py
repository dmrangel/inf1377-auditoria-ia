"""Regras de disponibilidade e de visibilidade de anúncios.

Reunidas aqui porque são usadas tanto pela busca (UC08) quanto pela página do
anúncio e pelo calendário (UC09). Cada função devolve um trecho SQL e os
parâmetros, para que a busca resolva tudo em uma única consulta (RNF-01).
"""
from datetime import date, timedelta

import relogio

# Uma reserva PENDENTE só segura as datas por 30 minutos: depois disso ela é
# cancelada automaticamente (RN-04). O cancelamento automático em si pertence
# ao módulo de reservas/pagamentos; aqui apenas deixamos de considerar como
# ocupadas as datas de uma PENDENTE vencida, para a busca não esconder uma
# acomodação que na prática já está livre (AMBIGUIDADES.md, A05).
PRAZO_PENDENTE_MINUTOS = 30

# Motivo de denúncia que indica risco à segurança do hóspede (RNF-06).
# A ERS não define a lista de motivos (AMBIGUIDADES.md, A06).
MOTIVO_RISCO_SEGURANCA = "RISCO_SEGURANCA"

# RF-08: o anúncio publicado precisa ter de 5 a 30 fotos.
MINIMO_FOTOS = 5


def limite_pendente():
    """Instante a partir do qual uma PENDENTE ainda está dentro do prazo."""
    return (relogio.agora() - timedelta(minutes=PRAZO_PENDENTE_MINUTOS)).isoformat(timespec="seconds")


def sql_reserva_ocupa(alias_reserva="r"):
    """Condição SQL: a reserva `alias_reserva` ocupa as datas dela.

    A data de criação da reserva PENDENTE vem do histórico de status
    (B.4 não tem coluna dataCriacao em reserva). Se não houver registro no
    histórico, a PENDENTE é tratada como válida (decisão conservadora).
    """
    r = alias_reserva
    return f"""(
        {r}.status IN ('CONFIRMADA', 'CONCLUIDA')
        OR ({r}.status = 'PENDENTE' AND COALESCE((
                SELECT MIN(h.dataHora) FROM historico_status_reserva h
                 WHERE h.reserva_id = {r}.id AND h.statusNovo = 'PENDENTE'
            ), :limite_pendente) >= :limite_pendente)
    )"""


def sql_livre_no_periodo(alias_acomodacao="a"):
    """Condição SQL: a acomodação está livre em [:checkin, :checkout).

    Status que ocupam: CONFIRMADA, CONCLUIDA (só existe no passado, mas entra
    por segurança caso o job de conclusão atrase) e PENDENTE dentro do prazo.
    CANCELADA libera as datas.

    Intervalos semiabertos: quem sai no dia 10 libera o dia 10 para quem
    entra no dia 10 (AMBIGUIDADES.md, A04). Bloqueios do anfitrião (RF-10)
    também ocupam o período.
    """
    a = alias_acomodacao
    return f"""(
        NOT EXISTS (
            SELECT 1 FROM reserva r
             WHERE r.acomodacao_id = {a}.id
               AND r.checkIn < :checkout AND r.checkOut > :checkin
               AND {sql_reserva_ocupa('r')}
        )
        AND NOT EXISTS (
            SELECT 1 FROM bloqueio_data b
             WHERE b.acomodacao_id = {a}.id
               AND b.dataInicio < :checkout AND b.dataFim > :checkin
        )
    )"""


def sql_publicado(alias_acomodacao="a"):
    """Condição SQL: o anúncio pode aparecer para o público.

    - ativo = 1 (RF-09: anfitrião pode desativar);
    - sem denúncia de risco à segurança EM_ANALISE (RNF-06);
    - com pelo menos 5 fotos (RF-08 / UC05-5a: sem isso não há publicação).
    """
    a = alias_acomodacao
    return f"""(
        {a}.ativo = 1
        AND NOT EXISTS (
            SELECT 1 FROM denuncia d
             WHERE d.acomodacao_id = {a}.id
               AND d.status = 'EM_ANALISE'
               AND d.motivo = '{MOTIVO_RISCO_SEGURANCA}'
        )
        AND (SELECT COUNT(*) FROM foto_acomodacao f WHERE f.acomodacao_id = {a}.id) >= {MINIMO_FOTOS}
    )"""


def acomodacao_publicada(con, acomodacao_id):
    linha = con.execute(
        f"SELECT 1 FROM acomodacao a WHERE a.id = ? AND {sql_publicado('a')}",
        (acomodacao_id,),
    ).fetchone()
    return linha is not None


def livre_no_periodo(con, acomodacao_id, checkin, checkout):
    params = {
        "id": acomodacao_id,
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "limite_pendente": limite_pendente(),
    }
    linha = con.execute(
        f"SELECT 1 FROM acomodacao a WHERE a.id = :id AND {sql_livre_no_periodo('a')}",
        params,
    ).fetchone()
    return linha is not None


def noites_ocupadas(con, acomodacao_id, inicio, fim):
    """Conjunto de datas (noites) ocupadas em [inicio, fim).

    Usada pelo calendário. Não diz se a ocupação é reserva ou bloqueio, nem de
    quem é, para não expor dados de outros hóspedes.
    """
    params = {
        "id": acomodacao_id,
        "checkin": inicio.isoformat(),
        "checkout": fim.isoformat(),
        "limite_pendente": limite_pendente(),
    }
    intervalos = con.execute(
        f"""
        SELECT r.checkIn AS ini, r.checkOut AS fim FROM reserva r
         WHERE r.acomodacao_id = :id
           AND r.checkIn < :checkout AND r.checkOut > :checkin
           AND {sql_reserva_ocupa('r')}
        UNION ALL
        SELECT b.dataInicio, b.dataFim FROM bloqueio_data b
         WHERE b.acomodacao_id = :id
           AND b.dataInicio < :checkout AND b.dataFim > :checkin
        """,
        params,
    ).fetchall()
    ocupadas = set()
    for linha in intervalos:
        dia = max(date.fromisoformat(linha["ini"]), inicio)
        ate = min(date.fromisoformat(linha["fim"]), fim)
        while dia < ate:
            ocupadas.add(dia)
            dia += timedelta(days=1)
    return ocupadas
