import sys
import os
sys.path.insert(0, os.path.abspath("codigo"))

from datetime import date, timedelta
import database
import models
import avaliacoes
from app import app
from services.email_service import EmailService

print("=== CONTINUANDO VERIFICACAO DE AUDITORIA ===")

# Teste 2B: RF-19 (reservas sobrepostas) ignora reservas CONCLUIDAS!
print("\n[Teste 2B] RF-19: validar_disponibilidade_e_regras ignora status CONCLUIDA!")
database.init_db(force_recreate=True)
# No seed, a reserva #3 (Cenario B, Ipanema, D-8 a D-5) esta com status CONCLUIDA!
# Vamos tentar criar uma nova reserva em Ipanema (acomodacao 2) exatamente nas mesmas datas (D-8 a D-5)!
d8 = (date.today() - timedelta(days=8)).isoformat()
d5 = (date.today() - timedelta(days=5)).isoformat()
res_sobreposta = models.criar_reserva(2, 2, d8, d5, 2)
print(f"Reservar acomodacao 2 em D-8..D-5 (onde JA EXISTE a reserva #3 CONCLUIDA) funcionou?! ID={res_sobreposta['reserva_id']}")

# E se a pessoa pagar essa reserva criada no passado (D-8 a D-5)?
models.confirmar_reserva_apos_pagamento(res_sobreposta["reserva_id"])
# No proximo acesso, concluir_reservas_encerradas() transforma essa reserva sobreposta em CONCLUIDA!
concl = avaliacoes.concluir_reservas_encerradas()
print(f"A reserva sobreposta no passado #{res_sobreposta['reserva_id']} virou CONCLUIDA ({res_sobreposta['reserva_id'] in concl}) e permite o usuario avaliar uma estadia impossivel/sobreposta!")

# Teste 3: Criacao de reserva com datas no passado (em periodo sem reserva CONFIRMADA/PENDENTE)
print("\n[Teste 3] Criacao de reserva com datas no passado e impacto em RF-32 / fraude de avaliacoes...")
d3 = (date.today() - timedelta(days=3)).isoformat()
d1 = (date.today() - timedelta(days=1)).isoformat()
res_passado = models.criar_reserva(1, 2, d3, d1, 1)
models.confirmar_reserva_apos_pagamento(res_passado["reserva_id"])
avaliacoes.concluir_reservas_encerradas()
av_fraude = avaliacoes.registrar_avaliacao(res_passado["reserva_id"], 1, 1, "Reserva criada no passado e avaliada imediatamente!")
print(f"Avaliacao registrada para reserva recem-criada no passado! {av_fraude}")

# Teste 4: Acomodacao inativa (ativo = 0) nas rotas de avaliacao
print("\n[Teste 4] Acomodacao inativa (id=4, ativo=0) em GET /acomodacoes/4/avaliacoes...")
with app.test_client() as c:
    resp_inativa = c.get("/acomodacoes/4/avaliacoes")
    print(f"GET /acomodacoes/4/avaliacoes (acomodacao inativa) status_code = {resp_inativa.status_code}")

# Teste 5: Notas com espacos ou sinais e comentarios
print("\n[Teste 5] Validacao de nota e comentario...")
database.init_db(force_recreate=True)
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 1
    r_plus5 = c.post("/api/reservas/2/avaliacoes", json={"nota": "+5", "comentario": "teste"})
    print(f"POST nota='+5' -> status={r_plus5.status_code}")

    # E dígitos Unicode não-ASCII? Em Python, "⑤".isdigit() ou "５".isdigit() ou "²".isdigit()!
    for ch in ["²", "³", "¹", "５", "❹"]:
        try:
            print(f"  ch={ch!r}: isdigit()={ch.isdigit()}")
            r_uni = c.post("/api/reservas/2/avaliacoes", json={"nota": ch})
            print(f"  POST nota={ch!r} -> status={r_uni.status_code}")
        except Exception as e:
            print(f"  POST nota={ch!r} -> EXCECAO 500! {type(e).__name__}: {e}")

# Teste 7: Visualizacao de /confirmacao/<id> em varios cenarios
print("\n[Teste 7] Visualizacao de /confirmacao/<id> para reservas CONCLUIDAS...")
database.init_db(force_recreate=True)
avaliacoes.concluir_reservas_encerradas()
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess["session_initialized"] = True
        sess["usuario_id"] = 3 # Carlos
    resp_anf_conf = c.get("/confirmacao/2")
    html_anf_conf = resp_anf_conf.get_data(as_text=True)
    print(f"Anfitriao (id=3) em /confirmacao/2: status={resp_anf_conf.status_code}, tem botao 'Avaliar esta estadia'? {'Avaliar esta estadia' in html_anf_conf}")

    resp_d_conf = c.get("/confirmacao/5")
    html_d_conf = resp_d_conf.get_data(as_text=True)
    print(f"Em /confirmacao/5 (prazo encerrado D-20), botao 'Avaliar esta estadia' aparece? {'Avaliar esta estadia' in html_d_conf}")

    resp_g_conf = c.get("/confirmacao/9")
    html_g_conf = resp_g_conf.get_data(as_text=True)
    print(f"Em /confirmacao/9 (auto-hospedagem bloqueada), botao 'Avaliar esta estadia' aparece? {'Avaliar esta estadia' in html_g_conf}")
