"""Verificações da auditoria do código gerado pelo Gemini (fluxo de reserva).

Cada verificação reproduz um problema descrito em auditoria_ia.md.
Roda num banco SQLite temporário, sem tocar no hospedagem.db do projeto.

Uso (na pasta rodada1, com o venv ativo):
    python auditoria/verificacoes.py
"""
import logging
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

database.DATABASE_NAME = os.path.join(tempfile.mkdtemp(), "auditoria.db")
database.init_db()

from app import app  # noqa: E402  (importado depois de trocar o banco)

app.logger.disabled = True
logging.getLogger("werkzeug").disabled = True
cliente = app.test_client()
resultados = []


def logar(usuario_id, nome="Hóspede Teste", email="hospede@teste.com"):
    with cliente.session_transaction() as sessao:
        sessao["usuario_id"] = usuario_id
        sessao["usuario_nome"] = nome
        sessao["usuario_email"] = email


def nova_reserva(acomodacao, checkin, checkout, hospedes=1):
    resposta = cliente.post("/api/reservas", json={
        "acomodacao_id": acomodacao, "checkin": checkin,
        "checkout": checkout, "num_hospedes": hospedes,
    })
    return resposta.status_code, resposta.get_json(silent=True) or {}


def envelhecer(reserva_id, intervalo):
    conn = database.get_db()
    conn.execute("UPDATE reserva SET criadoEm = datetime('now', ?) WHERE id = ?",
                 (intervalo, reserva_id))
    conn.commit()
    conn.close()


def registrar(codigo, descricao, confirmado, detalhe):
    resultados.append((codigo, descricao, confirmado, detalhe))


logar(1)

# A01: webhook PIX aceito sem autenticação e com valor diferente do cobrado
_, r = nova_reserva(1, "2027-03-01", "2027-03-03")
txid = cliente.post(f"/api/reservas/{r['reserva_id']}/gerar-pix").get_json()["txid"]
resp = cliente.post("/api/webhook/pix", json={"txid": txid, "valor": 99999})
registrar("A01", "Webhook PIX falso (sem assinatura, valor errado) confirma a reserva",
          resp.status_code == 200, f"HTTP {resp.status_code}")

# A02: a mesma reserva paga duas vezes (cartão e PIX)
_, r = nova_reserva(1, "2027-04-01", "2027-04-03")
rid = r["reserva_id"]
txid = cliente.post(f"/api/reservas/{rid}/gerar-pix").get_json()["txid"]
cliente.post(f"/api/reservas/{rid}/pagar-cartao", json={"numero_cartao": "4111111111111111"})
cliente.post("/api/webhook/pix", json={"txid": txid, "valor": 456})
conn = database.get_db()
aprovados = conn.execute("SELECT COUNT(*) FROM pagamento WHERE reserva_id = ? AND status = 'APROVADO'",
                         (rid,)).fetchone()[0]
conn.close()
registrar("A02", "Reserva já confirmada aceita um segundo pagamento aprovado",
          aprovados == 2, f"{aprovados} pagamentos APROVADO na mesma reserva")

# A03: outro usuário vê a confirmação, com endereço completo, de reserva alheia
_, r = nova_reserva(1, "2027-09-01", "2027-09-03")
rid = r["reserva_id"]
cliente.post(f"/api/reservas/{rid}/pagar-cartao", json={"numero_cartao": "4111111111111111"})
logar(2, "Outro usuário", "outro@teste.com")
html = cliente.get(f"/reservas/{rid}/confirmacao").get_data(as_text=True)
logar(1)
registrar("A03", "Usuário 2 abre a confirmação da reserva do usuário 1 e vê rua e CEP",
          "22041-001" in html, "endereço completo exibido" if "22041-001" in html else "bloqueado")

# A04: PIX pago depois do prazo fica sem reembolso e preso em PROCESSANDO
_, r = nova_reserva(1, "2027-05-01", "2027-05-03")
rid = r["reserva_id"]
txid = cliente.post(f"/api/reservas/{rid}/gerar-pix").get_json()["txid"]
envelhecer(rid, "-31 minutes")
resp = cliente.post("/api/webhook/pix", json={"txid": txid, "valor": 456})
conn = database.get_db()
status_pix = conn.execute("SELECT status FROM pagamento WHERE txid = ?", (txid,)).fetchone()[0]
conn.close()
registrar("A04", "PIX pago após os 30 minutos: recusado sem reembolso, pagamento fica PROCESSANDO",
          resp.status_code == 400 and status_pix == "PROCESSANDO",
          f"webhook HTTP {resp.status_code}, pagamento {status_pix}")

# A05: reserva expirada continua bloqueando as datas
_, r = nova_reserva(1, "2027-06-01", "2027-06-05")
envelhecer(r["reserva_id"], "-2 days")
status, _ = nova_reserva(1, "2027-06-02", "2027-06-04")
registrar("A05", "Reserva PENDENTE expirada há 2 dias ainda bloqueia o período",
          status == 409, f"nova reserva: HTTP {status}")

# A06: valores inválidos aceitos
s_zero, _ = nova_reserva(1, "2027-07-01", "2027-07-02", 0)
s_neg, _ = nova_reserva(1, "2027-07-03", "2027-07-04", -3)
s_passado, _ = nova_reserva(1, "2020-01-01", "2020-01-05")
registrar("A06", "Reserva criada com 0 ou -3 hóspedes e com check-in no passado",
          (s_zero, s_neg, s_passado) == (200, 200, 200),
          f"0 hóspedes: {s_zero}, -3 hóspedes: {s_neg}, passado: {s_passado}")

# A07: entrada malformada derruba a requisição com erro 500
s_sem, s_data = (
    cliente.post("/api/reservas", json={"acomodacao_id": 1, "checkin": "2027-08-01",
                                        "checkout": "2027-08-02"}).status_code,
    cliente.post("/api/reservas", json={"acomodacao_id": 1, "checkin": "amanha",
                                        "checkout": "2027-08-02", "num_hospedes": 1}).status_code,
)
registrar("A07", "Campo ausente ou data malformada geram erro 500 em vez de mensagem",
          (s_sem, s_data) == (500, 500), f"sem hóspedes: {s_sem}, data inválida: {s_data}")

# A08: mudanças de status de pagamento não são auditadas (RNF-22)
conn = database.get_db()
entidades = [linha[0] for linha in conn.execute("SELECT DISTINCT entidade FROM auditoria")]
status_cartao = [linha[0] for linha in conn.execute(
    "SELECT DISTINCT status FROM pagamento WHERE metodo = 'CARTAO'")]
conn.close()
registrar("A08", "Auditoria só registra reservas; cartão nunca passa por PROCESSANDO",
          entidades == ["reserva"] and "PROCESSANDO" not in status_cartao,
          f"entidades auditadas: {entidades}; status de cartão: {sorted(status_cartao)}")

# A09: uma exceção no meio da gravação trava o banco para os pedidos seguintes
logar(99, "Usuário inexistente")
cliente.post("/api/reservas", json={"acomodacao_id": 1, "checkin": "2027-10-01",
                                    "checkout": "2027-10-02", "num_hospedes": 1})
logar(1)
inicio = time.time()
resp = cliente.post("/api/reservas", json={"acomodacao_id": 1, "checkin": "2027-10-05",
                                           "checkout": "2027-10-06", "num_hospedes": 1})
registrar("A09", "Depois de um erro de gravação, um pedido válido falha com 'database is locked'",
          resp.status_code == 500, f"HTTP {resp.status_code} após {time.time() - inicio:.1f}s")

print()
for codigo, descricao, confirmado, detalhe in resultados:
    marca = "CONFIRMADO" if confirmado else "não reproduzido"
    print(f"[{marca:>15}] {codigo} {descricao}\n{'':18}{detalhe}")
print(f"\n{sum(r[2] for r in resultados)} de {len(resultados)} problemas reproduzidos.")
