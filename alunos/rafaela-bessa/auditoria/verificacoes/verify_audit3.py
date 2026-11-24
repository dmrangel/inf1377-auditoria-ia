import sys
import os
sys.path.insert(0, os.path.abspath("codigo"))

from datetime import date, timedelta
import database
import models
import avaliacoes
from app import app
from services.email_service import EmailService

print("=== TESTE DE CASOS DE BORDA ADICIONAIS ===")

# 1. Arredondamento inconsistente entre API JSON (2 casas decimais) e filtro nota_br (1 casa decimal)
print("\n[Teste 8] Arredondamento da nota media: API vs Template vsEstrelas...")
database.init_db(force_recreate=True)
# Vamos adicionar avaliacoes para que a media de Copacabana seja 14 / 3 = 4.6666...
# Atualmente Copacabana tem nota 5 (Ana, reserva #7).
# Vamos avaliar reserva #2 (Lucas=5, Carlos=5) e criar outra reserva concluida com nota 4.
avaliacoes.concluir_reservas_encerradas()
avaliacoes.registrar_avaliacao(2, 1, 5)
avaliacoes.registrar_avaliacao(2, 3, 5)
# Criar reserva #10 para Ana com nota 4
d4 = (date.today() - timedelta(days=4)).isoformat()
d3 = (date.today() - timedelta(days=3)).isoformat()
r10 = models.criar_reserva(2, 1, d4, d3, 1)
models.confirmar_reserva_apos_pagamento(r10["reserva_id"])
avaliacoes.concluir_reservas_encerradas()
avaliacoes.registrar_avaliacao(r10["reserva_id"], 2, 4)
avaliacoes.registrar_avaliacao(r10["reserva_id"], 3, 5)

resumo = avaliacoes.resumo_notas_acomodacao(1)
print(f"Resumo em JSON (API): media={resumo['media']} (round 2 casas)")
with app.test_client() as c:
    html = c.get("/acomodacoes/1/avaliacoes").get_data(as_text=True)
    print(f"Na tela HTML (nota_br): '4,7' in html? {'4,7' in html}")

# 2. O que acontece se um usuario nao-participante (ex: Ana, id=2) ou o proprio participante acessa GET /reservas/<id>/avaliar quando reserva nao existe (404) ou nao participa (403)?
print("\n[Teste 9] Status HTTP de GET /reservas/<id>/avaliar quando 403 ou 404...")
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 2 # Ana
    resp_403 = c.get("/reservas/2/avaliar")
    print(f"GET /reservas/2/avaliar por nao-participante -> status={resp_403.status_code} (redireciona 302 para /avaliacoes com flash em vez de retornar HTTP 403)")
    resp_404 = c.get("/reservas/99999/avaliar")
    print(f"GET /reservas/99999/avaliar inexistente -> status={resp_404.status_code} (redireciona 302 para /avaliacoes com flash em vez de retornar HTTP 404)")

# 3. E se na rota GET /reservas/<id>/avaliar a reserva ESTIVER BLOQUEADA (ex: RF-30 reserva PENDENTE/CONFIRMADA/CANCELADA, ou RN-06 prazo encerrado)?
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 1 # Lucas
    resp_canc = c.get("/reservas/6/avaliar") # Cenario E - CANCELADA
    print(f"GET /reservas/6/avaliar (CANCELADA) -> status={resp_canc.status_code}")

# 4. Verificar trap de banco de dados existente (migration / CHECK constraint e seed_avaliacoes)
print("\n[Teste 10] Comportamento de database.init_db() quando hospedagem.db ja existia sem CHECK ou quando todas as avaliacoes sao apagadas...")
# No README linha 445: "O CHECK só vale para bancos novos; um hospedagem.db antigo continua sem ele"
# E em seed_avaliacoes.py linha 27: "SELECT COUNT(*) AS n FROM avaliacao; if n > 0: return"
# Se o banco ja tivesse 1 avaliacao, nao roda seed. Mas se todas as avaliacoes fossem excluidas (ou num banco novo onde ainda nao havia avaliacao), toda vez que init_db() rodasse com avaliacao vazia, ele inseriria 8 reservas DUPLICADAS!
conn = database.get_db_connection()
qtd_reservas_antes = conn.execute("SELECT COUNT(*) FROM reserva").fetchone()[0]
conn.execute("DELETE FROM avaliacao")
conn.commit()
conn.close()
database.init_db(force_recreate=False)
conn = database.get_db_connection()
qtd_reservas_depois = conn.execute("SELECT COUNT(*) FROM reserva").fetchone()[0]
conn.close()
print(f"Reservas antes={qtd_reservas_antes}, depois de init_db() com tabela avaliacao vazia={qtd_reservas_depois} (duplicou as 8 reservas do seed_avaliacoes!)")

# 5. Verificar SQLite Foreign Keys e Concorrencia / Lock
print("\n[Teste 11] Verificar avaliacoes.py quando usuario_id nao existe na tabela usuario (mas esta na sessao)...")
database.init_db(force_recreate=True)
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 999 # usuario que nao existe
    # Se tentar avaliar reserva 2, papel_do_usuario retorna None -> 403.
    # Mas e se o usuario_id da sessao for o hospede da reserva e por algum motivo IntegrityError de FK ou CHECK ocorrer em registrar_avaliacao?
    pass

# E se o check constraint do banco falhar em registrar_avaliacao (por exemplo, se _validar_nota fosse burlado ou outro IntegrityError ocorresse)?
# Veja avaliacoes.py linhas 342-346:
# except sqlite3.IntegrityError:
#     conn.rollback()
#     raise ErroAvaliacao("Você já avaliou esta estadia. Cada participante avalia uma única vez (RF-31).", 409)
# Qualquer IntegrityError (mesmo CHECK constraint ou FOREIGN KEY constraint) eh capturado e transformado em erro 409 "Você já avaliou esta estadia (RF-31)"!
print("Verificado em avaliacoes.py:342-346: qualquer sqlite3.IntegrityError (inclusive CHECK ou FK) eh reportado falsamente como 409 'Você já avaliou esta estadia (RF-31)'.")

# 6. Verificar `painel_do_usuario` (avaliacoes.py:508 e 523) quando um usuario eh HOSPEDE e ANFITRIAO da mesma reserva (Cenario G, reserva #9)!
print("\n[Teste 12] Cenario G (auto-hospedagem) caso existisse avaliacao no banco ou em situacao_para_usuario...")
# Em situacao_para_usuario(9, 3):
sit_g = avaliacoes.situacao_para_usuario(9, 3)
print(f"situacao_para_usuario(9, 3): papel={sit_g['papel']}, pode_avaliar={sit_g['pode_avaliar']}, dias_restantes={sit_g['dias_restantes']}")
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 3
    html_g = c.get("/reservas/9/avaliar").get_data(as_text=True)
    # Veja templates/avaliar.html linha 10:
    # {% set eh_hospede = (s.papel != 'ANFITRIAO') %}
    # E linha 25:
    # {% if eh_hospede %} <div><strong>Anfitrião:</strong> {{ r.anfitriao_nome }}</div>
    print(f"Em /reservas/9/avaliar (PAPEL_CONFLITO), o titulo exibido eh 'Como foi sua estadia?' ({'Como foi sua estadia?' in html_g}) e mostra Anfitriao: Carlos Eduardo, tratando o conflito visualmente como tela de hospede!")

# 7. Verificar se `api_status_reserva` (/api/reservas/<id>/status) tem falha de RNF-11 (controle de acesso)!
print("\n[Teste 13] Verificar RNF-11 em /api/reservas/<id>/status e models.obter_reserva_completa...")
# Olhe models.py linha 388:
# def obter_reserva_completa(reserva_id: int, usuario_logado_id: Optional[int] = None)
# A docstring na linha 392 DIZ:
# "Aplica RNF-11: Verifica se usuário é o hóspede ou anfitrião caso fornecido."
# MAS OLHE O CORPO DE obter_reserva_completa (linhas 394-465):
# O parametro `usuario_logado_id` NUNCA EH USADO DENTRO DA FUNCAO!
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 2 # Ana
    res_leak = models.obter_reserva_completa(2, usuario_logado_id=2) # Reserva #2 eh do Lucas (id=1) com Carlos (id=3)!
    print(f"models.obter_reserva_completa(2, usuario_logado_id=2) retornou os dados da reserva do Lucas para a Ana?! {res_leak is not None} (rua={res_leak['acomodacao_rua']})")
    resp_api_status = c.get("/api/reservas/2/status")
    print(f"GET /api/reservas/2/status logado como Ana (id=2) -> status={resp_api_status.status_code}, json={resp_api_status.get_json()}")
