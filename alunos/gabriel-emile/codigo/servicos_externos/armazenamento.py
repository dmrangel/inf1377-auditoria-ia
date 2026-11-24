"""Armazenamento de arquivos (ERS 3.3) -- SIMULADO.

Na ERS, o armazenamento guarda as fotos de anúncios e perfis (JPEG/PNG de até
10 MB). Esta tarefa só LÊ fotos: o envio pertence ao cadastro de acomodação
(UC05), fora do escopo.

Interface (a mesma que um adaptador real, por exemplo para um bucket S3,
teria de implementar):

    url_publica(chave) -> str
        URL que o navegador usa para baixar a foto.
    obter(chave) -> (bytes, mimetype)
        Conteúdo do arquivo. Lança ArquivoNaoEncontrado ou ServicoIndisponivel.

A simulação não guarda imagens de verdade: gera na hora um SVG colorido com a
legenda da foto, servido pela rota /arquivos/<chave>.

Como simular cada resposta:
  * Sucesso: qualquer chave que comece com "fotos/".
  * Arquivo não encontrado (foto quebrada): chave que comece com "ausente/"
    (o seed tem uma foto assim no "Loft em Pinheiros"); o front-end mostra um
    texto alternativo no lugar.
  * Serviço fora do ar: variável de ambiente SIMULAR_FALHA_ARMAZENAMENTO=1
    (ou app.config["SIMULAR_FALHA_ARMAZENAMENTO"] = True).
"""
import hashlib
from html import escape


class ServicoIndisponivel(Exception):
    pass


class ArquivoNaoEncontrado(Exception):
    pass


class ArmazenamentoSimulado:
    def __init__(self, base_url="/arquivos/", falhar=False):
        self.base_url = base_url
        self.falhar = falhar

    def url_publica(self, chave):
        return self.base_url + chave

    def obter(self, chave):
        if self.falhar:
            raise ServicoIndisponivel("Armazenamento fora do ar (simulado).")
        if not chave.startswith("fotos/"):
            raise ArquivoNaoEncontrado(chave)
        # Cor estável derivada da chave, para as fotos parecerem diferentes.
        h = hashlib.md5(chave.encode("utf-8")).hexdigest()
        cor1, cor2 = "#" + h[:6], "#" + h[6:12]
        texto = escape(chave.rsplit("/", 1)[-1].replace("-", " ").rsplit(".", 1)[0])
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420" '
            'viewBox="0 0 640 420" role="img">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{cor1}"/><stop offset="1" stop-color="{cor2}"/>'
            "</linearGradient></defs>"
            '<rect width="640" height="420" fill="url(#g)"/>'
            '<rect x="20" y="350" width="600" height="50" rx="8" fill="rgba(0,0,0,.55)"/>'
            f'<text x="40" y="383" font-family="sans-serif" font-size="24" fill="#fff">{texto}</text>'
            "</svg>"
        )
        return svg.encode("utf-8"), "image/svg+xml"
