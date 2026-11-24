"""
dados_exemplo.py - Contas de teste inseridas quando o banco é criado vazio.

Todas usam a senha Senha123. Cada uma existe para demonstrar um cenário
(ver README.md, "Como testar cada cenário").
"""

from datetime import timedelta

import tempo
import usuarios

SENHA_PADRAO = "Senha123"

CONTAS = [
    # e-mail, nome, telefone, anfitrião?, e-mail confirmado?, bloqueada?
    ("ana@exemplo.com", "Ana Souza", "21999990001", False, True, False),
    ("bruno@exemplo.com", "Bruno Lima", "21999990002", True, True, False),
    ("carla@exemplo.com", "Carla Dias", "21999990003", False, True, True),
    ("diego@exemplo.com", "Diego Alves", "2133330004", False, False, False),
]


def popular(conn):
    agora = tempo.agora_utc()
    agora_iso = tempo.para_iso(agora)
    for email, nome, telefone, anfitriao, confirmado, bloqueada in CONTAS:
        conn.execute(
            "INSERT INTO usuario (nome, email, senhaHash, telefone, dataCadastro, ehAnfitriao, "
            "dataAtivacaoAnfitriao, emailConfirmado, consentimentoTermosEm, versaoTermos, "
            "bloqueadoAte) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                nome, email, usuarios.gerar_hash_senha(SENHA_PADRAO), telefone, agora_iso,
                int(anfitriao), agora_iso if anfitriao else None, int(confirmado),
                agora_iso, usuarios.VERSAO_TERMOS,
                # Carla começa bloqueada (RNF-10) pelos 15 minutos seguintes à criação do banco.
                tempo.para_iso(agora + timedelta(minutes=15)) if bloqueada else None,
            ),
        )
    print("[banco] Banco criado com as contas de exemplo (senha de todas: Senha123).", flush=True)
