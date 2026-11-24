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
    def send_review_invitation(
        cls,
        destinatario_email: str,
        destinatario_nome: str,
        papel: str,
        reserva_id: int,
        acomodacao_titulo: str,
        outra_parte_nome: str,
        prazo_final: str,
        link: str
    ) -> bool:
        """
        [Avaliação de estadia] Convida um participante a avaliar a estadia
        (seção 4.6.2, passo 1; UC18/UC19, passo 1).

        papel: "HOSPEDE" (avalia a acomodação, UC18) ou "ANFITRIAO" (avalia o hóspede, UC19).
        prazo_final: último dia, inclusive, para avaliar (RN-06), no formato AAAA-MM-DD.

        Como simular: não há resposta a simular; o envio sempre "funciona" e a
        mensagem fica visível em GET /api/dev/emails com tipo CONVITE_AVALIACAO.
        """
        if papel == "HOSPEDE":
            alvo = f"a acomodação '{acomodacao_titulo}' e o anfitrião {outra_parte_nome}"
        else:
            alvo = f"o hóspede {outra_parte_nome}, que ficou em '{acomodacao_titulo}'"

        corpo = (
            f"Olá, {destinatario_nome}!\n\n"
            f"A estadia da reserva #{reserva_id} terminou. Conte como foi avaliando {alvo}.\n"
            f"Dê uma nota de 1 a 5 e, se quiser, deixe um comentário.\n"
            f"Você pode avaliar até {prazo_final} (14 dias após o check-out, RN-06).\n"
            f"As avaliações só ficam públicas quando as duas partes avaliarem ou quando o prazo terminar.\n\n"
            f"Avaliar agora: {link}\n"
        )
        _SENT_EMAILS.append({
            "destinatario": destinatario_email,
            "tipo": "CONVITE_AVALIACAO",
            "assunto": f"[Airbnb Plataforma] Como foi a estadia da reserva #{reserva_id}?",
            "corpo": corpo,
            "dataEnvio": datetime.now().isoformat(),
            "reserva_id": reserva_id
        })
        print(f"[email_service] Convite de avaliação da reserva #{reserva_id} enviado para {destinatario_email}.")
        return True

    @classmethod
    def get_sent_emails(cls) -> List[Dict[str, Any]]:
        """Retorna o histórico de e-mails enviados para verificação em testes."""
        return list(_SENT_EMAILS)

    @classmethod
    def clear(cls):
        """Limpa a fila de e-mails enviados (útil em testes unitários)."""
        _SENT_EMAILS.clear()
