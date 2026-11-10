"""
services/payment_gateway.py - Simulação do Gateway de Pagamento Externo
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
Conforme Seções 3.3, 3.4, 4.5 e RNF-08 da ERS v1.2.

REGRAS DE SIMULAÇÃO DOCUMENTADAS:
--------------------------------
1. Cartão de Crédito (Síncrono):
   - Cartões com final diferente de 0002: APROVADO com código de autorização e token do cartão.
   - Cartões terminados em '0002' ou nome 'RECUSADO': RECUSADO (simula saldo insuficiente / recusa bancária - RF-26).
   - Validade no passado: RECUSADO por cartão expirado.
   - Observância RNF-08: O sistema nunca armazena o número completo nem o CVV; apenas repassa
     ao gateway nesta chamada e persiste o token (`tok_...`) e código de autorização (`AUTH-...`).

2. PIX (Assíncrono):
   - `create_pix_charge`: Gera cobrança com txid único vinculado à reserva, QR code e código copia e cola válidos por 30 min.
   - O pagamento só se torna APROVADO após a confirmação via webhook (Seção 3.4).
"""

import uuid
from datetime import datetime, timedelta


class PaymentGateway:
    """Interface simulada do Gateway de Pagamento conforme Seções 3.3 e 3.4 da ERS."""

    @staticmethod
    def authorize_credit_card(card_holder: str, card_number: str, expiration: str, cvv: str, amount: float, reservation_id: int) -> dict:
        """
        Autorização síncrona de cartão de crédito.
        Retorna dicionário com o resultado da transação financeira.
        """
        clean_number = "".join(filter(str.isdigit, str(card_number)))
        now_iso = datetime.now().isoformat()
        txid = f"TX-CC-{reservation_id}-{uuid.uuid4().hex[:8].upper()}"

        # Validações simuladas
        if not clean_number or len(clean_number) < 13:
            return {
                "sucesso": False,
                "status": "RECUSADO",
                "txid": txid,
                "motivo": "Número de cartão de crédito inválido.",
                "dataHora": now_iso
            }

        # Simulação de recusa: cartão terminado em 0002 ou titular "RECUSADO"
        if clean_number.endswith("0002") or "RECUSADO" in (card_holder or "").upper():
            return {
                "sucesso": False,
                "status": "RECUSADO",
                "txid": txid,
                "motivo": "Transação recusada pela instituição emissora do cartão (saldo insuficiente ou restrição).",
                "dataHora": now_iso
            }

        # Simulação de validade expirada (formato MM/AA ou MM/AAAA)
        try:
            parts = expiration.strip().split("/")
            if len(parts) == 2:
                mes = int(parts[0])
                ano = int(parts[1])
                if ano < 100:
                    ano += 2000
                hoje = datetime.now()
                # Considera último dia do mês de validade
                if (ano < hoje.year) or (ano == hoje.year and mes < hoje.month):
                    return {
                        "sucesso": False,
                        "status": "RECUSADO",
                        "txid": txid,
                        "motivo": "Cartão vencido/expirado.",
                        "dataHora": now_iso
                    }
        except Exception:
            pass

        # Validação do CVV
        clean_cvv = "".join(filter(str.isdigit, str(cvv)))
        if len(clean_cvv) not in (3, 4):
            return {
                "sucesso": False,
                "status": "RECUSADO",
                "txid": txid,
                "motivo": "Código de segurança (CVV) inválido.",
                "dataHora": now_iso
            }

        # Sucesso: APROVADO
        # RNF-08: Devolve token do cartão e código de autorização
        card_token = f"tok_{uuid.uuid4().hex[:16]}"
        auth_code = f"AUTH-{uuid.uuid4().hex[:8].upper()}"

        return {
            "sucesso": True,
            "status": "APROVADO",
            "txid": txid,
            "codigoAutorizacao": auth_code,
            "tokenCartao": card_token,
            "ultimos4Digitos": clean_number[-4:],
            "bandeira": "Mastercard" if clean_number.startswith("5") else "Visa",
            "valor": float(amount),
            "dataHora": now_iso,
            "motivo": "Transação autorizada com sucesso."
        }

    @staticmethod
    def create_pix_charge(amount: float, reservation_id: int) -> dict:
        """
        Criação de cobrança assíncrona PIX (Seções 4.5.1, 4.5.2 e RF-23).
        Gera identificador único txid vinculado à reserva e payload copia-e-cola.
        """
        txid = f"PIX-{reservation_id}-{uuid.uuid4().hex[:10].upper()}"
        expires_at = (datetime.now() + timedelta(minutes=30)).isoformat()

        # Simulação do payload BR Code (Padrão BACEN / EMV)
        formatted_amount = f"{amount:.2f}"
        pix_copia_e_cola = (
            f"00020126580014br.gov.bcb.pix0136{txid}"
            f"520400005303986540{formatted_amount}5802BR5916AirbnbPlataforma6009RioDeJane"
            f"62070503***6304ABCD"
        )

        # Representação vetorial simples em SVG do QR Code (sem dependência externa)
        qr_code_svg = _generate_simulated_qr_svg(txid)

        return {
            "txid": txid,
            "reserva_id": reservation_id,
            "valor": float(amount),
            "chavePix": "financeiro@hospedagem-plataforma.com.br",
            "copiaECola": pix_copia_e_cola,
            "qrCodeSvg": qr_code_svg,
            "criadoEm": datetime.now().isoformat(),
            "expiraEm": expires_at,
            "status": "PROCESSANDO"
        }

    @staticmethod
    def process_refund(txid: str, amount: float) -> dict:
        """Processamento de reembolso (RF-27 e Seção 3.3)."""
        return {
            "sucesso": True,
            "status": "REEMBOLSADO",
            "txid": txid,
            "refund_id": f"REF-{uuid.uuid4().hex[:8].upper()}",
            "valor": float(amount),
            "dataHora": datetime.now().isoformat()
        }


def _generate_simulated_qr_svg(payload: str) -> str:
    """Gera um SVG estilizado simulando o QR Code do PIX."""
    # Gera um padrão geométrico determinístico baseado no hash do payload
    h = hash(payload)
    grid_size = 7
    rects = []
    for r in range(grid_size):
        for c in range(grid_size):
            bit = (h >> ((r * grid_size + c) % 32)) & 1
            if bit or (r in (0, 6) or c in (0, 6)):
                x = 20 + c * 20
                y = 20 + r * 20
                rects.append(f'<rect x="{x}" y="{y}" width="16" height="16" rx="2" fill="#0f172a" />')
    
    # Marcadores de canto clássicos de QR Code
    corner_markers = """
        <rect x="15" y="15" width="45" height="45" fill="none" stroke="#0f172a" stroke-width="6" rx="4"/>
        <rect x="25" y="25" width="25" height="25" fill="#0f172a" rx="2"/>
        <rect x="120" y="15" width="45" height="45" fill="none" stroke="#0f172a" stroke-width="6" rx="4"/>
        <rect x="130" y="25" width="25" height="25" fill="#0f172a" rx="2"/>
        <rect x="15" y="120" width="45" height="45" fill="none" stroke="#0f172a" stroke-width="6" rx="4"/>
        <rect x="25" y="130" width="25" height="25" fill="#0f172a" rx="2"/>
    """
    
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 180" width="180" height="180">
        <rect width="180" height="180" fill="#ffffff" rx="10" />
        {corner_markers}
        {' '.join(rects)}
    </svg>"""
    return svg
