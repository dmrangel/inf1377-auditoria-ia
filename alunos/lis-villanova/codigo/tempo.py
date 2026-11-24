"""
tempo.py - Relógio único do sistema.

Todas as regras que dependem de tempo (bloqueio de 15 min do RNF-10, sessão de
30 min do RNF-09, validade dos links enviados por e-mail) leem a hora daqui.
Assim os testes podem "avançar o relógio" trocando agora_utc() com monkeypatch,
sem precisar esperar de verdade.

As datas são gravadas no banco como texto ISO 8601 em UTC.
"""

from datetime import datetime, timezone


def agora_utc():
    """Hora atual em UTC, sem microssegundos (facilita comparar e ler no banco)."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def para_iso(dt):
    """Converte um datetime com fuso para texto ISO 8601 em UTC."""
    return dt.astimezone(timezone.utc).isoformat()


def de_iso(texto):
    """Converte o texto ISO 8601 gravado no banco de volta para datetime."""
    return datetime.fromisoformat(texto)
