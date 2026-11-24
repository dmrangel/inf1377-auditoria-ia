"""
services/email_service.py - Simulação do Serviço de E-mail Externo
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
Conforme Seções 3.3, 3.4, 4.4.2, 4.5.2 e RF-28 da ERS v1.2.
"""

from datetime import datetime
from typing import List, Dict, Any

# Armazenamento em memória dos e-mails disparados para auditoria e asserções em testes
_SENT_EMAILS: List[Dict[str, Any]] = []


class EmailService:
    """Interface simulada para envio de notificações por e-mail."""

    @classmethod
    def send_reservation_confirmed(
        cls,
        hospede_email: str,
        hospede_nome: str,
        anfitriao_email: str,
        anfitriao_nome: str,
        reserva: dict,
        acomodacao: dict,
        pagamento: dict
    ) -> bool:
        """
        Dispara e-mail de confirmação ao hóspede (RF-28) com comprovante e endereço completo (RNF-05*),
        e e-mail de notificação ao anfitrião sobre a nova reserva confirmada.
        """
        now = datetime.now().strftime("%d/%m/%Y às %H:%M")

        # 1. E-mail ao hóspede com comprovante completo
        corpo_hospede = (
            f"Olá, {hospede_nome}!\n\n"
            f"Sua reserva #{reserva['id']} foi CONFIRMADA com sucesso em {now}!\n"
            f"Acomodação: {acomodacao['titulo']}\n"
            f"Endereço Completo: {acomodacao['rua']}, nº {acomodacao['numero']}, {acomodacao['bairro']} - {acomodacao['cidade']}/{acomodacao['estado']} (CEP: {acomodacao['cep']})\n"
            f"Check-in: {reserva['checkIn']}\n"
            f"Check-out: {reserva['checkOut']}\n"
            f"Hóspedes: {reserva['numHospedes']}\n\n"
            f"--- Detalhes do Pagamento ---\n"
            f"Método: {pagamento['metodo']}\n"
            f"Valor Total Pago: R$ {pagamento['valor']:.2f}\n"
            f"Identificador da Transação (txid): {pagamento['txid']}\n"
            f"Código de Autorização: {pagamento.get('codigoAutorizacao', 'N/A')}\n\n"
            f"--- Contato do Anfitrião ---\n"
            f"Anfitrião: {anfitriao_nome}\n"
            f"E-mail: {anfitriao_email}\n\n"
            f"--- Regras da Casa ---\n"
            f"{acomodacao['regras']}\n\n"
            f"Tenha uma excelente estadia!"
        )

        email_hospede = {
            "destinatario": hospede_email,
            "tipo": "CONFIRMACAO_RESERVA_HOSPEDE",
            "assunto": f"[Airbnb Plataforma] Reserva #{reserva['id']} CONFIRMADA! Seu comprovante de estadia",
            "corpo": corpo_hospede,
            "dataEnvio": datetime.now().isoformat(),
            "reserva_id": reserva["id"]
        }
        _SENT_EMAILS.append(email_hospede)

        # 2. E-mail ao anfitrião comunicando nova reserva
        corpo_anfitriao = (
            f"Olá, {anfitriao_nome}!\n\n"
            f"Você recebeu uma nova reserva confirmada na acomodação '{acomodacao['titulo']}'.\n"
            f"Hóspede: {hospede_nome} ({hospede_email})\n"
            f"Período: de {reserva['checkIn']} até {reserva['checkOut']}\n"
            f"Número de hóspedes: {reserva['numHospedes']}\n"
            f"Valor da reserva: R$ {reserva['valorTotal']:.2f}\n"
            f"O valor repassado será liberado 24 horas após o check-in (RN-08).\n"
        )

        email_anfitriao = {
            "destinatario": anfitriao_email,
            "tipo": "NOTIFICACAO_NOVA_RESERVA_ANFITRIAO",
            "assunto": f"[Airbnb Plataforma] Nova reserva confirmada (#{reserva['id']})",
            "corpo": corpo_anfitriao,
            "dataEnvio": datetime.now().isoformat(),
            "reserva_id": reserva["id"]
        }
        _SENT_EMAILS.append(email_anfitriao)

        print(f"[email_service] E-mails de confirmação enviados para {hospede_email} e {anfitriao_email}.")
        return True

    @classmethod
    def send_reservation_cancelled(
        cls,
        reserva: dict,
        cancelado_por: str,
        reembolso: dict,
        pagamento_reembolso: dict = None
    ) -> List[Dict[str, Any]]:
        """
        Notificações do cancelamento (UC12 passo 5 e RF-28 aplicado ao reembolso).

        - A "outra parte" sempre é avisada: se o hóspede cancelou, o anfitrião;
          se o anfitrião cancelou, o hóspede (com os dados do reembolso).
        - Quando há reembolso e quem cancelou foi o hóspede, ele também recebe o
          comprovante do reembolso, porque o reembolso é um pagamento da reserva
          (Seção 4.5.1) e o RF-28 manda emitir comprovante de pagamento por e-mail.
        O e-mail não traz o endereço exato: a reserva não está mais CONFIRMADA (RNF-05*).
        """
        enviados = []
        agora = datetime.now()
        quando = agora.strftime("%d/%m/%Y às %H:%M")
        valor = float(reembolso.get("valor_reembolso", 0))

        detalhes_reembolso = ""
        if pagamento_reembolso:
            detalhes_reembolso = (
                f"\n--- Reembolso ---\n"
                f"Valor reembolsado: R$ {valor:.2f}\n"
                f"Regra aplicada: {reembolso.get('descricao_regra', '')}\n"
                f"Identificador do reembolso: {pagamento_reembolso.get('txid')}\n"
                f"Código de autorização do estorno: {pagamento_reembolso.get('codigoAutorizacao')}\n"
                f"Pagamento original (txid): {reembolso.get('txid_original')}\n"
                f"O prazo para o valor aparecer na fatura ou na conta depende da instituição financeira.\n"
            )
        else:
            detalhes_reembolso = f"\nNão há valor a reembolsar: {reembolso.get('descricao_regra', '')}\n"

        def registrar(destinatario, tipo, assunto, corpo):
            email = {
                "destinatario": destinatario,
                "tipo": tipo,
                "assunto": assunto,
                "corpo": corpo,
                "dataEnvio": agora.isoformat(),
                "reserva_id": reserva["id"]
            }
            _SENT_EMAILS.append(email)
            enviados.append(email)

        periodo = f"de {reserva['checkIn']} até {reserva['checkOut']}"

        if cancelado_por == "HOSPEDE":
            registrar(
                reserva["anfitriao_email"],
                "CANCELAMENTO_RESERVA_ANFITRIAO",
                f"[Airbnb Plataforma] Reserva #{reserva['id']} cancelada pelo hóspede",
                f"Olá, {reserva['anfitriao_nome']}!\n\n"
                f"O hóspede {reserva['hospede_nome']} cancelou a reserva #{reserva['id']} em {quando}.\n"
                f"Acomodação: {reserva['acomodacao_titulo']}\n"
                f"Período: {periodo}\n"
                f"As datas voltaram a ficar livres no calendário.\n"
                f"Valor reembolsado ao hóspede: R$ {valor:.2f}\n"
            )
            if pagamento_reembolso:
                registrar(
                    reserva["hospede_email"],
                    "COMPROVANTE_REEMBOLSO_HOSPEDE",
                    f"[Airbnb Plataforma] Comprovante de reembolso da reserva #{reserva['id']}",
                    f"Olá, {reserva['hospede_nome']}!\n\n"
                    f"Você cancelou a reserva #{reserva['id']} ({reserva['acomodacao_titulo']}, {periodo}) em {quando}.\n"
                    + detalhes_reembolso
                )
        else:
            registrar(
                reserva["hospede_email"],
                "CANCELAMENTO_RESERVA_HOSPEDE",
                f"[Airbnb Plataforma] Sua reserva #{reserva['id']} foi cancelada pelo anfitrião",
                f"Olá, {reserva['hospede_nome']}!\n\n"
                f"O anfitrião {reserva['anfitriao_nome']} cancelou a sua reserva #{reserva['id']} em {quando}.\n"
                f"Acomodação: {reserva['acomodacao_titulo']}\n"
                f"Período: {periodo}\n"
                + detalhes_reembolso
            )

        print(f"[email_service] Cancelamento da reserva #{reserva['id']}: {len(enviados)} e-mail(s) enviado(s).")
        return enviados

    @classmethod
    def get_sent_emails(cls) -> List[Dict[str, Any]]:
        """Retorna o histórico de e-mails enviados para verificação em testes."""
        return list(_SENT_EMAILS)

    @classmethod
    def clear(cls):
        """Limpa a fila de e-mails enviados (útil em testes unitários)."""
        _SENT_EMAILS.clear()
