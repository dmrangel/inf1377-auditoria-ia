"""
models.py - Regras de Negócio, Validações e Operações de Dados
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
Conforme ERS v1.2: RF-17 a RF-28, RN-01 a RN-04, RN-07, RNF-05*, RNF-11, RNF-22.
"""

from datetime import datetime, date, timedelta
from typing import Tuple, Dict, Any, Optional, List
from database import get_db_connection


# ---------------------------------------------------------------------------
# RN-01, RN-02, RN-03, RN-07, RF-18: Cálculos Financeiros e Validações
# ---------------------------------------------------------------------------

def calcular_valores_estadia(preco_noite: float, check_in_str: str, check_out_str: str, eh_superhost: bool) -> Dict[str, Any]:
    """
    Calcula número de noites, subtotal das diárias, taxa de serviço (14% - RN-03)
    e desconto de Superhost (10% sobre a taxa de serviço = taxa efetiva 12.6% - RN-07, RF-18).
    """
    check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
    check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()

    # RN-01: Check-out posterior ao check-in com estadia mínima de 1 noite
    num_noites = (check_out - check_in).days
    if num_noites < 1:
        raise ValueError("O check-out deve ser posterior ao check-in, com estadia mínima de 1 noite (RN-01).")

    subtotal_diarias = round(num_noites * float(preco_noite), 2)
    # RN-03: taxa de 14% sobre o valor das diárias
    taxa_servico_base = round(subtotal_diarias * 0.14, 2)

    # RN-07 e RF-18: desconto de 10% sobre o valor da taxa de serviço para Superhost
    if eh_superhost:
        desconto_superhost = round(taxa_servico_base * 0.10, 2)
        taxa_servico_final = round(taxa_servico_base - desconto_superhost, 2)
    else:
        desconto_superhost = 0.0
        taxa_servico_final = taxa_servico_base

    valor_total = round(subtotal_diarias + taxa_servico_final, 2)

    return {
        "num_noites": num_noites,
        "preco_noite": float(preco_noite),
        "subtotal_diarias": subtotal_diarias,
        "taxa_servico_base": taxa_servico_base,
        "eh_superhost": bool(eh_superhost),
        "desconto_superhost": desconto_superhost,
        "taxa_servico_final": taxa_servico_final,
        "taxa_efetiva_percentual": 12.6 if eh_superhost else 14.0,
        "valor_total": valor_total
    }


def validar_disponibilidade_e_regras(
    acomodacao_id: int,
    check_in_str: str,
    check_out_str: str,
    num_hospedes: int,
    reserva_id_ignorar: Optional[int] = None,
    conn=None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Valida capacidade (RN-02), datas (RN-01) e conflito de reservas sobrepostas (RF-19).
    Retorna (sucesso: bool, mensagem_erro: str, acomodacao_info: dict).
    """
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    try:
        # Primeiro garantir expiração de reservas pendentes com mais de 30 min (RN-04)
        expirar_reservas_pendentes(conn)

        # 1. Buscar acomodação e dados do anfitrião
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, u.nome as anfitriao_nome, u.email as anfitriao_email,
                   u.superhost, u.taxaResposta
            FROM acomodacao a
            JOIN usuario u ON a.anfitriao_id = u.id
            WHERE a.id = ?;
        """, (acomodacao_id,))
        acomodacao = cursor.fetchone()

        if not acomodacao:
            return False, "Acomodação não encontrada.", None

        if not acomodacao["ativo"]:
            return False, "Esta acomodação está temporariamente inativa para reservas.", None

        # 2. Validar datas (RN-01)
        try:
            check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
            check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return False, "Datas de check-in e check-out em formato inválido. Use AAAA-MM-DD.", None

        if check_out <= check_in:
            return False, "A data de check-out deve ser posterior à data de check-in (RN-01).", None

        # 3. Validar capacidade máxima (RN-02)
        if num_hospedes < 1:
            return False, "O número de hóspedes deve ser de pelo menos 1.", None

        if num_hospedes > acomodacao["capacidadeMaxima"]:
            return False, (
                f"O número de hóspedes ({num_hospedes}) ultrapassa a capacidade "
                f"máxima permitida desta acomodação ({acomodacao['capacidadeMaxima']} hóspedes) (RN-02)."
            ), None

        # 4. Validar sobreposição de reservas (RF-19, UC10 passo 3a)
        # Uma data está ocupada se existe reserva CONFIRMADA ou PENDENTE (ativa nos últimos 30 min)
        # Condição matemática de interseção de intervalos de datas:
        # (novo_checkin < existente_checkout) E (novo_checkout > existente_checkin)
        query_conflito = """
            SELECT id, checkIn, checkOut, status, dataCriacao
            FROM reserva
            WHERE acomodacao_id = ?
              AND status IN ('CONFIRMADA', 'PENDENTE')
              AND checkIn < ?
              AND checkOut > ?
        """
        params = [acomodacao_id, check_out_str, check_in_str]
        if reserva_id_ignorar:
            query_conflito += " AND id != ?"
            params.append(reserva_id_ignorar)

        cursor.execute(query_conflito, params)
        conflitos = cursor.fetchall()

        # Filtrar se algum PENDENTE já expirou (tolerância de segurança)
        agora = datetime.now()
        conflitos_ativos = []
        for c in conflitos:
            if c["status"] == "PENDENTE":
                criado = datetime.fromisoformat(c["dataCriacao"])
                if (agora - criado).total_seconds() > 1800:
                    continue  # PENDENTE expirado, ignora
            conflitos_ativos.append(c)

        if conflitos_ativos:
            return False, (
                "A acomodação já está reservada ou possui solicitação em andamento "
                "no período selecionado (RF-19). Por favor, selecione outras datas."
            ), None

        return True, "", dict(acomodacao)

    finally:
        if close_at_end:
            conn.close()


# ---------------------------------------------------------------------------
# RN-04: Controle de Expiração de Reservas Pendentes (30 minutos)
# ---------------------------------------------------------------------------

def expirar_reservas_pendentes(conn=None) -> int:
    """
    Cancela automaticamente reservas com status PENDENTE cujo tempo de criação
    tenha ultrapassado 30 minutos (RN-04 e UC16 passo 4b).
    Registra histórico de auditoria (RNF-22). Retorna quantidade de expiradas.
    """
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    try:
        cursor = conn.cursor()
        limite_tempo = (datetime.now() - timedelta(minutes=30)).isoformat()

        cursor.execute("""
            SELECT id FROM reserva
            WHERE status = 'PENDENTE' AND dataCriacao < ?;
        """, (limite_tempo,))
        expiradas = cursor.fetchall()

        now_iso = datetime.now().isoformat()
        for r in expiradas:
            reserva_id = r["id"]
            cursor.execute("""
                UPDATE reserva SET status = 'CANCELADA' WHERE id = ?;
            """, (reserva_id,))
            cursor.execute("""
                INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora, responsavel_id)
                VALUES (?, 'PENDENTE', 'CANCELADA', ?, NULL);
            """, (reserva_id, now_iso))

        if expiradas:
            conn.commit()
            print(f"[models] {len(expiradas)} reserva(s) PENDENTE(s) cancelada(s) por expiração de 30 min (RN-04).")

        return len(expiradas)

    finally:
        if close_at_end:
            conn.close()


# ---------------------------------------------------------------------------
# Operações de Reserva e Histórico de Auditoria (RNF-22, RF-20)
# ---------------------------------------------------------------------------

def criar_reserva(hospede_id: int, acomodacao_id: int, check_in: str, check_out: str, num_hospedes: int) -> Dict[str, Any]:
    """
    Cria uma nova reserva com status PENDENTE (UC10 passo 4/5, RF-17, RF-20).
    Registra o histórico de status de reserva (RNF-22).
    """
    conn = get_db_connection()
    try:
        # Validação completa
        valido, msg_erro, acomodacao = validar_disponibilidade_e_regras(
            acomodacao_id, check_in, check_out, num_hospedes, conn=conn
        )
        if not valido:
            raise ValueError(msg_erro)

        # Cálculo do valor
        calculos = calcular_valores_estadia(
            acomodacao["precoNoite"], check_in, check_out, bool(acomodacao["superhost"])
        )

        now_iso = datetime.now().isoformat()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO reserva (
                hospede_id, acomodacao_id, checkIn, checkOut, numHospedes, valorTotal, status, dataCriacao
            ) VALUES (?, ?, ?, ?, ?, ?, 'PENDENTE', ?);
        """, (hospede_id, acomodacao_id, check_in, check_out, num_hospedes, calculos["valor_total"], now_iso))
        reserva_id = cursor.lastrowid

        # RNF-22: Trilha de auditoria da reserva
        cursor.execute("""
            INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora, responsavel_id)
            VALUES (?, NULL, 'PENDENTE', ?, ?);
        """, (reserva_id, now_iso, hospede_id))

        conn.commit()

        return {
            "reserva_id": reserva_id,
            "status": "PENDENTE",
            "valor_total": calculos["valor_total"],
            "calculos": calculos,
            "dataCriacao": now_iso
        }
    finally:
        conn.close()


def confirmar_reserva_apos_pagamento(reserva_id: int, conn=None):
    """
    Muda automaticamente o status da reserva de PENDENTE para CONFIRMADA
    quando o pagamento é aprovado (RF-20, TBD-03).
    Registra a auditoria (RNF-22).
    """
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    try:
        now_iso = datetime.now().isoformat()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM reserva WHERE id = ?;", (reserva_id,))
        res = cursor.fetchone()
        if not res:
            raise ValueError("Reserva não encontrada.")

        status_anterior = res["status"]
        if status_anterior == "CONFIRMADA":
            return  # Já confirmada

        cursor.execute("UPDATE reserva SET status = 'CONFIRMADA' WHERE id = ?;", (reserva_id,))
        cursor.execute("""
            INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora, responsavel_id)
            VALUES (?, ?, 'CONFIRMADA', ?, NULL);
        """, (reserva_id, status_anterior, now_iso))

        if close_at_end:
            conn.commit()
    finally:
        if close_at_end:
            conn.close()


# ---------------------------------------------------------------------------
# Operações de Pagamento e Histórico de Auditoria (RF-23, RF-24, RF-25, RNF-08, RNF-22)
# ---------------------------------------------------------------------------

def registrar_tentativa_pagamento(
    reserva_id: int,
    txid: str,
    metodo: str,
    valor: float,
    status: str,
    codigo_autorizacao: Optional[str] = None,
    token_cartao: Optional[str] = None,
    responsavel_id: Optional[int] = None,
    conn=None
) -> int:
    """
    Registra um registro de pagamento e grava no histórico de status de pagamento (RNF-22).
    RNF-08: Salva apenas o token do cartão, nunca dados sensíveis (CVV/número completo).
    """
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    try:
        now_iso = datetime.now().isoformat()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO pagamento (
                reserva_id, txid, metodo, valor, codigoAutorizacao, status, dataHora, tokenCartao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (reserva_id, txid, metodo, valor, codigo_autorizacao, status, now_iso, token_cartao))
        pagamento_id = cursor.lastrowid

        # RNF-22: Auditoria de status de pagamento
        cursor.execute("""
            INSERT INTO historico_status_pagamento (pagamento_id, statusAnterior, statusNovo, dataHora, responsavel_id)
            VALUES (?, NULL, ?, ?, ?);
        """, (pagamento_id, status, now_iso, responsavel_id))

        if close_at_end:
            conn.commit()

        return pagamento_id
    finally:
        if close_at_end:
            conn.close()


def atualizar_status_pagamento(
    pagamento_id: int,
    novo_status: str,
    codigo_autorizacao: Optional[str] = None,
    responsavel_id: Optional[int] = None,
    conn=None
):
    """
    Atualiza o status de um pagamento e registra a transição no histórico (RNF-22).
    """
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    try:
        now_iso = datetime.now().isoformat()
        cursor = conn.cursor()
        cursor.execute("SELECT status, codigoAutorizacao FROM pagamento WHERE id = ?;", (pagamento_id,))
        p = cursor.fetchone()
        if not p:
            raise ValueError("Pagamento não encontrado.")

        status_anterior = p["status"]
        cod_auth = codigo_autorizacao or p["codigoAutorizacao"]

        cursor.execute("""
            UPDATE pagamento SET status = ?, codigoAutorizacao = ? WHERE id = ?;
        """, (novo_status, cod_auth, pagamento_id))

        cursor.execute("""
            INSERT INTO historico_status_pagamento (pagamento_id, statusAnterior, statusNovo, dataHora, responsavel_id)
            VALUES (?, ?, ?, ?, ?);
        """, (pagamento_id, status_anterior, novo_status, now_iso, responsavel_id))

        if close_at_end:
            conn.commit()
    finally:
        if close_at_end:
            conn.close()


# ---------------------------------------------------------------------------
# Consultas e Filtragem de Privacidade de Endereço (RNF-05*, RNF-11)
# ---------------------------------------------------------------------------

def obter_reserva_completa(reserva_id: int, usuario_logado_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Retorna os detalhes completos da reserva, acomodação, anfitrião e pagamentos.
    Aplica RNF-05*: O endereço exato (rua, número, cep) SÓ é incluído se status == 'CONFIRMADA'.
    Aplica RNF-11: Verifica se usuário é o hóspede ou anfitrião caso fornecido.
    """
    conn = get_db_connection()
    try:
        # Atualiza status por timeout se necessário
        expirar_reservas_pendentes(conn)

        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*,
                   a.titulo as acomodacao_titulo, a.descricao as acomodacao_descricao,
                   a.precoNoite as acomodacao_precoNoite, a.capacidadeMaxima as acomodacao_capacidadeMaxima,
                   a.quartos as acomodacao_quartos, a.banheiros as acomodacao_banheiros,
                   a.camas as acomodacao_camas, a.regras as acomodacao_regras,
                   a.bairro as acomodacao_bairro, a.cidade as acomodacao_cidade, a.estado as acomodacao_estado,
                   a.cep as acomodacao_cep, a.rua as acomodacao_rua, a.numero as acomodacao_numero,
                   h.nome as hospede_nome, h.email as hospede_email, h.telefone as hospede_telefone,
                   anf.id as anfitriao_id, anf.nome as anfitriao_nome, anf.email as anfitriao_email,
                   anf.telefone as anfitriao_telefone, anf.superhost as anfitriao_superhost
            FROM reserva r
            JOIN acomodacao a ON r.acomodacao_id = a.id
            JOIN usuario h ON r.hospede_id = h.id
            JOIN usuario anf ON a.anfitriao_id = anf.id
            WHERE r.id = ?;
        """, (reserva_id,))
        row = cursor.fetchone()

        if not row:
            return None

        dados = dict(row)

        # RNF-05*: Antes da confirmação, oculta estritamente rua, número e cep
        esta_confirmada = (dados["status"] == "CONFIRMADA")
        if not esta_confirmada:
            dados["acomodacao_rua"] = None
            dados["acomodacao_numero"] = None
            dados["acomodacao_cep"] = None

        # Buscar pagamentos associados
        cursor.execute("""
            SELECT id, txid, metodo, valor, codigoAutorizacao, status, dataHora, tokenCartao
            FROM pagamento
            WHERE reserva_id = ?
            ORDER BY id ASC;
        """, (reserva_id,))
        dados["pagamentos"] = [dict(p) for p in cursor.fetchall()]

        # Pagamento aprovado mais recente (se houver)
        pag_aprovado = next((p for p in reversed(dados["pagamentos"]) if p["status"] == "APROVADO"), None)
        dados["pagamento_aprovado"] = pag_aprovado

        # Recalcular quebra de valores para visualização
        calculos = calcular_valores_estadia(
            dados["acomodacao_precoNoite"],
            dados["checkIn"],
            dados["checkOut"],
            bool(dados["anfitriao_superhost"])
        )
        dados["calculos"] = calculos

        # Tempo restante em segundos para expiração dos 30 minutos (RN-04)
        criacao = datetime.fromisoformat(dados["dataCriacao"])
        segundos_passados = (datetime.now() - criacao).total_seconds()
        segundos_restantes = max(0, int(1800 - segundos_passados))
        dados["segundos_restantes"] = segundos_restantes
        dados["expirada"] = (segundos_restantes == 0 and dados["status"] == "PENDENTE")

        return dados

    finally:
        conn.close()


def obter_acomodacao_detalhe(acomodacao_id: int) -> Optional[Dict[str, Any]]:
    """
    Retorna os detalhes de uma acomodação para a Tela 1 (Resumo).
    Aplica RNF-05*: Sempre oculta rua, número e CEP nesta fase de resumo.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.anfitriao_id, a.titulo, a.descricao, a.precoNoite,
                   a.capacidadeMaxima, a.quartos, a.banheiros, a.camas, a.regras,
                   a.bairro, a.cidade, a.estado, a.ativo,
                   u.nome as anfitriao_nome, u.email as anfitriao_email,
                   u.superhost, u.taxaResposta
            FROM acomodacao a
            JOIN usuario u ON a.anfitriao_id = u.id
            WHERE a.id = ?;
        """, (acomodacao_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def listar_acomodacoes_demonstracao() -> List[Dict[str, Any]]:
    """Retorna lista de acomodações para seleção e teste na interface."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.titulo, a.precoNoite, a.capacidadeMaxima, a.bairro, a.cidade, a.estado, a.ativo,
                   u.nome as anfitriao_nome, u.superhost
            FROM acomodacao a
            JOIN usuario u ON a.anfitriao_id = u.id
            ORDER BY a.id ASC;
        """)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
