"""Verificação do grupo sobre a auditoria do ChatGPT.

O ChatGPT não conseguiu rodar o sistema. Este script reproduz, num banco
temporário (nunca o hospedagem.db do app), dois achados que ele deixou como
suspeita ou que só testou num núcleo isolado:

  A-03  o reembolso tardio muda se o anfitrião alterar o preço por noite;
  A-04  /api/dev/switch-user deixa qualquer visitante agir como o hóspede
        e cancelar a reserva dele.

Uso, a partir de alunos/pedro-loschi/:
    python auditoria/verificacoes/verificacao_grupo.py
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta

os.environ["HOSPEDAGEM_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "verificacao.db")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "codigo"))

import database  # noqa: E402
import cancelamento  # noqa: E402
from app import app  # noqa: E402

database.init_db(force_recreate=True)
conn = database.get_db_connection()
reserva = conn.execute("""
    SELECT r.id, r.hospede_id, r.checkIn, r.acomodacao_id, a.anfitriao_id
    FROM reserva r JOIN acomodacao a ON a.id = r.acomodacao_id
    JOIN pagamento p ON p.reserva_id = r.id AND p.status = 'APROVADO'
    WHERE r.status = 'CONFIRMADA' ORDER BY r.id LIMIT 1""").fetchone()
estranho = conn.execute("SELECT id FROM usuario WHERE id NOT IN (?, ?) ORDER BY id LIMIT 1",
                        (reserva["hospede_id"], reserva["anfitriao_id"])).fetchone()["id"]
print(f"Reserva #{reserva['id']} CONFIRMADA: hóspede {reserva['hospede_id']}, "
      f"anfitrião {reserva['anfitriao_id']}; usuário sem relação com ela: {estranho}")

# A-03: mesma reserva, mesmo pagamento, preço por noite alterado depois
check_in = datetime.strptime(reserva["checkIn"], "%Y-%m-%d")
agora = check_in - timedelta(hours=24)  # dentro das 48 h: 50% das diárias
antes = cancelamento.obter_previa_cancelamento(reserva["id"], reserva["hospede_id"], agora=agora)
conn.execute("UPDATE acomodacao SET precoNoite = precoNoite * 2 WHERE id = ?", (reserva["acomodacao_id"],))
conn.commit()
depois = cancelamento.obter_previa_cancelamento(reserva["id"], reserva["hospede_id"], agora=agora)
v1, v2 = antes["reembolso"]["valor_reembolso"], depois["reembolso"]["valor_reembolso"]
print(f"\nA-03  reembolso tardio antes de dobrar o preço: R$ {v1:.2f}; depois: R$ {v2:.2f}")
print("      CONFIRMADO" if v1 != v2 else "      não reproduzido")
conn.execute("UPDATE acomodacao SET precoNoite = precoNoite / 2 WHERE id = ?", (reserva["acomodacao_id"],))
conn.commit()
conn.close()

# A-04: um usuário sem relação com a reserva troca de identidade e cancela
cliente = app.test_client()
cliente.post("/api/dev/switch-user", data={"usuario_id": estranho})
r1 = cliente.post(f"/api/reservas/{reserva['id']}/cancelamento", json={})
cliente.post("/api/dev/switch-user", data={"usuario_id": reserva["hospede_id"]})  # sem senha
r2 = cliente.post(f"/api/reservas/{reserva['id']}/cancelamento", json={})
print(f"\nA-04  como usuário {estranho}: HTTP {r1.status_code}; "
      f"depois de /api/dev/switch-user para o hóspede: HTTP {r2.status_code}, "
      f"status da reserva: {r2.get_json().get('status')}")
print("      CONFIRMADO" if r1.status_code in (401, 403) and r2.status_code == 200 else "      não reproduzido")
