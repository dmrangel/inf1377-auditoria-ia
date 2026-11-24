"""
tests/conftest.py - Configuração compartilhada dos testes.

Os testes usam um banco SQLite próprio, num diretório temporário, e nunca o
hospedagem.db do app. A variável HOSPEDAGEM_DB_PATH precisa ser definida antes
de qualquer import de database/app, por isso fica no topo deste arquivo, que o
pytest carrega antes dos módulos de teste.
"""

import os
import sys
import tempfile

_DIR_TESTES_DB = tempfile.mkdtemp(prefix="hospedagem_testes_")
os.environ["HOSPEDAGEM_DB_PATH"] = os.path.join(_DIR_TESTES_DB, "hospedagem_testes.db")

# Permite rodar tanto `pytest` quanto `python -m pytest` a partir de codigo/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
