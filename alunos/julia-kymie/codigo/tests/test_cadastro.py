"""UC05 — Cadastrar acomodação (RF-07, RF-08, ERS 3.3)."""

import io

import pytest

from conftest import (ANA, CARLA, arquivos_png, dados_validos, entrar, form_com_fotos)
from servicos_externos.armazenamento import TAMANHO_MAXIMO_BYTES


def publicar(cliente, dados=None, fotos=None):
    return cliente.post(
        "/api/acomodacoes",
        data=form_com_fotos(dados or dados_validos(), arquivos_png(5) if fotos is None else fotos),
        content_type="multipart/form-data",
    )


def test_caminho_feliz_publica_anuncio_com_endereco_do_cep(ana, app):
    r = publicar(ana)
    assert r.status_code == 201, r.json
    assert r.json["origemEndereco"] == "servico_cep"
    novo = ana.get(f"/api/acomodacoes/{r.json['id']}").json
    # UC05 passo 3: rua, bairro e cidade vieram do serviço de CEP
    assert novo["rua"] == "Rua Marquês de São Vicente"
    assert novo["bairro"] == "Gávea"
    assert novo["cidade"] == "Rio de Janeiro"
    assert novo["precoNoite"] == "200.00" and novo["precoNoiteCentavos"] == 20000
    assert novo["ativo"] is True  # publicado (pós-condição do UC05)
    assert len(novo["fotos"]) == 5
    # visível na vitrine pública
    assert any(a["id"] == r.json["id"] for a in ana.get("/api/anuncios").json)


def test_servico_cep_prevalece_sobre_endereco_digitado(ana):
    r = publicar(ana, dados_validos(rua="Rua Inventada", cidade="Niterói", estado="SP"))
    assert r.status_code == 201
    novo = ana.get(f"/api/acomodacoes/{r.json['id']}").json
    assert (novo["rua"], novo["cidade"], novo["estado"]) == ("Rua Marquês de São Vicente", "Rio de Janeiro", "RJ")


def test_cep_nao_encontrado_aceita_endereco_manual(ana):
    """UC05 fluxo 3a."""
    dados = dados_validos(cep="20000-123", rua="Rua Manual", bairro="Centro", cidade="Rio de Janeiro")
    r = publicar(ana, dados)
    assert r.status_code == 201
    assert r.json["origemEndereco"] == "manual_cep_nao_encontrado"
    assert ana.get(f"/api/acomodacoes/{r.json['id']}").json["rua"] == "Rua Manual"


def test_cep_nao_encontrado_sem_endereco_manual_falha(ana):
    r = publicar(ana, dados_validos(cep="20000-123"))
    assert r.status_code == 400
    assert {"rua", "bairro", "cidade"} <= set(r.json["campos"])


def test_servico_cep_indisponivel_aceita_endereco_manual(ana):
    dados = dados_validos(cep="99999-999", rua="Rua X", bairro="Centro", cidade="Rio de Janeiro")
    r = publicar(ana, dados)
    assert r.status_code == 201
    assert r.json["origemEndereco"] == "manual_servico_indisponivel"


def test_cep_geral_de_cidade_completa_rua_e_bairro_manualmente(ana):
    dados = dados_validos(cep="35400-000", rua="Rua São José", bairro="Centro", estado="")
    r = publicar(ana, dados)
    assert r.status_code == 201
    novo = ana.get(f"/api/acomodacoes/{r.json['id']}").json
    assert (novo["rua"], novo["cidade"], novo["estado"]) == ("Rua São José", "Ouro Preto", "MG")


@pytest.mark.parametrize("cep", ["123", "abcde-fgh", "", "2245190"])
def test_cep_invalido(ana, cep):
    r = publicar(ana, dados_validos(cep=cep))
    assert r.status_code == 400
    assert "cep" in r.json["campos"]


def test_menos_de_5_fotos_impede_publicacao(ana, app):
    """UC05 fluxo 5a: informa o mínimo exigido e não grava nada."""
    antes = len(ana.get("/api/minhas-acomodacoes").json)
    r = publicar(ana, fotos=arquivos_png(4))
    assert r.status_code == 400
    assert "no mínimo 5 fotos" in r.json["erro"]
    assert len(ana.get("/api/minhas-acomodacoes").json) == antes


def test_exatamente_30_fotos_e_aceito(ana):
    assert publicar(ana, fotos=arquivos_png(30)).status_code == 201


def test_mais_de_30_fotos_e_recusado(ana):
    r = publicar(ana, fotos=arquivos_png(31))
    assert r.status_code == 400
    assert "no máximo 30 fotos" in r.json["erro"]


def test_foto_que_nao_e_jpeg_nem_png_e_recusada(ana):
    fotos = arquivos_png(5)
    fotos[2] = (io.BytesIO(b"GIF89a" + b"\x00" * 100), "disfarcado.png")  # extensão mente
    r = publicar(ana, fotos=fotos)
    assert r.status_code == 400
    assert "não é JPEG nem PNG" in r.json["erro"]


def test_jpeg_e_aceito(ana):
    fotos = arquivos_png(4) + [(io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 200), "foto.jpg")]
    assert publicar(ana, fotos=fotos).status_code == 201


def test_foto_maior_que_10mb_e_recusada(ana):
    grande = b"\x89PNG\r\n\x1a\n" + b"\x00" * (TAMANHO_MAXIMO_BYTES - 7)
    fotos = arquivos_png(4) + [(io.BytesIO(grande), "grande.png")]
    r = publicar(ana, fotos=fotos)
    assert r.status_code == 400
    assert "mais de 10 MB" in r.json["erro"]


def test_foto_de_exatamente_10mb_e_aceita(ana):
    limite = b"\x89PNG\r\n\x1a\n" + b"\x00" * (TAMANHO_MAXIMO_BYTES - 8)
    fotos = arquivos_png(4) + [(io.BytesIO(limite), "limite.png")]
    assert publicar(ana, fotos=fotos).status_code == 201


def test_falha_do_armazenamento_nao_deixa_nada_gravado(ana, app, tmp_path):
    antes_arquivos = set((tmp_path / "arquivos").iterdir())
    antes = len(ana.get("/api/minhas-acomodacoes").json)
    fotos = arquivos_png(4) + [(io.BytesIO(arquivos_png(1)[0][0].getvalue()), "falha-armazenamento.png")]
    r = publicar(ana, fotos=fotos)
    assert r.status_code == 503
    assert len(ana.get("/api/minhas-acomodacoes").json) == antes
    assert set((tmp_path / "arquivos").iterdir()) == antes_arquivos  # sem arquivos órfãos


@pytest.mark.parametrize("campo", ["titulo", "descricao", "precoNoite", "capacidadeMaxima",
                                   "quartos", "banheiros", "camas", "regras", "numero"])
def test_campos_obrigatorios_rf07(ana, campo):
    r = publicar(ana, dados_validos(**{campo: ""}))
    assert r.status_code == 400
    assert campo in r.json["campos"]


@pytest.mark.parametrize("campo,valor", [
    ("precoNoite", "0"), ("precoNoite", "-10"), ("precoNoite", "abc"), ("precoNoite", "10,555"),
    ("precoNoite", "100000,01"), ("capacidadeMaxima", "0"), ("capacidadeMaxima", "2.5"),
    ("capacidadeMaxima", "51"), ("quartos", "-1"), ("banheiros", "0"), ("camas", "0"),
    ("titulo", "Casa"), ("descricao", "curta"), ("estado", "XX"),
])
def test_valores_invalidos(ana, campo, valor):
    r = publicar(ana, dados_validos(cep="20000-123", rua="R", bairro="B", cidade="C", **{campo: valor}))
    assert r.status_code == 400
    assert campo in r.json["campos"]


def test_todos_os_erros_aparecem_juntos(ana):
    r = publicar(ana, dados_validos(titulo="", precoNoite="0"), fotos=arquivos_png(2))
    assert r.status_code == 400
    assert {"titulo", "precoNoite", "fotos"} <= set(r.json["campos"])


@pytest.mark.parametrize("entrada,centavos", [("350", 35000), ("350,5", 35050), ("1.234,56", 123456), ("99.90", 9990)])
def test_formatos_de_preco(ana, entrada, centavos):
    r = publicar(ana, dados_validos(precoNoite=entrada))
    assert r.status_code == 201
    assert ana.get(f"/api/acomodacoes/{r.json['id']}").json["precoNoiteCentavos"] == centavos


def test_quartos_zero_estudio_e_aceito(ana):
    assert publicar(ana, dados_validos(quartos="0")).status_code == 201


def test_json_sem_fotos_e_recusado(ana):
    r = ana.post("/api/acomodacoes", json=dados_validos())
    assert r.status_code == 400
    assert "fotos" in r.json["campos"]


def test_usuario_que_nao_e_anfitriao_nao_pode_anunciar(cliente):
    """Pré-condição do UC05: o ator é o anfitrião. Carla é só hóspede."""
    entrar(cliente, CARLA)
    r = publicar(cliente)
    assert r.status_code == 403
    assert "anfitrião" in r.json["erro"]


def test_sem_login_retorna_401(cliente):
    r = publicar(cliente)
    assert r.status_code == 401


def test_anuncio_fica_com_o_usuario_logado_e_nao_com_o_enviado(ana):
    """O dono vem da sessão; um campo anfitriao_id no formulário é ignorado."""
    dados = dados_validos()
    dados["anfitriao_id"] = "2"
    r = publicar(ana, dados)
    ids = [a["id"] for a in ana.get("/api/minhas-acomodacoes").json]
    assert r.json["id"] in ids
    assert ana.get(f"/api/acomodacoes/{r.json['id']}").json["anfitriao_id"] == ANA
