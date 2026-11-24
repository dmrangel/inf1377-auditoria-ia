"""Relógio da aplicação.

Todas as regras que dependem de "hoje" ou "agora" (datas no passado, prazo de
30 min da reserva PENDENTE, prazo de 14 dias das avaliações) leem o relógio
daqui, para que os testes possam fixar a data com app.config["AGORA"].
"""
from datetime import datetime

from flask import current_app, has_app_context


def agora():
    if has_app_context():
        fixo = current_app.config.get("AGORA")
        if fixo is not None:
            return fixo
    return datetime.now().replace(microsecond=0)


def hoje():
    return agora().date()
