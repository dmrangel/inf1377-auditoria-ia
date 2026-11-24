"""Gera imagens PNG simples (sem bibliotecas externas) para os dados de exemplo,
os testes e as amostras de upload."""

import struct
import zlib


def _bloco(tipo, dados):
    return (struct.pack(">I", len(dados)) + tipo + dados
            + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF))


def gerar_png(largura=320, altura=200, cor=(70, 130, 180), faixa=(255, 255, 255)):
    """PNG RGB com uma cor de fundo e uma faixa horizontal, para as fotos
    de exemplo serem distinguíveis entre si."""
    linhas = []
    for y in range(altura):
        c = faixa if altura // 2 - 6 <= y <= altura // 2 + 6 else cor
        linhas.append(b"\x00" + bytes(c) * largura)
    cabecalho = struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _bloco(b"IHDR", cabecalho)
            + _bloco(b"IDAT", zlib.compress(b"".join(linhas), 9)) + _bloco(b"IEND", b""))


PALETA = [
    (231, 76, 60), (46, 134, 193), (39, 174, 96), (241, 196, 15), (142, 68, 173),
    (230, 126, 34), (22, 160, 133), (52, 73, 94), (192, 57, 43), (41, 128, 185),
]


def png_numerado(i):
    return gerar_png(cor=PALETA[i % len(PALETA)])
