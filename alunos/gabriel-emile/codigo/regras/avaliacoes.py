"""Avaliações exibidas na busca e no anúncio (RF-15, UC20 estendendo UC09).

Duas regras não óbvias:

1. Só contam as avaliações SOBRE A ACOMODAÇÃO, isto é, as escritas pelo
   hóspede da reserva. Cada reserva gera até duas avaliações (4.6.1) e a do
   anfitrião é sobre o hóspede, não sobre o imóvel. O B.4 não tem coluna
   "alvo", então o tipo é deduzido comparando autor_id com reserva.hospede_id
   (AMBIGUIDADES.md, A09).

2. Só aparecem avaliações PUBLICADAS. Pela sequência 4.6.2-3, o sistema publica
   as avaliações quando ambos avaliam ou quando o prazo termina; o prazo é de
   14 dias após o check-out (RN-06). Avaliação não publicada também não entra
   na nota média (AMBIGUIDADES.md, A10).
"""
from datetime import timedelta

import relogio

PRAZO_AVALIACAO_DIAS = 14  # RN-06


def data_limite_prazo():
    """Reservas com checkOut ANTES desta data já tiveram o prazo encerrado.

    Prazo de 14 dias após o check-out: com check-out em D, ainda é possível
    avaliar até o dia D+14 inclusive; a publicação por prazo ocorre a partir
    de D+15.
    """
    return (relogio.hoje() - timedelta(days=PRAZO_AVALIACAO_DIAS)).isoformat()


# Condição SQL: a avaliação `av` (da reserva `r`) é do hóspede e está publicada.
# Usa o parâmetro nomeado :limite_prazo.
SQL_AVALIACAO_PUBLICA_DO_HOSPEDE = """
    av.autor_id = r.hospede_id
    AND (
        r.checkOut < :limite_prazo
        OR EXISTS (
            SELECT 1 FROM avaliacao outra
             WHERE outra.reserva_id = r.id AND outra.autor_id <> r.hospede_id
        )
    )
"""


def sql_notas_por_acomodacao():
    """Subconsulta (acomodacao_id, notaMedia, totalAvaliacoes)."""
    return f"""
        SELECT r.acomodacao_id AS acomodacao_id,
               AVG(av.nota)    AS notaMedia,
               COUNT(*)        AS totalAvaliacoes
          FROM avaliacao av
          JOIN reserva r ON r.id = av.reserva_id
         WHERE {SQL_AVALIACAO_PUBLICA_DO_HOSPEDE}
         GROUP BY r.acomodacao_id
    """


def arredondar_nota(valor):
    return None if valor is None else round(valor, 2)


def resumo_notas(con, acomodacao_id):
    linha = con.execute(
        f"""SELECT notaMedia, totalAvaliacoes FROM ({sql_notas_por_acomodacao()})
             WHERE acomodacao_id = :id""",
        {"id": acomodacao_id, "limite_prazo": data_limite_prazo()},
    ).fetchone()
    if linha is None:
        return {"notaMedia": None, "totalAvaliacoes": 0}
    return {"notaMedia": arredondar_nota(linha["notaMedia"]), "totalAvaliacoes": linha["totalAvaliacoes"]}


def listar_avaliacoes_publicas(con, acomodacao_id):
    """Avaliações publicadas da acomodação, da mais recente para a mais antiga.

    O autor é exibido só pelo primeiro nome (minimização de dados, LGPD).
    """
    linhas = con.execute(
        f"""
        SELECT av.id, av.nota, av.comentario, av.dataAvaliacao, u.nome AS autor
          FROM avaliacao av
          JOIN reserva r ON r.id = av.reserva_id
          JOIN usuario u ON u.id = av.autor_id
         WHERE r.acomodacao_id = :id AND {SQL_AVALIACAO_PUBLICA_DO_HOSPEDE}
         ORDER BY av.dataAvaliacao DESC, av.id DESC
        """,
        {"id": acomodacao_id, "limite_prazo": data_limite_prazo()},
    ).fetchall()
    return [
        {
            "id": l["id"],
            "nota": l["nota"],
            "comentario": l["comentario"],
            "dataAvaliacao": l["dataAvaliacao"],
            "autor": primeiro_nome(l["autor"]),
        }
        for l in linhas
    ]


def primeiro_nome(nome):
    return (nome or "").split(" ")[0]
