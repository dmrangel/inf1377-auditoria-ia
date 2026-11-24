"""
seed_avaliacoes.py - Dados de exemplo da Avaliação de Estadia
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)

Cria reservas no PASSADO (datas relativas a hoje, D) para demonstrar todos os
cenários de avaliação. Ficam todas antes de hoje para não colidir com as datas
usadas pelo fluxo de reserva e pelos seus testes.

Roda uma única vez: só insere se a tabela avaliacao estiver vazia, então também
funciona num hospedagem.db criado antes desta funcionalidade.
"""

from datetime import date, datetime, timedelta


def _id_por_email(cursor, email):
    cursor.execute("SELECT id FROM usuario WHERE email = ?;", (email,))
    row = cursor.fetchone()
    return row["id"] if row else None


def seed_avaliacoes(conn):
    # Importação tardia: models importa database, que chama esta função.
    from models import calcular_valores_estadia

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS n FROM avaliacao;")
    if cursor.fetchone()["n"] > 0:
        return

    lucas = _id_por_email(cursor, "hospede_teste@exemplo.com")
    ana = _id_por_email(cursor, "ana_hospede@exemplo.com")
    carlos = _id_por_email(cursor, "carlos_anfitriao@exemplo.com")
    mariana = _id_por_email(cursor, "mariana_superhost@exemplo.com")
    if None in (lucas, ana, carlos, mariana):
        return  # banco sem os usuários padrão de database.seed_test_data

    def acomodacao(titulo_inicio):
        cursor.execute(
            "SELECT a.id, a.precoNoite, u.superhost FROM acomodacao a JOIN usuario u ON u.id = a.anfitriao_id "
            "WHERE a.titulo LIKE ?;", (titulo_inicio + "%",)
        )
        return cursor.fetchone()

    copacabana = acomodacao("Apartamento Aconchegante")   # anfitrião Carlos
    ipanema = acomodacao("Loft Moderno em Ipanema")        # anfitriã Mariana (superhost)
    chale = acomodacao("Chalé Rústico")                    # anfitrião Carlos

    hoje = date.today()
    agora = datetime.now()

    def d(dias):
        return (hoje + timedelta(days=dias)).isoformat()

    def momento(dias):
        return (agora + timedelta(days=dias)).isoformat(timespec="seconds")

    def reserva(hospede, acom, ini, fim, status):
        """Insere a reserva com pagamento aprovado e histórico coerente (RNF-22)."""
        valores = calcular_valores_estadia(acom["precoNoite"], d(ini), d(fim), bool(acom["superhost"]))
        criada = momento(ini - 10)
        cursor.execute("""
            INSERT INTO reserva (hospede_id, acomodacao_id, checkIn, checkOut, numHospedes, valorTotal, status, dataCriacao)
            VALUES (?, ?, ?, ?, 2, ?, ?, ?);
        """, (hospede, acom["id"], d(ini), d(fim), valores["valor_total"], status, criada))
        rid = cursor.lastrowid
        historico = [(None, "PENDENTE", criada, hospede)]
        if status == "CANCELADA":
            historico.append(("PENDENTE", "CANCELADA", criada, None))   # expirou (RN-04)
        else:
            historico.append(("PENDENTE", "CONFIRMADA", criada, None))
            cursor.execute("""
                INSERT INTO pagamento (reserva_id, txid, metodo, valor, codigoAutorizacao, status, dataHora, tokenCartao)
                VALUES (?, ?, 'CARTAO_CREDITO', ?, ?, 'APROVADO', ?, ?);
            """, (rid, f"SEED-{rid}-CARTAO", valores["valor_total"], f"AUTH-SEED{rid}", criada, f"tok_seed_{rid}"))
            cursor.execute("""
                INSERT INTO historico_status_pagamento (pagamento_id, statusAnterior, statusNovo, dataHora, responsavel_id)
                VALUES (?, NULL, 'APROVADO', ?, ?);
            """, (cursor.lastrowid, criada, hospede))
        if status == "CONCLUIDA":
            historico.append(("CONFIRMADA", "CONCLUIDA", momento(fim + 1), None))
        for anterior, novo, quando, resp in historico:
            cursor.execute("""
                INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora, responsavel_id)
                VALUES (?, ?, ?, ?, ?);
            """, (rid, anterior, novo, quando, resp))
        return rid

    def avaliacao(rid, autor, nota, comentario, dias):
        cursor.execute("""
            INSERT INTO avaliacao (reserva_id, autor_id, nota, comentario, dataAvaliacao)
            VALUES (?, ?, ?, ?, ?);
        """, (rid, autor, nota, comentario, momento(dias)))

    # Cenário A - caminho feliz: Lucas em Copacabana, check-out há 2 dias, ainda CONFIRMADA.
    # Vira CONCLUIDA no primeiro acesso e os dois são convidados por e-mail.
    reserva(lucas, copacabana, -5, -2, "CONFIRMADA")

    # Cenário B - publicação ao segundo voto: Lucas em Ipanema. Mariana já avaliou Lucas;
    # a avaliação dela fica oculta até Lucas avaliar. Mariana tentar de novo -> 409 (RF-31).
    rid = reserva(lucas, ipanema, -8, -5, "CONCLUIDA")
    avaliacao(rid, mariana, 5, "Hóspede educado, deixou tudo organizado.", -4)

    # Cenário C - último dia do prazo: check-out há exatamente 14 dias (RN-06, inclusive).
    reserva(lucas, chale, -17, -14, "CONCLUIDA")

    # Cenário D - prazo encerrado: check-out há 20 dias. Só Lucas avaliou; como o prazo
    # terminou, a avaliação dele está publicada. Carlos tentar avaliar -> erro RN-06.
    rid = reserva(lucas, chale, -25, -20, "CONCLUIDA")
    avaliacao(rid, lucas, 4, "Lugar lindo e silencioso. A lareira poderia ter mais lenha.", -18)

    # Cenário E - reserva CANCELADA: não pode ser avaliada (RF-30).
    reserva(lucas, copacabana, -12, -10, "CANCELADA")

    # Cenário F - histórico publicado (as duas partes avaliaram): base da nota média.
    rid = reserva(ana, copacabana, -35, -30, "CONCLUIDA")
    avaliacao(rid, ana, 5, "Apartamento impecável e muito bem localizado.", -29)
    avaliacao(rid, carlos, 4, "Boa hóspede, só atrasou um pouco o check-out.", -28)

    rid = reserva(ana, ipanema, -40, -38, "CONCLUIDA")
    avaliacao(rid, ana, 4, None, -37)   # comentário é opcional (RF-29)
    avaliacao(rid, mariana, 5, "Ótima comunicação.", -36)

    # Cenário G - anfitrião hospedado na própria acomodação: ninguém pode avaliar.
    reserva(carlos, copacabana, -9, -7, "CONCLUIDA")

    conn.commit()
    print("[seed_avaliacoes] Reservas passadas e avaliações de exemplo inseridas.")
