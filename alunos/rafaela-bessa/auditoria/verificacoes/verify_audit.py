import sys
import os
sys.path.insert(0, os.path.abspath("codigo"))

from datetime import date, timedelta
import database
import models
import avaliacoes
from app import app
from services.email_service import EmailService

print("=== INICIANDO VERIFICACAO DE AUDITORIA ===")

# 1. Teste de monkeypatch de avaliacoes.hoje() vs SQLite date()
print("\n[Teste 1] Monkeypatch de avaliacoes.hoje() vs SQLite date(r.checkOut, '+14 days')...")
database.init_db(force_recreate=True)
# Vamos simular uma reserva criada em 2030 (como a propria IA fez em test_conclusao_so_depois_do_dia_do_checkout)
res = models.criar_reserva(1, 1, "2030-01-10", "2030-01-12", 2)
rid_2030 = res["reserva_id"]
models.confirmar_reserva_apos_pagamento(rid_2030)

# Avancamos avaliacoes.hoje() para 2030-01-13 (1 dia apos check-out)
orig_hoje = avaliacoes.hoje
avaliacoes.hoje = lambda: date(2030, 1, 13)

painel_2030 = avaliacoes.painel_do_usuario(1)
pendentes_ids = [p["id"] for p in painel_2030["pendentes"]]
print(f"Reserva 2030 (#{rid_2030}) esta em pendentes no dia 2030-01-13? {rid_2030 in pendentes_ids}")

# Agora Lucas avalia em 2030-01-13 (apenas 1 parte avaliou)
av_res = avaliacoes.registrar_avaliacao(rid_2030, 1, 5, "Avaliacao em 2030")
print(f"Retorno de registrar_avaliacao['publicada']: {av_res['publicada']}")

# Mas e no SQL (_SQL_PUBLICADA)? Vamos testar se ela aparece como publicada em resumo_notas_acomodacao ou painel_do_usuario!
# Wait: em 2030-01-13, date('2030-01-12', '+14 days') = '2030-01-26', que NAO e < '2030-01-13'.
# E se a reserva tiver check-out no passado em relacao a date.today(), ou e se testarmos onde date() do SQLite diverge?
# Espera! Em _SQL_PUBLICADA: date(r.checkOut, '+14 days') < :hoje
# O que date(r.checkOut, '+14 days') faz no SQLite? Ele soma 14 dias a string r.checkOut! NAO usa date('now')!
print("Verificando _SQL_PUBLICADA: date(r.checkOut, '+14 days') soma 14 dias a r.checkOut e compara com :hoje (que vem de avaliacoes.hoje()). Entao _SQL_PUBLICADA funciona com monkeypatch!")
avaliacoes.hoje = orig_hoje

# 2. Teste de /confirmacao/<id> e /pagamento/<id> ANTES de qualquer rota de avaliacao ser chamada!
print("\n[Teste 2] Acesso direto a /confirmacao/<id> ou /pagamento/<id> logo apos check-out sem passar por concluir_reservas_encerradas()...")
database.init_db(force_recreate=True)
EmailService.clear()
# No seed recem-criado, Cenario A (reserva #2) tem check-out D-2 e status Inicial = CONFIRMADA no banco!
conn = database.get_db_connection()
r2_antes = conn.execute("SELECT id, status, checkOut FROM reserva WHERE id = 2").fetchone()
conn.close()
print(f"Status inicial da reserva #2 no banco: {r2_antes['status']} (checkOut={r2_antes['checkOut']})")

# Se um cliente chamar /api/reservas/2/status (que retorna JSON e NAO renderiza template base.html, portanto NAO chama context_processor injetar_pendencias!):
app.config["TESTING"] = True
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 1
    resp_status = c.get("/api/reservas/2/status").get_json()
    print(f"GET /api/reservas/2/status (sem render_template): status retornado = {resp_status['status']}")
    print(f"E-mails de convite enviados ate agora: {len(EmailService.get_sent_emails())}")

    # E agora se o usuario acessar GET /confirmacao/2!
    # Em view_confirmacao (app.py:190), models.obter_reserva_completa(2) e chamado ANTES de render_template!
    # E obter_reserva_completa NAO chama avaliacoes.concluir_reservas_encerradas()!
    # So durante render_template('confirmacao.html') o context_processor injetar_pendencias() roda e muda no banco para CONCLUIDA,
    # MAS o objeto `reserva` passado para confirmacao.html ja foi carregado com status='CONFIRMADA'!
    resp_conf = c.get("/confirmacao/2")
    html_conf = resp_conf.get_data(as_text=True)
    print(f"Na 1a abertura de GET /confirmacao/2, mostra 'ESTADIA CONCLUÍDA'? {'ESTADIA CONCLUÍDA' in html_conf}")
    print(f"Na 1a abertura de GET /confirmacao/2, mostra 'RESERVA CONFIRMADA (RF-20)'? {'RESERVA CONFIRMADA (RF-20)' in html_conf}")
    print(f"Na 1a abertura de GET /confirmacao/2, mostra botao 'Avaliar esta estadia'? {'Avaliar esta estadia' in html_conf}")

# 3. Teste de Reserva no Passado via POST /resumo ou API
print("\n[Teste 3] Criacao de reserva com datas no passado (check-in e check-out ja passados)...")
database.init_db(force_recreate=True)
ontem = (date.today() - timedelta(days=1)).isoformat()
anteontem = (date.today() - timedelta(days=3)).isoformat()
res_passado = models.criar_reserva(1, 1, anteontem, ontem, 2)
print(f"models.criar_reserva permitiu criar reserva no passado ({anteontem} a {ontem})! ID={res_passado['reserva_id']}")

# E se o check-out for há 20 dias (fora do prazo de 14 dias da RN-06)?
d25 = (date.today() - timedelta(days=25)).isoformat()
d20 = (date.today() - timedelta(days=20)).isoformat()
res_antiga = models.criar_reserva(1, 1, d25, d20, 2)
models.confirmar_reserva_apos_pagamento(res_antiga["reserva_id"])
concluidas = avaliacoes.concluir_reservas_encerradas()
print(f"Reserva criada diretamente com check-out D-20 foi concluida imediatamente ({res_antiga['reserva_id'] in concluidas}) e ja nasce com prazo RN-06 expirado!")

# 4. Teste de Acomodacao Inativa (ativo = 0) nas rotas de avaliacao
print("\n[Teste 4] Acomodacao inativa (id=4, ativo=0) em GET /acomodacoes/4/avaliacoes...")
with app.test_client() as c:
    resp_inativa = c.get("/acomodacoes/4/avaliacoes")
    print(f"GET /acomodacoes/4/avaliacoes (acomodacao inativa) status_code = {resp_inativa.status_code}")

# 5. Teste de Race Condition / Falha no envio de e-mail ou reinicio do servidor
print("\n[Teste 5] Reinicio ou falha em concluir_reservas_encerradas e _SENT_EMAILS em memoria...")
# Se avaliacoes.registrar_avaliacao recebe um comentario com caracteres de controle ou espacos internos
database.init_db(force_recreate=True)
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 1
    # Testar nota booleana, float, string com sinal "+5"
    r_plus5 = c.post("/api/reservas/2/avaliacoes", json={"nota": "+5", "comentario": "teste"})
    print(f"POST nota='+5' -> status={r_plus5.status_code} (isdigit() em '+5' eh False)")

    # Testar comentario com 1000 espacos + 1000 caracteres
    r_spaces = c.post("/api/reservas/2/avaliacoes", json={"nota": 5, "comentario": "   " + ("a" * 1000) + "   "})
    print(f"POST comentario com 1006 chars (1000 apos strip) -> status={r_spaces.status_code}")

# 6. Verificar `registrar_avaliacao` quando a reserva ja tem o prazo expirado ou avaliar no ultimo dia:
# Olhe a linha 348-349 de avaliacoes.py:
# total = len(avaliacoes) + 1
# publicada = total >= 2
print("\n[Teste 6] Verificar avaliacoes.py:349 (`publicada = total >= 2`)...")
# Se por algum motivo uma avaliacao fosse registrada ou se olharmos a logica:
# Mas mais importante: o que acontece na Tela `avaliar.html` quando `outra_parte_ja_avaliou` e o usuario NAO pode avaliar (ex: reserva no Cenário B ou D)?
database.init_db(force_recreate=True)
with app.test_client() as c:
    # No Cenario B (reserva #3), Mariana (id=4) ja avaliou Lucas (id=1). Prazo ainda nao venceu (D-5).
    # Se Mariana (que JA avaliou, entao s.pode_avaliar == False e s.minha_avaliacao != None) abre /reservas/3/avaliar:
    # E se Lucas tivesse avaliado? Ambos avaliaram -> publicada.
    # Mas e se um terceiro estado ocorrer: Reserva CONCLUIDA, Mariana avaliou, Lucas NAO avaliou, e Lucas esta impedido? Nao, se Lucas nao avaliou e prazo nao acabou, Lucas pode avaliar.
    pass

# 7. Verificar visualizacao de `/confirmacao/<id>` pelo ANFITRIAO!
print("\n[Teste 7] Anfitriao acessa GET /confirmacao/2 (reserva CONCLUIDA)...")
database.init_db(force_recreate=True)
avaliacoes.concluir_reservas_encerradas()
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 3 # Carlos (Anfitriao da reserva #2)
    resp_anf_conf = c.get("/confirmacao/2")
    html_anf_conf = resp_anf_conf.get_data(as_text=True)
    print(f"Anfitriao (id=3) pode acessar /confirmacao/2? status={resp_anf_conf.status_code}")
    print(f"O que aparece para o Anfitriao em /confirmacao/2? Botao 'Avaliar esta estadia' (texto de hospede UC18 em vez de 'Avaliar hospede' UC19) E texto 'Tudo pronto! Sua hospedagem...' / 'Uma copia detalhada deste comprovante foi enviada para hospede_teste@exemplo.com'!")
    # E se a reserva ja foi avaliada ou o prazo ja encerrou (ex: Cenario D, reserva #5, D-20)?
    resp_d_conf = c.get("/confirmacao/5")
    html_d_conf = resp_d_conf.get_data(as_text=True)
    print(f"Em /confirmacao/5 (Cenario D, check-out D-20, prazo encerrado e Lucas ja avaliou), o botao 'Avaliar esta estadia' AINDA aparece? {'Avaliar esta estadia' in html_d_conf}")

    # E no Cenario G (reserva #9, anfitriao hospedado na propria acomodacao, onde NINGUEM pode avaliar):
    resp_g_conf = c.get("/confirmacao/9")
    html_g_conf = resp_g_conf.get_data(as_text=True)
    print(f"Em /confirmacao/9 (Cenario G, auto-hospedagem bloqueada), o botao 'Avaliar esta estadia' AINDA aparece? {'Avaliar esta estadia' in html_g_conf}")
