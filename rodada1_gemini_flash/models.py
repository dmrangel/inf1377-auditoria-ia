from datetime import datetime, timezone
from database import get_db

def registrar_auditoria(conn, entidade, entidade_id, status_anterior, status_novo, responsavel="SISTEMA"):
    """Atende a RNF-22: auditoria de status com data, hora e responsável"""
    conn.execute("""
        INSERT INTO auditoria (entidade, entidade_id, status_anterior, status_novo, responsavel)
        VALUES (?, ?, ?, ?, ?)
    """, (entidade, entidade_id, status_anterior, status_novo, responsavel))

def verificar_expiracao_reserva(reserva_id):
    """Atende a RN-04: cancelamento automático de reserva pendente após 30 min"""
    conn = get_db()
    reserva = conn.execute("SELECT * FROM reserva WHERE id = ?", (reserva_id,)).fetchone()
    if reserva and reserva['status'] == 'PENDENTE':
        criado_str = str(reserva['criadoEm']).split('.')[0]
        try:
            criado = datetime.strptime(criado_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            criado = datetime.fromisoformat(criado_str)
        
        agora_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        if (agora_utc - criado).total_seconds() > 1800:
            conn.execute("UPDATE reserva SET status = 'CANCELADA' WHERE id = ?", (reserva_id,))
            registrar_auditoria(conn, 'reserva', reserva_id, 'PENDENTE', 'CANCELADA', 'SISTEMA_TIMEOUT_RN04')
            conn.commit()
    conn.close()

def calcular_valores(preco_noite, noites, eh_superhost):
    """
    Atende a:
    - RN-03: taxa de serviço de 14% sobre as diárias
    - RN-07 / RF-18 / RF-33: desconto de 10% na taxa de serviço se for Superhost
    """
    subtotal = preco_noite * noites
    taxa_servico = subtotal * 0.14
    desconto_superhost = (taxa_servico * 0.10) if eh_superhost else 0.0
    valor_total = subtotal + taxa_servico - desconto_superhost
    return {
        "subtotal": round(subtotal, 2),
        "taxa_servico": round(taxa_servico, 2),
        "taxaServico": round(taxa_servico, 2),
        "desconto_superhost": round(desconto_superhost, 2),
        "descontoSuperhost": round(desconto_superhost, 2),
        "valor_total": round(valor_total, 2),
        "valorTotal": round(valor_total, 2)
    }

def validar_disponibilidade(conn, acomodacao_id, checkin, checkout):
    """Atende a RF-19: impede sobreposição de reservas ativas para a mesma acomodação"""
    query = """
    SELECT COUNT(*) FROM reserva
    WHERE acomodacao_id = ?
      AND status IN ('PENDENTE', 'CONFIRMADA')
      AND NOT (checkOut <= ? OR checkin >= ?)
    """
    count = conn.execute(query, (acomodacao_id, checkin, checkout)).fetchone()[0]
    return count == 0
