"""Gera em amostras/ os arquivos para testar o upload de fotos pela tela.

    python gerar_amostras.py

Cria:
    foto01.png ... foto31.png   fotos válidas (31 para testar o limite de 30)
    foto.jpg                    JPEG válido (cabeçalho JPEG)
    gif-disfarcado.png          GIF com extensão .png (deve ser recusado)
    grande-11mb.png             PNG com mais de 10 MB (deve ser recusado)
    falha-armazenamento.png     PNG válido cujo nome simula queda do armazenamento
"""

import os

from imagens import png_numerado

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "amostras")


def main():
    os.makedirs(PASTA, exist_ok=True)

    def gravar(nome, conteudo):
        with open(os.path.join(PASTA, nome), "wb") as f:
            f.write(conteudo)

    for i in range(1, 32):
        gravar(f"foto{i:02d}.png", png_numerado(i))
    gravar("foto.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 1000 + b"\xff\xd9")
    gravar("gif-disfarcado.png", b"GIF89a" + b"\x00" * 1000)
    gravar("grande-11mb.png", png_numerado(0) + b"\x00" * (11 * 1024 * 1024))
    gravar("falha-armazenamento.png", png_numerado(5))
    print(f"Amostras gravadas em {PASTA}")


if __name__ == "__main__":
    main()
