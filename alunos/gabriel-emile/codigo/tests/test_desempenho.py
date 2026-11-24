"""RNF-01: a busca deve responder em até 2 s em 95% das requisições.

O teste cria um volume bem maior que o do seed (3.000 acomodações na mesma
cidade, com fotos, reservas, bloqueios e avaliações) e mede 40 buscas
variadas. É uma verificação local, não substitui teste de carga com usuários
simultâneos (RNF-03 fica fora do escopo).
"""
import random
import time
from datetime import timedelta

from conftest import AGORA, dia
from db import conectar

N_ACOMODACOES = 3000
N_BUSCAS = 40
LIMITE_S = 2.0


def popular_volume(caminho):
    rnd = random.Random(42)
    con = conectar(caminho)
    bairros = ["Copacabana", "Ipanema", "Leblon", "Botafogo", "Gávea", "Santa Teresa"]
    acom, fotos, reservas, hist, aval = [], [], [], [], []
    for i in range(N_ACOMODACOES):
        aid = 1000 + i
        acom.append((aid, 2 if i % 2 else 3, f"Imóvel {aid}", "Descrição", rnd.randint(80, 2000),
                     rnd.randint(1, 10), rnd.randint(1, 5), rnd.randint(1, 4), rnd.randint(1, 6),
                     "Regras", "22000-000", f"Rua {i % 200}", str(i), rnd.choice(bairros),
                     "Rio de Janeiro", "RJ", 1))
        fotos += [(aid, f"fotos/{aid}/{k}.svg", "Foto", k) for k in range(5)]
        for k in range(3):
            rid = aid * 10 + k
            ini = rnd.randint(-60, 120)
            status = rnd.choice(["CONFIRMADA", "CONCLUIDA", "CANCELADA", "PENDENTE"])
            reservas.append((rid, 1, aid, dia(ini), dia(ini + rnd.randint(1, 7)), 2, 100.0, status))
            hist.append((rid, None, "PENDENTE", (AGORA - timedelta(minutes=rnd.randint(0, 120))).isoformat(), 1))
            if status == "CONCLUIDA":
                aval.append((rid, 1, rnd.randint(1, 5), "ok", dia(0)))
    con.executemany("INSERT INTO acomodacao VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", acom)
    con.executemany("INSERT INTO foto_acomodacao (acomodacao_id, chave, legenda, ordem) VALUES (?,?,?,?)", fotos)
    con.executemany("INSERT INTO reserva VALUES (?,?,?,?,?,?,?,?)", reservas)
    con.executemany("INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora, responsavel_id) VALUES (?,?,?,?,?)", hist)
    con.executemany("INSERT INTO avaliacao (reserva_id, autor_id, nota, comentario, dataAvaliacao) VALUES (?,?,?,?,?)", aval)
    con.execute("ANALYZE")
    con.commit()
    con.close()


def test_rnf01_busca_em_ate_2s_no_percentil_95(app, client):
    popular_volume(app.config["DATABASE"])
    rnd = random.Random(7)
    tempos = []
    for _ in range(N_BUSCAS):
        ini = rnd.randint(1, 90)
        q = {
            "cidade": "Rio de Janeiro",
            "bairro": rnd.choice(["Copacabana", "Ipanema", "Botafogo"]),
            "checkin": dia(ini), "checkout": dia(ini + rnd.randint(1, 10)),
            "hospedes": str(rnd.randint(1, 6)),
            "ordenar": rnd.choice(["relevancia", "preco_asc", "nota_desc"]),
        }
        if rnd.random() < 0.5:
            q["preco_max"] = "800"
        t0 = time.perf_counter()
        r = client.get("/api/acomodacoes/busca", query_string=q)
        tempos.append(time.perf_counter() - t0)
        assert r.status_code == 200
    tempos.sort()
    p95 = tempos[int(0.95 * len(tempos)) - 1]
    assert p95 < LIMITE_S, f"p95 = {p95:.3f}s"
