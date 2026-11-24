"""
cancelamento.py - Regras de negócio do cancelamento de reserva e do reembolso
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
Conforme ERS v1.2: RF-21, RF-25, RF-27, Seção 4.4.2 (sequência 4), Seção 4.5.1,
RN-05, UC12 (Cancelar reserva), RNF-11, RNF-19 e RNF-22.

As decisões tomadas onde a ERS é ambígua estão no README (seção "Ambiguidades e
decisões do cancelamento", itens AMB-01 a AMB-14) e são citadas nos comentários.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

import models
from database import get_db_connection
from services.payment_gateway import PaymentGateway, GatewayIndisponivelError
from services.email_service import EmailService


# ---------------------------------------------------------------------------
# Parâmetros da política (RN-05)
# ---------------------------------------------------------------------------

# AMB-01: a ERS guarda o check-in só como data. O prazo de 48 h é contado a partir
# das 14:00 do dia do check-in, o mesmo horário que a tela de confirmação já mostra
# ao hóspede ("Check-in a partir das 14:00"). O check-out segue o mesmo raciocínio (11:00).
HORA_CHECKIN = time(14, 0)
HORA_CHECKOUT = time(11, 0)

# RN-05: "até 48 horas antes do check-in gera reembolso integral" (inclusive: exatamente 48 h ainda é integral)
ANTECEDENCIA_REEMBOLSO_INTEGRAL = timedelta(hours=48)

# RN-05: "depois disso, reembolso de 50% das diárias" (AMB-02: a taxa de serviço não entra nos 50%)
PERCENTUAL_DIARIAS_CANCELAMENTO_TARDIO = Decimal("0.50")

# UC12, pré-condição: "Reserva está PENDENTE ou CONFIRMADA"
STATUS_CANCELAVEIS = ("PENDENTE", "CONFIRMADA")

PAPEL_HOSPEDE = "HOSPEDE"
PAPEL_ANFITRIAO = "ANFITRIAO"

REGRA_SEM_PAGAMENTO = "SEM_PAGAMENTO"
REGRA_ANFITRIAO_INTEGRAL = "ANFITRIAO_INTEGRAL"
REGRA_HOSPEDE_INTEGRAL = "HOSPEDE_INTEGRAL"
REGRA_HOSPEDE_PARCIAL = "HOSPEDE_PARCIAL"


class CancelamentoErro(Exception):
    """Erro de regra de negócio do cancelamento, com mensagem em linguagem simples (Seção 3.1)."""

    def __init__(self, mensagem: str, http_status: int = 400, codigo: str = "ERRO",
                 dados: Optional[Dict[str, Any]] = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.http_status = http_status
        self.codigo = codigo
        self.dados = dados or {}


# ---------------------------------------------------------------------------
# Funções puras (sem banco): datas, papel do usuário e cálculo do reembolso
# ---------------------------------------------------------------------------

def _dinheiro(valor) -> Decimal:
    """Arredonda valores monetários para centavos, metade para cima."""
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def instante_checkin(check_in_str: str) -> datetime:
    """Data do check-in + HORA_CHECKIN (AMB-01)."""
    return datetime.combine(datetime.strptime(check_in_str, "%Y-%m-%d").date(), HORA_CHECKIN)


def instante_checkout(check_out_str: str) -> datetime:
    """Data do check-out + HORA_CHECKOUT (AMB-01 e AMB-05)."""
    return datetime.combine(datetime.strptime(check_out_str, "%Y-%m-%d").date(), HORA_CHECKOUT)


def papel_do_usuario(reserva: Dict[str, Any], usuario_id: Optional[int]) -> Optional[str]:
    """
    RF-21 e RNF-11: só o hóspede da reserva ou o anfitrião dono da acomodação podem cancelar.
    AMB-11: se a mesma pessoa for as duas coisas, vale o papel de hóspede (a regra menos favorável).
    """
    if not usuario_id or not reserva:
        return None
    if reserva["hospede_id"] == usuario_id:
        return PAPEL_HOSPEDE
    if reserva["anfitriao_id"] == usuario_id:
        return PAPEL_ANFITRIAO
    return None


def calcular_reembolso(papel: str, check_in_str: str, valor_pago, valor_diarias,
                       agora: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Política de reembolso (RN-05, UC12 passo 2 e fluxo alternativo 2a, RF-27).

    - Sem pagamento aprovado (ex.: reserva PENDENTE): nada a reembolsar.
    - Anfitrião cancela: reembolso integral ao hóspede, em qualquer momento (UC12 2a).
    - Hóspede cancela com 48 h ou mais de antecedência: reembolso integral do valor pago (AMB-02).
    - Hóspede cancela com menos de 48 h (inclusive durante a estadia, AMB-05):
      50% das diárias; a taxa de serviço não é devolvida (AMB-02).
    O reembolso nunca passa do valor efetivamente pago.
    """
    agora = agora or datetime.now()
    pago = _dinheiro(valor_pago or 0)
    diarias = _dinheiro(valor_diarias or 0)
    checkin = instante_checkin(check_in_str)
    antecedencia = checkin - agora
    prazo_integral = checkin - ANTECEDENCIA_REEMBOLSO_INTEGRAL

    if pago <= 0:
        regra = REGRA_SEM_PAGAMENTO
        valor = Decimal("0.00")
        referencia = "UC12 / RF-27"
        descricao = "A reserva não tem pagamento aprovado, então não há valor a reembolsar."
    elif papel == PAPEL_ANFITRIAO:
        regra = REGRA_ANFITRIAO_INTEGRAL
        valor = pago
        referencia = "UC12, fluxo 2a"
        descricao = "Cancelamento feito pelo anfitrião: o hóspede recebe de volta todo o valor pago."
    elif antecedencia >= ANTECEDENCIA_REEMBOLSO_INTEGRAL:
        regra = REGRA_HOSPEDE_INTEGRAL
        valor = pago
        referencia = "RN-05"
        descricao = ("Cancelamento pelo hóspede com 48 horas ou mais de antecedência do check-in: "
                     "reembolso integral do valor pago.")
    else:
        regra = REGRA_HOSPEDE_PARCIAL
        valor = min(_dinheiro(diarias * PERCENTUAL_DIARIAS_CANCELAMENTO_TARDIO), pago)
        referencia = "RN-05"
        descricao = ("Cancelamento pelo hóspede com menos de 48 horas de antecedência do check-in: "
                     "reembolso de 50% das diárias. A taxa de serviço não é devolvida.")

    return {
        "regra": regra,
        "referencia": referencia,
        "descricao_regra": descricao,
        "papel": papel,
        "valor_pago": float(pago),
        "valor_diarias": float(diarias),
        "valor_reembolso": float(valor),
        "valor_retido": float(pago - valor),
        "reembolso_integral": valor == pago and pago > 0,
        "instante_checkin": checkin.isoformat(),
        "prazo_reembolso_integral": prazo_integral.isoformat(),
        "horas_ate_checkin": round(antecedencia.total_seconds() / 3600, 1),
        "calculado_em": agora.isoformat(),
    }


def verificar_pode_cancelar(reserva: Optional[Dict[str, Any]], usuario_id: Optional[int],
                            agora: Optional[datetime] = None) -> str:
    """Pré-condições do UC12 verificadas no servidor. Devolve o papel de quem cancela."""
    agora = agora or datetime.now()
    if not reserva:
        raise CancelamentoErro("Reserva não encontrada.", 404, "RESERVA_NAO_ENCONTRADA")

    papel = papel_do_usuario(reserva, usuario_id)
    if papel is None:
        raise CancelamentoErro(
            "Você não tem permissão para cancelar esta reserva. Só o hóspede da reserva "
            "ou o anfitrião da acomodação podem cancelá-la (RF-21, RNF-11).",
            403, "SEM_PERMISSAO")

    if reserva["status"] not in STATUS_CANCELAVEIS:
        raise CancelamentoErro(
            f"Esta reserva está {reserva['status']} e não pode ser cancelada. "
            "Só reservas pendentes ou confirmadas podem ser canceladas (UC12).",
            409, "STATUS_NAO_CANCELAVEL")

    # AMB-05: depois do check-out a reserva deveria estar CONCLUIDA (Seção 4.4.2, sequência 3),
    # mesmo que a transição automática ainda não tenha rodado.
    if agora >= instante_checkout(reserva["checkOut"]):
        raise CancelamentoErro(
            f"A estadia desta reserva já terminou (check-out em {reserva['checkOut']}). "
            "Ela não pode mais ser cancelada.",
            409, "ESTADIA_ENCERRADA")

    return papel


# ---------------------------------------------------------------------------
# Acesso ao banco
# ---------------------------------------------------------------------------

def _carregar_reserva(conn, reserva_id: int) -> Optional[Dict[str, Any]]:
    """Lê a reserva, a acomodação, as partes e os pagamentos na conexão informada."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*,
               a.titulo AS acomodacao_titulo, a.precoNoite AS acomodacao_precoNoite,
               a.anfitriao_id AS anfitriao_id,
               h.nome AS hospede_nome, h.email AS hospede_email,
               anf.nome AS anfitriao_nome, anf.email AS anfitriao_email,
               anf.superhost AS anfitriao_superhost
        FROM reserva r
        JOIN acomodacao a ON r.acomodacao_id = a.id
        JOIN usuario h ON r.hospede_id = h.id
        JOIN usuario anf ON a.anfitriao_id = anf.id
        WHERE r.id = ?;
    """, (reserva_id,))
    row = cursor.fetchone()
    if not row:
        return None
    reserva = dict(row)
    cursor.execute("""
        SELECT id, txid, metodo, valor, codigoAutorizacao, status, dataHora
        FROM pagamento WHERE reserva_id = ? ORDER BY id ASC;
    """, (reserva_id,))
    reserva["pagamentos"] = [dict(p) for p in cursor.fetchall()]
    return reserva


def _pagamento_a_reembolsar(reserva: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    O pagamento aprovado mais recente é o que confirmou a reserva e é o que será estornado
    (mesmo critério de models.obter_reserva_completa). Ver AMB-08 sobre pagamentos duplicados.
    """
    return next((p for p in reversed(reserva["pagamentos"]) if p["status"] == "APROVADO"), None)


def _valor_diarias(reserva: Dict[str, Any]) -> float:
    """
    AMB-09: a tabela reserva (B.4) guarda só o valorTotal. O valor das diárias é recalculado
    como noites x preço por noite, a mesma conta que o fluxo de reserva usa nas telas.
    """
    calculos = models.calcular_valores_estadia(
        reserva["acomodacao_precoNoite"], reserva["checkIn"], reserva["checkOut"],
        bool(reserva["anfitriao_superhost"])
    )
    return calculos["subtotal_diarias"]


def _montar_previa(reserva: Dict[str, Any], usuario_id: int, agora: datetime) -> Dict[str, Any]:
    papel = verificar_pode_cancelar(reserva, usuario_id, agora)
    pagamento = _pagamento_a_reembolsar(reserva)
    reembolso = calcular_reembolso(
        papel=papel,
        check_in_str=reserva["checkIn"],
        valor_pago=pagamento["valor"] if pagamento else 0,
        valor_diarias=_valor_diarias(reserva),
        agora=agora,
    )
    reembolso["txid_original"] = pagamento["txid"] if pagamento else None
    reembolso["metodo_original"] = pagamento["metodo"] if pagamento else None
    return {
        "reserva_id": reserva["id"],
        "status_atual": reserva["status"],
        "papel": papel,
        "outra_parte": "anfitrião" if papel == PAPEL_HOSPEDE else "hóspede",
        "reembolso": reembolso,
        "pagamento_original": pagamento,
    }


# ---------------------------------------------------------------------------
# UC12 passos 1 e 2: prévia do cancelamento
# ---------------------------------------------------------------------------

def obter_previa_cancelamento(reserva_id: int, usuario_id: int,
                              agora: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Mostra o valor de reembolso conforme a política, sem alterar nada (UC12 passo 2).
    Levanta CancelamentoErro se a reserva não puder ser cancelada por esse usuário.
    """
    agora = agora or datetime.now()
    models.expirar_reservas_pendentes()  # RN-04: uma PENDENTE vencida já não é cancelável
    conn = get_db_connection()
    try:
        return _montar_previa(_carregar_reserva(conn, reserva_id), usuario_id, agora)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# UC12 passos 3 a 5: confirmação, cancelamento, reembolso e notificação
# ---------------------------------------------------------------------------

def cancelar_reserva(reserva_id: int, usuario_id: int, valor_exibido: Optional[float] = None,
                     agora: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Cancela a reserva (RF-21, Seção 4.4.2 seq. 4), solicita e registra o reembolso (RF-27,
    Seção 4.5.1, RF-25) e notifica a outra parte (UC12 passo 5).

    Tudo acontece numa única transação com BEGIN IMMEDIATE, para que dois cancelamentos
    simultâneos da mesma reserva não gerem dois reembolsos.

    AMB-07: se o gateway recusar ou não responder, nada é alterado: a reserva continua
    como estava e o usuário pode tentar de novo. Nunca fica uma reserva CANCELADA sem o
    reembolso devido.

    AMB-12: `valor_exibido` é o reembolso que a tela mostrou no passo 2. Se o valor mudou
    até a confirmação (ex.: o prazo de 48 h venceu nesse meio-tempo), o cancelamento é
    interrompido e o novo valor é devolvido para o usuário confirmar de novo.
    """
    agora = agora or datetime.now()
    models.expirar_reservas_pendentes()  # RN-04 antes de decidir

    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        reserva = _carregar_reserva(conn, reserva_id)
        previa = _montar_previa(reserva, usuario_id, agora)
        papel = previa["papel"]
        reembolso = previa["reembolso"]
        pagamento_original = previa["pagamento_original"]
        valor_reembolso = reembolso["valor_reembolso"]

        if valor_exibido is not None and abs(float(valor_exibido) - valor_reembolso) > 0.005:
            raise CancelamentoErro(
                f"O valor do reembolso mudou desde que a tela foi aberta: agora é R$ {valor_reembolso:.2f}. "
                "Nada foi cancelado. Confira o novo valor e confirme de novo se quiser continuar.",
                409, "VALOR_ALTERADO", dados=previa)

        # UC12 passo 4 (parte 1): solicitar o reembolso ao gateway, quando houver valor devido
        resposta_gateway = None
        if valor_reembolso > 0:
            try:
                resposta_gateway = PaymentGateway.process_refund(
                    txid=pagamento_original["txid"],
                    amount=valor_reembolso,
                    reservation_id=reserva_id,
                    idempotency_key=f"cancelamento-reserva-{reserva_id}",
                )
            except GatewayIndisponivelError:
                raise CancelamentoErro(
                    "O serviço de pagamento não respondeu e o reembolso não pôde ser solicitado. "
                    f"Nada foi alterado: a reserva continua {reserva['status']}. Tente de novo em alguns minutos.",
                    503, "GATEWAY_INDISPONIVEL")
            if not resposta_gateway.get("sucesso"):
                raise CancelamentoErro(
                    f"O serviço de pagamento recusou o reembolso ({(resposta_gateway.get('motivo') or '').rstrip('.')}). "
                    f"Nada foi alterado: a reserva continua {reserva['status']}. "
                    "Tente de novo mais tarde ou procure o suporte.",
                    502, "REEMBOLSO_RECUSADO")

        now_iso = datetime.now().isoformat()
        cursor = conn.cursor()

        # UC12 passo 4 (parte 2): reserva passa para CANCELADA (Seção 4.4.2 seq. 4, RF-20)
        cursor.execute("""
            UPDATE reserva SET status = 'CANCELADA'
            WHERE id = ? AND status IN ('PENDENTE', 'CONFIRMADA');
        """, (reserva_id,))
        if cursor.rowcount != 1:  # proteção extra; com o BEGIN IMMEDIATE não deveria ocorrer
            raise CancelamentoErro("A reserva mudou de status durante o cancelamento. Recarregue a página.",
                                   409, "CONCORRENCIA")

        # RNF-22: histórico com data, hora e responsável (quem cancelou)
        cursor.execute("""
            INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora, responsavel_id)
            VALUES (?, ?, 'CANCELADA', ?, ?);
        """, (reserva_id, reserva["status"], now_iso, usuario_id))

        # Seção 4.5.1 e RF-25 (AMB-03): o reembolso é registrado como um novo pagamento da reserva,
        # com status REEMBOLSADO. O pagamento original continua APROVADO e nada é apagado (RNF-19).
        pagamento_reembolso = None
        if resposta_gateway:
            cursor.execute("""
                INSERT INTO pagamento (reserva_id, txid, metodo, valor, codigoAutorizacao, status, dataHora, tokenCartao)
                VALUES (?, ?, ?, ?, ?, 'REEMBOLSADO', ?, NULL);
            """, (reserva_id, resposta_gateway["refund_id"], pagamento_original["metodo"],
                  valor_reembolso, resposta_gateway["codigoAutorizacao"], resposta_gateway["dataHora"]))
            pagamento_reembolso_id = cursor.lastrowid
            # AMB-10: o responsável é quem pediu o cancelamento (mesmo critério do pagamento por cartão)
            cursor.execute("""
                INSERT INTO historico_status_pagamento (pagamento_id, statusAnterior, statusNovo, dataHora, responsavel_id)
                VALUES (?, NULL, 'REEMBOLSADO', ?, ?);
            """, (pagamento_reembolso_id, now_iso, usuario_id))
            pagamento_reembolso = {
                "id": pagamento_reembolso_id,
                "txid": resposta_gateway["refund_id"],
                "metodo": pagamento_original["metodo"],
                "valor": valor_reembolso,
                "codigoAutorizacao": resposta_gateway["codigoAutorizacao"],
                "status": "REEMBOLSADO",
                "dataHora": resposta_gateway["dataHora"],
            }

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # UC12 passo 5: notificar a outra parte. Fica fora da transação: uma falha no e-mail
    # não desfaz um cancelamento e um reembolso já feitos; ela é registrada no resultado.
    resultado = {
        "reserva_id": reserva_id,
        "status_anterior": reserva["status"],
        "status": "CANCELADA",
        "cancelado_por": papel,
        "responsavel_id": usuario_id,
        "reembolso": reembolso,
        "pagamento_reembolso": pagamento_reembolso,
        "notificacoes": [],
    }
    try:
        enviados = EmailService.send_reservation_cancelled(
            reserva=reserva, cancelado_por=papel, reembolso=reembolso,
            pagamento_reembolso=pagamento_reembolso)
        resultado["notificacoes"] = [{"destinatario": e["destinatario"], "tipo": e["tipo"]} for e in enviados]
    except Exception as exc:  # pragma: no cover - o serviço simulado não falha
        print(f"[cancelamento] Falha ao notificar o cancelamento da reserva #{reserva_id}: {exc}")
        resultado["erro_notificacao"] = str(exc)
    return resultado


def mensagem_resultado(resultado: Dict[str, Any]) -> str:
    """Resumo em linguagem simples do cancelamento concluído (usado na tela e na API)."""
    partes = [f"Reserva #{resultado['reserva_id']} cancelada."]
    if resultado["pagamento_reembolso"]:
        partes.append(
            f"Reembolso de R$ {resultado['reembolso']['valor_reembolso']:.2f} solicitado ao serviço de "
            f"pagamento e registrado (identificador {resultado['pagamento_reembolso']['txid']}).")
    else:
        partes.append("Não havia pagamento aprovado, então não há reembolso.")
    outra = "O anfitrião" if resultado["cancelado_por"] == PAPEL_HOSPEDE else "O hóspede"
    partes.append(f"{outra} foi notificado por e-mail.")
    return " ".join(partes)


# ---------------------------------------------------------------------------
# Consultas para as telas (ponto de entrada do UC12)
# ---------------------------------------------------------------------------

def listar_reservas_do_usuario(usuario_id: int, agora: Optional[datetime] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Lista mínima para o usuário abrir uma reserva (UC12 passo 1): as que ele fez como
    hóspede e as recebidas nas acomodações dele (RNF-11: só as do próprio anfitrião).
    Não implementa o RF-22 nem o RF-11 por completo (filtros, paginação etc.).
    """
    agora = agora or datetime.now()
    models.expirar_reservas_pendentes()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        base = """
            SELECT r.id, r.checkIn, r.checkOut, r.numHospedes, r.valorTotal, r.status,
                   a.titulo AS acomodacao_titulo, a.bairro AS acomodacao_bairro, a.cidade AS acomodacao_cidade,
                   h.nome AS hospede_nome, anf.nome AS anfitriao_nome
            FROM reserva r
            JOIN acomodacao a ON r.acomodacao_id = a.id
            JOIN usuario h ON r.hospede_id = h.id
            JOIN usuario anf ON a.anfitriao_id = anf.id
        """
        cursor.execute(base + " WHERE r.hospede_id = ? ORDER BY r.checkIn ASC;", (usuario_id,))
        como_hospede = [dict(r) for r in cursor.fetchall()]
        cursor.execute(base + " WHERE a.anfitriao_id = ? ORDER BY r.checkIn ASC;", (usuario_id,))
        como_anfitriao = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    for r in como_hospede + como_anfitriao:
        r["pode_cancelar"] = r["status"] in STATUS_CANCELAVEIS and agora < instante_checkout(r["checkOut"])
    return {"como_hospede": como_hospede, "como_anfitriao": como_anfitriao}


def listar_historico_reserva(reserva_id: int) -> List[Dict[str, Any]]:
    """Histórico de status da reserva (RNF-22), com o nome do responsável."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hsr.statusAnterior, hsr.statusNovo, hsr.dataHora, u.nome AS responsavel_nome
            FROM historico_status_reserva hsr
            LEFT JOIN usuario u ON hsr.responsavel_id = u.id
            WHERE hsr.reserva_id = ?
            ORDER BY hsr.id ASC;
        """, (reserva_id,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
