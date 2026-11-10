import uuid

class PaymentGatewaySimulado:
    """
    Simulação de Gateway de Pagamento Externo (Seção 3.3 e 4.5 da ERS).
    Suporta autorização síncrona (Cartão) e emissão assíncrona (PIX).
    """
    
    @staticmethod
    def processar_cartao(numero_cartao, valor):
        # Regra de teste: cartões com final '0000' simulam recusa (RF-26)
        if str(numero_cartao).strip().endswith("0000"):
            return {
                "sucesso": False,
                "codigoAutorizacao": None,
                "txid": f"TX-CARD-{uuid.uuid4().hex[:8].upper()}",
                "status": "RECUSADO"
            }
        return {
            "sucesso": True,
            "codigoAutorizacao": f"AUTH-{uuid.uuid4().hex[:8].upper()}",
            "txid": f"TX-CARD-{uuid.uuid4().hex[:8].upper()}",
            "status": "APROVADO"
        }

    @staticmethod
    def gerar_cobranca_pix(reserva_id, valor):
        # RF-23: identificador único vinculado à reserva
        txid = f"PIX-RES-{reserva_id}-{uuid.uuid4().hex[:6].upper()}"
        copia_cola = (
            f"00020126580014BR.GOV.BCB.PIX0136{txid}"
            f"520400005303986540{valor:.2f}5802BR5920AIRBNB_ERS_PLATAFORM"
            f"6009RIO_DE_JANEIRO62070503***6304"
        )
        return {
            "txid": txid,
            "qr_code_simulado": f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={copia_cola}",
            "copia_cola": copia_cola
        }
