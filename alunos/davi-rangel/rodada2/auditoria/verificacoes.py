"""Verificações da auditoria da rodada 2 (Gemini 3.8 Flash, conversa única no Antigravity).

A primeira parte reproduz os problemas descritos em auditoria_ia.md (B01 a B08).
A segunda confere se os problemas da rodada 1 foram corrigidos.
Roda num banco SQLite temporário, sem tocar no hospedagem.db do projeto.

Uso (na pasta rodada2):
    python auditoria/verificacoes.py
"""
import logging
import os
import sys
import tempfile
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

database.DB_PATH = os.path.join(tempfile.mkdtemp(), "auditoria.db")

import models  # noqa: E402  (importados depois de trocar o banco)
from app import app  # noqa: E402
from services.email_service import EmailService  # noqa: E402

app.logger.disabled = True
logging.getLogger("werkzeug").disabled = True
cliente = app.test_client()
problemas, correcoes = [], []
CARTAO_OK = {"titular": "Lucas", "numero_cartao": "4111111111114000", "validade": "12/30", "cvv": "123"}


def dia(n):
    return (date.today() + timedelta(days=n)).isoformat()


def logar(usuario_id):
    with cliente.session_transaction() as sessao:
        sessao["session_initialized"] = True
        sessao["usuario_id"] = usuario_id


def consulta(sql, *params):
    conn = database.get_db_connection()
    linhas = [dict(linha) for linha in conn.execute(sql, params).fetchall()]
    conn.close()
    return linhas


def reserva(hospede, acomodacao, inicio, fim, hospedes=1):
    return models.criar_reserva(hospede, acomodacao, dia(inicio), dia(fim), hospedes)["reserva_id"]


def gerar_pix(reserva_id):
    return cliente.post("/api/pagamento/pix/gerar", json={"reserva_id": reserva_id}).get_json()["cobranca"]


def webhook(cobranca):
    valor = consulta("SELECT valor FROM pagamento WHERE txid = ?", cobranca["txid"])[0]["valor"]
    return cliente.post("/api/webhook/pix", json={"txid": cobranca["txid"], "valor": valor})


def envelhecer(reserva_id, minutos):
    momento = (datetime.now() - timedelta(minutes=minutos)).isoformat()
    conn = database.get_db_connection()
    conn.execute("UPDATE reserva SET dataCriacao = ? WHERE id = ?", (momento, reserva_id))
    conn.commit()
    conn.close()


def registrar(lista, codigo, descricao, confirmado, detalhe):
    lista.append((codigo, descricao, confirmado, detalhe))


cep = consulta("SELECT cep FROM acomodacao WHERE id = 1")[0]["cep"]
logar(1)

# B01: o próprio hóspede confirma a reserva chamando o webhook, sem pagar
rid = reserva(1, 1, 10, 12)
resp = webhook(gerar_pix(rid))
status = consulta("SELECT status FROM reserva WHERE id = ?", rid)[0]["status"]
registrar(problemas, "B01", "Webhook PIX sem autenticação: o hóspede confirma a própria reserva sem pagar",
          resp.status_code == 200 and status == "CONFIRMADA", f"HTTP {resp.status_code}, reserva {status}")

# B02: pagamento duplicado sem reembolso
rid = reserva(1, 1, 20, 22)
cobranca = gerar_pix(rid)
cliente.post("/api/pagamento/cartao", json={**CARTAO_OK, "reserva_id": rid})
webhook(cobranca)
aprovados = consulta("SELECT COUNT(*) AS n FROM pagamento WHERE reserva_id = ? AND status = 'APROVADO'", rid)[0]["n"]
registrar(problemas, "B02", "Cartão aprovado e depois PIX da mesma reserva: dois pagamentos, nenhum reembolso",
          aprovados == 2, f"{aprovados} pagamentos APROVADO na mesma reserva")

# B03: PIX pago depois do prazo ressuscita a reserva cancelada e gera reserva dupla
rid_antiga = reserva(1, 1, 30, 33)
cobranca = gerar_pix(rid_antiga)
envelhecer(rid_antiga, 31)
models.expirar_reservas_pendentes()
rid_nova = reserva(2, 1, 31, 32)
logar(2)
cliente.post("/api/pagamento/cartao", json={**CARTAO_OK, "reserva_id": rid_nova})
logar(1)
webhook(cobranca)
confirmadas = consulta("SELECT id FROM reserva WHERE acomodacao_id = 1 AND status = 'CONFIRMADA' "
                       "AND id IN (?, ?)", rid_antiga, rid_nova)
registrar(problemas, "B03", "PIX pago após os 30 min reativa a reserva cancelada: dois hóspedes no mesmo período",
          len(confirmadas) == 2, f"reservas confirmadas no mesmo período: {[c['id'] for c in confirmadas]}")

# B04: a rota de desenvolvimento deixa qualquer visitante virar outro usuário
rid = reserva(1, 1, 40, 42)
cliente.post("/api/pagamento/cartao", json={**CARTAO_OK, "reserva_id": rid})
invasor = app.test_client()
invasor.post("/api/dev/switch-user", data={"usuario_id": "1"})
html = invasor.get(f"/confirmacao/{rid}").get_data(as_text=True)
registrar(problemas, "B04", "Visitante usa /api/dev/switch-user, vira o hóspede 1 e vê o endereço completo",
          cep in html, "rota ativa sem restrição; CEP exibido" if cep in html else "bloqueado")

# B05: outro usuário gera PIX e consulta o status de reserva alheia
rid = reserva(1, 1, 50, 52)
logar(2)
r_pix = cliente.post("/api/pagamento/pix/gerar", json={"reserva_id": rid})
r_status = cliente.get(f"/api/reservas/{rid}/status")
logar(1)
registrar(problemas, "B05", "Usuário 2 gera cobrança PIX e consulta o status da reserva do usuário 1",
          r_pix.status_code == 200 and r_status.status_code == 200,
          f"gerar PIX: HTTP {r_pix.status_code}, status: HTTP {r_status.status_code}")

# B06: reserva com check-in no passado
try:
    rid = models.criar_reserva(1, 1, dia(-10), dia(-8), 1)["reserva_id"]
    criada = True
except ValueError:
    criada = False
registrar(problemas, "B06", "Reserva criada com check-in 10 dias no passado", criada,
          "aceita" if criada else "recusada")

# B07: entradas malformadas derrubam a requisição com erro 500
codigos = (
    cliente.post("/resumo", data={"check_in": dia(1), "check_out": dia(2), "num_hospedes": "1"}).status_code,
    cliente.get("/resumo?acomodacao_id=abc").status_code,
    cliente.post("/api/pagamento/cartao", json={**CARTAO_OK, "reserva_id": "x"}).status_code,
)
registrar(problemas, "B07", "Formulário sem acomodação, id não numérico e reserva_id inválido geram erro 500",
          codigos == (500, 500, 500), f"HTTP {codigos}")

# B08: o mesmo aviso de PIX processado duas vezes reenviando e-mails
rid = reserva(1, 1, 60, 62)
cobranca = gerar_pix(rid)
EmailService.clear()
webhook(cobranca)
segundo = webhook(cobranca)
enviados = len(EmailService.get_sent_emails())
registrar(problemas, "B08", "Webhook repetido é aceito de novo e reenvia os e-mails de confirmação",
          segundo.status_code == 200 and enviados == 4, f"2º aviso: HTTP {segundo.status_code}, {enviados} e-mails")

# Rodada 1 x rodada 2
rid = reserva(1, 1, 70, 74)
envelhecer(rid, 60 * 48)
try:
    models.criar_reserva(2, 1, dia(71), dia(73), 1)
    liberou = True
except ValueError:
    liberou = False
registrar(correcoes, "A05", "Reserva expirada deixa de bloquear as datas", liberou, "datas liberadas" if liberou else "bloqueadas")

try:
    models.criar_reserva(1, 1, dia(80), dia(81), 0)
    zero = True
except ValueError:
    zero = False
registrar(correcoes, "A06", "Reserva com 0 hóspedes é recusada (check-in no passado continua aceito: B06)",
          not zero, "recusada" if not zero else "aceita")

rid = reserva(1, 1, 90, 92)
cliente.post("/api/pagamento/cartao", json={**CARTAO_OK, "reserva_id": rid})
logar(2)
bloqueou = cep not in cliente.get(f"/confirmacao/{rid}").get_data(as_text=True)
logar(1)
registrar(correcoes, "A03", "Confirmação recusa outro usuário logado (mas veja B04 e B05)", bloqueou,
          "bloqueado" if bloqueou else "endereço exibido")

entidades = {"reserva": consulta("SELECT COUNT(*) AS n FROM historico_status_reserva")[0]["n"],
             "pagamento": consulta("SELECT COUNT(*) AS n FROM historico_status_pagamento")[0]["n"]}
registrar(correcoes, "A08", "Mudanças de status de reserva e de pagamento são auditadas",
          all(entidades.values()), f"registros de histórico: {entidades}")

rid = reserva(1, 1, 100, 102)
EmailService.clear()
cliente.post("/api/pagamento/cartao", json={**CARTAO_OK, "reserva_id": rid})
destinos = sorted({e["destinatario"] for e in EmailService.get_sent_emails()})
registrar(correcoes, "A11", "Hóspede e anfitrião recebem e-mail", len(destinos) == 2, f"destinatários: {destinos}")

svg = gerar_pix(reserva(1, 1, 110, 112)).get("qrCodeSvg", "")
registrar(correcoes, "A12", "QR Code do PIX gerado localmente, sem serviço externo",
          svg.startswith("<svg"), "SVG local" if svg.startswith("<svg") else "externo")

colunas = {c["name"] for c in consulta("PRAGMA table_info(usuario)")}
tabelas = {t["name"] for t in consulta("SELECT name FROM sqlite_master WHERE type = 'table'")}
registrar(correcoes, "A13", "Banco segue o B.4 da ERS v1.2 (superhost no usuário e tabelas de histórico)",
          "superhost" in colunas and {"historico_status_reserva", "historico_status_pagamento"} <= tabelas, "")

for titulo, lista, ok, nok in (("PROBLEMAS DA RODADA 2", problemas, "CONFIRMADO", "não reproduzido"),
                               ("CORREÇÕES EM RELAÇÃO À RODADA 1", correcoes, "CORRIGIDO", "persiste")):
    print(f"\n{titulo}")
    for codigo, descricao, confirmado, detalhe in lista:
        print(f"[{(ok if confirmado else nok):>15}] {codigo} {descricao}")
        if detalhe:
            print(f"{'':18}{detalhe}")
print(f"\n{sum(p[2] for p in problemas)} de {len(problemas)} problemas reproduzidos; "
      f"{sum(c[2] for c in correcoes)} de {len(correcoes)} correções confirmadas.")
