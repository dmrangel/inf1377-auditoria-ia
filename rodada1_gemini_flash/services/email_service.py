class EmailServiceSimulado:
    """Simulador do Serviço de E-mail para atender a RF-28"""
    mensagens_enviadas = []

    @classmethod
    def enviar_confirmacao_reserva(cls, destinatario, reserva_id, valor, auth_code):
        mensagem = {
            "para": destinatario,
            "assunto": f"Confirmação da Reserva #{reserva_id}",
            "corpo": f"Reserva #{reserva_id} confirmada com sucesso! Valor pago: R$ {valor:.2f}. Aut: {auth_code}."
        }
        cls.mensagens_enviadas.append(mensagem)
        return True
