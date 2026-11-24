"""UC06 — Alterar acomodação, UC07 — Remover (desativar), RF-09, RNF-11."""

import io

import pytest

from conftest import (BRUNO, CARLA, COPA, GAVEA, OURO, PAULISTA, arquivos_png, entrar)


def formulario_atual(cliente, acomodacao_id, **mudancas):
    a = cliente.get(f"/api/acomodacoes/{acomodacao_id}").json
    campos = ["titulo", "descricao", "precoNoite", "capacidadeMaxima", "quartos", "banheiros",
              "camas", "regras", "cep", "rua", "numero", "bairro", "cidade", "estado"]
    dados = {c: a[c] for c in campos}
    dados.update(mudancas)
    return dados


# ------------------------------------------------------------------ edição de dados

def test_dono_edita_titulo_e_preco(ana):
    r = ana.put(f"/api/acomodacoes/{COPA}", json=formulario_atual(ana, COPA, titulo="Novo título do anúncio", precoNoite="500,00"))
    assert r.status_code == 200, r.json
    a = ana.get(f"/api/acomodacoes/{COPA}").json
    assert a["titulo"] == "Novo título do anúncio" and a["precoNoiteCentavos"] == 50000


def test_mudar_preco_nao_altera_valor_de_reservas_existentes(ana):
    antes = ana.get(f"/api/acomodacoes/{COPA}/reservas").json
    ana.put(f"/api/acomodacoes/{COPA}", json=formulario_atual(ana, COPA, precoNoite="999,00"))
    depois = ana.get(f"/api/acomodacoes/{COPA}/reservas").json
    assert [r["valorTotal"] for r in antes] == [r["valorTotal"] for r in depois]


def test_edicao_valida_campos(ana):
    r = ana.put(f"/api/acomodacoes/{COPA}", json=formulario_atual(ana, COPA, titulo="", camas="0"))
    assert r.status_code == 400
    assert {"titulo", "camas"} <= set(r.json["campos"])


def test_edicao_troca_cep_e_endereco_vem_do_servico(ana):
    r = ana.put(f"/api/acomodacoes/{COPA}", json=formulario_atual(ana, COPA, cep="01310100", numero="50"))
    assert r.status_code == 200
    a = ana.get(f"/api/acomodacoes/{COPA}").json
    assert (a["cep"], a["rua"], a["cidade"], a["estado"]) == ("01310-100", "Avenida Paulista", "São Paulo", "SP")


def test_capacidade_nao_pode_ficar_menor_que_reserva_ativa(ana):
    """COPA tem reserva CONFIRMADA futura para 4 hóspedes."""
    r = ana.put(f"/api/acomodacoes/{COPA}", json=formulario_atual(ana, COPA, capacidadeMaxima="3"))
    assert r.status_code == 409
    assert "capacidadeMaxima" in r.json["campos"]
    assert ana.put(f"/api/acomodacoes/{COPA}", json=formulario_atual(ana, COPA, capacidadeMaxima="4")).status_code == 200


def test_capacidade_pode_diminuir_se_nao_ha_reserva_ativa(ana):
    assert ana.put(f"/api/acomodacoes/{GAVEA}", json=formulario_atual(ana, GAVEA, capacidadeMaxima="1")).status_code == 200


def test_desativada_ainda_pode_ser_editada(ana):
    r = ana.put(f"/api/acomodacoes/{OURO}", json=formulario_atual(ana, OURO, titulo="Casa colonial em Ouro Preto"))
    assert r.status_code == 200


# ------------------------------------------------------------------ RNF-11

@pytest.mark.parametrize("metodo,url", [
    ("get", f"/api/acomodacoes/{PAULISTA}"),
    ("put", f"/api/acomodacoes/{PAULISTA}"),
    ("get", f"/api/acomodacoes/{PAULISTA}/reservas"),
    ("get", f"/api/acomodacoes/{PAULISTA}/calendario"),
    ("post", f"/api/acomodacoes/{PAULISTA}/desativar"),
    ("post", f"/api/acomodacoes/{PAULISTA}/bloqueios"),
    ("delete", f"/api/acomodacoes/{PAULISTA}/bloqueios"),
    ("post", f"/api/acomodacoes/{PAULISTA}/fotos"),
    ("delete", f"/api/acomodacoes/{PAULISTA}/fotos/30"),
])
def test_outro_anfitriao_nao_edita_nem_ve_reservas(ana, metodo, url):
    """Ana tenta mexer na acomodação de Bruno."""
    r = getattr(ana, metodo)(url, json={"inicio": "2026-12-10", "fim": "2026-12-11"})
    assert r.status_code == 403


def test_put_de_outro_anfitriao_nao_altera_nada(ana, cliente):
    ana.put(f"/api/acomodacoes/{PAULISTA}", json={"titulo": "Invadido"})
    entrar(cliente, BRUNO)
    assert cliente.get(f"/api/acomodacoes/{PAULISTA}").json["titulo"] == "Loft no centro de São Paulo"


def test_hospede_nao_ve_reservas_da_acomodacao(cliente):
    entrar(cliente, CARLA)
    assert cliente.get(f"/api/acomodacoes/{COPA}/reservas").status_code == 403


def test_acomodacao_inexistente_404(ana):
    assert ana.get("/api/acomodacoes/9999").status_code == 404


def test_sem_login_401(cliente):
    assert cliente.get(f"/api/acomodacoes/{COPA}").status_code == 401
    assert cliente.get("/api/minhas-acomodacoes").status_code == 401


# ------------------------------------------------------------------ fotos (UC06 + RF-08)

def test_adicionar_fotos(ana):
    r = ana.post(f"/api/acomodacoes/{GAVEA}/fotos", data={"fotos": arquivos_png(2)}, content_type="multipart/form-data")
    assert r.status_code == 201 and r.json["totalFotos"] == 7


def test_adicionar_fotos_nao_passa_de_30(ana):
    # COPA tem 6; 24 levam a 30 (ok), mais 1 passa
    assert ana.post(f"/api/acomodacoes/{COPA}/fotos", data={"fotos": arquivos_png(24)},
                    content_type="multipart/form-data").status_code == 201
    r = ana.post(f"/api/acomodacoes/{COPA}/fotos", data={"fotos": arquivos_png(1)}, content_type="multipart/form-data")
    assert r.status_code == 400
    assert "máximo é 30" in r.json["erro"]


def test_adicionar_foto_invalida(ana):
    r = ana.post(f"/api/acomodacoes/{GAVEA}/fotos", data={"fotos": [(io.BytesIO(b"texto"), "a.png")]},
                 content_type="multipart/form-data")
    assert r.status_code == 400


def test_adicionar_sem_arquivo(ana):
    assert ana.post(f"/api/acomodacoes/{GAVEA}/fotos", data={}, content_type="multipart/form-data").status_code == 400


def test_remover_foto_que_deixaria_menos_de_5_e_bloqueado(ana):
    """GAVEA tem exatamente 5 fotos."""
    foto = ana.get(f"/api/acomodacoes/{GAVEA}").json["fotos"][0]
    r = ana.delete(f"/api/acomodacoes/{GAVEA}/fotos/{foto['id']}")
    assert r.status_code == 409
    assert "mínimo 5" in r.json["erro"]


def test_remover_foto_com_mais_de_5(ana, app, tmp_path):
    foto = ana.get(f"/api/acomodacoes/{COPA}").json["fotos"][0]
    chave = foto["url"].rsplit("/", 1)[1]
    r = ana.delete(f"/api/acomodacoes/{COPA}/fotos/{foto['id']}")
    assert r.status_code == 200 and r.json["totalFotos"] == 5
    assert not (tmp_path / "arquivos" / chave).exists()  # arquivo apagado do armazenamento


def test_remover_foto_de_outra_acomodacao_404(ana):
    foto_gavea = ana.get(f"/api/acomodacoes/{GAVEA}").json["fotos"][0]
    assert ana.delete(f"/api/acomodacoes/{COPA}/fotos/{foto_gavea['id']}").status_code == 404


def test_arquivo_de_foto_e_servido(ana):
    url = ana.get(f"/api/acomodacoes/{COPA}").json["fotos"][0]["url"]
    r = ana.get(url)
    assert r.status_code == 200 and r.mimetype == "image/png"
    assert ana.get("/arquivos/..%2Fteste.db").status_code == 404


# ------------------------------------------------------------------ desativar / reativar

def test_desativar_sem_reservas_futuras(ana):
    r = ana.post(f"/api/acomodacoes/{GAVEA}/desativar", json={})
    assert r.status_code == 200
    assert not ana.get(f"/api/acomodacoes/{GAVEA}").json["ativo"]
    assert GAVEA not in [a["id"] for a in ana.get("/api/anuncios").json]


def test_desativar_com_reservas_futuras_pede_confirmacao(ana):
    r = ana.post(f"/api/acomodacoes/{COPA}/desativar", json={})
    assert r.status_code == 409 and r.json["codigo"] == "CONFIRMACAO_NECESSARIA"
    assert len(r.json["detalhes"]) == 2  # CONFIRMADA e PENDENTE futuras
    assert ana.get(f"/api/acomodacoes/{COPA}").json["ativo"]  # nada mudou


def test_desativar_confirmado_mantem_reservas(ana):
    antes = ana.get(f"/api/acomodacoes/{COPA}/reservas").json
    r = ana.post(f"/api/acomodacoes/{COPA}/desativar", json={"confirmar": True})
    assert r.status_code == 200 and r.json["reservasMantidas"] == 2
    assert ana.get(f"/api/acomodacoes/{COPA}/reservas").json == antes  # nenhuma cancelada


def test_desativar_ja_desativada(ana):
    assert ana.post(f"/api/acomodacoes/{OURO}/desativar", json={}).status_code == 409


def test_reativar(ana):
    assert ana.post(f"/api/acomodacoes/{OURO}/reativar").status_code == 200
    assert OURO in [a["id"] for a in ana.get("/api/anuncios").json]
    assert ana.post(f"/api/acomodacoes/{OURO}/reativar").status_code == 409


def test_desativada_continua_na_lista_do_anfitriao(ana):
    lista = ana.get("/api/minhas-acomodacoes").json
    ouro = next(a for a in lista if a["id"] == OURO)
    assert ouro["ativo"] is False


def test_bruno_nao_desativa_anuncio_da_ana(cliente):
    entrar(cliente, BRUNO)
    assert cliente.post(f"/api/acomodacoes/{GAVEA}/desativar", json={"confirmar": True}).status_code == 403
