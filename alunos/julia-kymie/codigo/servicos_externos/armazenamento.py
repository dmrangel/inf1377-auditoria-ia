"""Armazenamento de arquivos (ERS 3.3): "Guardar fotos de anúncios e perfis".

Dados trocados (3.3): imagens JPEG/PNG de até 10 MB.

ArmazenamentoSimulado imita um bucket de objetos (por exemplo S3): recebe os
bytes, devolve uma chave opaca, permite ler e apagar pela chave. Os arquivos
ficam numa pasta local (por padrão instancia/arquivos/).

O serviço simulado também recusa o que um serviço real configurado com essas
regras recusaria (tipo ou tamanho fora do contrato). A validação amigável ao
usuário é feita antes, em dominio/validacao.py; esta é a segunda barreira.

Como simular cada resposta (também descrito no README):

    Situação                                   Como provocar
    Gravação bem-sucedida                      enviar JPEG ou PNG de até 10 MB
    Serviço indisponível                       enviar um arquivo cujo NOME contenha
                                               "falha-armazenamento" (ex.: falha-armazenamento.png)
                                               ou ligar FALHAR_ARMAZENAMENTO=1 no ambiente
"""

import os
import uuid

TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024
TIPOS_ACEITOS = {"image/jpeg": ".jpg", "image/png": ".png"}


class ArmazenamentoIndisponivel(RuntimeError):
    """O serviço de armazenamento não aceitou a gravação (queda simulada)."""


class ArquivoRecusado(ValueError):
    """O arquivo viola o contrato do serviço (tipo ou tamanho)."""


class ArmazenamentoSimulado:
    """Interface: salvar(conteudo, tipo_conteudo, nome_original) -> chave;
    ler(chave) -> (bytes, tipo_conteudo); remover(chave)."""

    GATILHO_FALHA = "falha-armazenamento"

    def __init__(self, diretorio, falhar_sempre=False):
        self.diretorio = str(diretorio)
        self.falhar_sempre = falhar_sempre
        os.makedirs(self.diretorio, exist_ok=True)

    def salvar(self, conteudo, tipo_conteudo, nome_original=""):
        if self.falhar_sempre or self.GATILHO_FALHA in (nome_original or "").lower():
            raise ArmazenamentoIndisponivel(
                "O serviço de armazenamento de fotos está indisponível. Tente novamente mais tarde."
            )
        if tipo_conteudo not in TIPOS_ACEITOS:
            raise ArquivoRecusado("Tipo de arquivo não aceito pelo armazenamento.")
        if len(conteudo) > TAMANHO_MAXIMO_BYTES:
            raise ArquivoRecusado("Arquivo maior que 10 MB.")
        chave = uuid.uuid4().hex + TIPOS_ACEITOS[tipo_conteudo]
        with open(self._caminho(chave), "wb") as f:
            f.write(conteudo)
        return chave

    def ler(self, chave):
        caminho = self._caminho(chave)
        if not os.path.isfile(caminho):
            raise FileNotFoundError(chave)
        with open(caminho, "rb") as f:
            dados = f.read()
        tipo = "image/png" if chave.endswith(".png") else "image/jpeg"
        return dados, tipo

    def remover(self, chave):
        try:
            os.remove(self._caminho(chave))
        except FileNotFoundError:
            pass  # remover é idempotente, como num bucket real

    def _caminho(self, chave):
        # A chave é gerada por nós (uuid + extensão); ainda assim, impedimos
        # que uma chave vinda da URL saia da pasta (path traversal).
        nome = os.path.basename(chave)
        if nome != chave or not nome:
            raise FileNotFoundError(chave)
        return os.path.join(self.diretorio, nome)
