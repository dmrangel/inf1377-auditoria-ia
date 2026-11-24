"""Testes da busca (UC08; RF-12, RF-13, RF-14, RF-15, RF-16; RN-01, RN-02,
RN-04; RNF-05; RNF-06; RF-08; RF-09; RF-10)."""
import pytest

from conftest import dia, ids
from regras import busca as regras_busca

URL = "/api/acomodacoes/busca"


# --------------------------------------------------------------------------- caminho feliz
def test_cenario_demonstracao_lista_somente_disponiveis(buscar):
    r = buscar()
    assert r.status_code == 200
    assert sorted(ids(r)) == [1, 3, 7, 10]
    assert r.get_json()["noites"] == 3


def test_resultado_tem_campos_da_pagina_de_resultados(buscar):
    """ERS 3.1: foto, título, bairro e cidade, precoNoite, nota média."""
    item = next(i for i in buscar().get_json()["itens"] if i["id"] == 1)
    assert item["titulo"] == "Apartamento com vista para o mar"
    assert item["bairro"] == "Copacabana" and item["cidade"] == "Rio de Janeiro"
    assert item["precoNoite"] == 450
    assert item["notaMedia"] == pytest.approx(4.67)
    assert item["totalAvaliacoes"] == 3
    assert item["foto"]["url"].startswith("/arquivos/fotos/1/")


# --------------------------------------------------------------------------- RF-13
def test_rf13_exclui_reserva_confirmada_no_periodo(buscar):
    assert 2 not in ids(buscar())


def test_rf13_capacidade_menor_que_hospedes_e_excluida(buscar):
    assert 4 not in ids(buscar())
    assert 4 in ids(buscar(hospedes="1"))


def test_rf13_capacidade_igual_ao_numero_de_hospedes_aparece(buscar):
    # #1 recebe exatamente 4 pessoas
    assert 1 in ids(buscar(hospedes="4"))
    assert 1 not in ids(buscar(hospedes="5"))


def test_rf10_datas_bloqueadas_pelo_anfitriao_excluem(buscar):
    assert 5 not in ids(buscar())


def test_rn04_pendente_dentro_de_30_min_ocupa(buscar):
    assert 6 not in ids(buscar())


def test_rn04_pendente_vencida_nao_ocupa(buscar):
    assert 7 in ids(buscar())


def test_pendente_vence_exatamente_aos_30_minutos(app, buscar):
    from datetime import timedelta
    from conftest import AGORA
    # reserva 204 do #6 foi criada 10 min antes de AGORA: com +20 min ainda
    # está no limite (30 min) e ocupa; com +21 min já venceu.
    app.config["AGORA"] = AGORA + timedelta(minutes=20)
    assert 6 not in ids(buscar())
    app.config["AGORA"] = AGORA + timedelta(minutes=21)
    assert 6 in ids(buscar())


def test_checkout_no_dia_do_checkin_nao_conflita(buscar):
    """#3 tem reserva que termina no dia do check-in pedido (intervalo semiaberto)."""
    assert 3 in ids(buscar())
    # um dia antes já conflita
    assert 3 not in ids(buscar(checkin=dia(13)))


def test_reserva_cancelada_nao_ocupa(buscar):
    # #2 tem CANCELADA em +10..+12 e CONFIRMADA em +14..+18
    assert 2 in ids(buscar(checkin=dia(10), checkout=dia(12)))


def test_sobreposicao_parcial_conflita(buscar):
    # CONFIRMADA do #2 é +14..+18; pedir +17..+20 sobrepõe uma noite.
    assert 2 not in ids(buscar(checkin=dia(17), checkout=dia(20)))
    assert 2 in ids(buscar(checkin=dia(18), checkout=dia(20)))


# --------------------------------------------------------------------------- publicação
def test_rf09_anuncio_desativado_nao_aparece(buscar):
    assert 8 not in ids(buscar(checkin=dia(60), checkout=dia(61)))


def test_rnf06_denuncia_de_risco_em_analise_oculta(buscar):
    assert 9 not in ids(buscar(checkin=dia(60), checkout=dia(61)))


def test_denuncia_que_nao_e_de_risco_nao_oculta(buscar):
    assert 10 in ids(buscar())


def test_denuncia_de_risco_ja_julgada_nao_oculta(buscar):
    r = buscar(bairro="Ipanema")
    assert ids(r) == [12]


def test_rf08_anuncio_com_menos_de_5_fotos_nao_aparece(buscar):
    assert 11 not in ids(buscar(checkin=dia(60), checkout=dia(61)))


# --------------------------------------------------------------------------- RF-12 localização
def test_rf12_busca_ignora_acentos_e_maiusculas(buscar):
    assert ids(buscar(cidade="SAO PAULO", bairro="pinheiros")) == [15]
    assert sorted(ids(buscar(cidade="rio  de janeiro", bairro="COPACABANA"))) == [1, 3, 7, 10]


def test_rf12_refinar_ate_a_rua(buscar):
    assert ids(buscar(rua="barata ribeiro")) == [10]  # #2 também é nessa rua, mas está ocupado


def test_rf12_busca_so_por_rua_sem_bairro(buscar):
    assert ids(buscar(bairro=None, rua="Atlântica")) == [1]


def test_rf12_rua_com_caracteres_curinga_nao_casa_tudo(buscar):
    assert ids(buscar(rua="%")) == []
    assert ids(buscar(rua="_")) == []


def test_rf12_estado_opcional_filtra(buscar):
    assert ids(buscar(cidade="São Paulo", bairro="Pinheiros", estado="sp")) == [15]
    assert ids(buscar(cidade="São Paulo", bairro="Pinheiros", estado="RJ")) == []


def test_bairro_de_outra_cidade_nao_aparece(buscar):
    r = buscar(cidade="São Paulo", bairro="Copacabana")
    assert r.status_code == 200
    assert r.get_json()["total"] == 0
    assert "Nenhuma acomodação" in r.get_json()["mensagem"]


# --------------------------------------------------------------------------- RNF-05 na busca
def test_rnf05_resultado_nunca_traz_endereco_exato(buscar):
    for r in (buscar(), buscar(rua="Barata Ribeiro")):
        for item in r.get_json()["itens"]:
            assert not {"rua", "numero", "cep"} & set(item)


# --------------------------------------------------------------------------- validação
@pytest.mark.parametrize("extra, campo", [
    ({"cidade": ""}, "cidade"),
    ({"bairro": None, "rua": None}, "bairro"),
    ({"checkin": None}, "checkin"),
    ({"checkout": None}, "checkout"),
    ({"checkin": "31/12/2030"}, "checkin"),
    ({"checkin": "2030-02-30"}, "checkin"),
    ({"hospedes": None}, "hospedes"),
    ({"hospedes": "0"}, "hospedes"),
    ({"hospedes": "-1"}, "hospedes"),
    ({"hospedes": "dois"}, "hospedes"),
    ({"hospedes": "51"}, "hospedes"),
    ({"preco_min": "-10"}, "preco_min"),
    ({"preco_max": "abc"}, "preco_max"),
    ({"preco_max": "inf"}, "preco_max"),
    ({"preco_min": "500", "preco_max": "100"}, "preco_max"),
    ({"quartos": "-1"}, "quartos"),
    ({"camas": "x"}, "camas"),
    ({"ordenar": "aleatorio"}, "ordenar"),
    ({"estado": "Rio"}, "estado"),
    ({"cidade": "x" * 101}, "cidade"),
    ({"pagina": "0"}, "pagina"),
])
def test_parametros_invalidos_retornam_400_com_mensagem(buscar, extra, campo):
    r = buscar(**extra)
    assert r.status_code == 400
    corpo = r.get_json()
    assert campo in corpo["campos"]
    assert corpo["erro"]


def test_rn01_checkout_igual_ao_checkin_e_rejeitado(buscar):
    r = buscar(checkin=dia(14), checkout=dia(14))
    assert r.status_code == 400
    assert "mínimo de 1 noite" in r.get_json()["campos"]["checkout"]


def test_rn01_checkout_antes_do_checkin_e_rejeitado(buscar):
    assert buscar(checkin=dia(14), checkout=dia(12)).status_code == 400


def test_rn01_estadia_de_uma_noite_e_aceita(buscar):
    r = buscar(checkin=dia(30), checkout=dia(31))
    assert r.status_code == 200
    assert r.get_json()["noites"] == 1


def test_checkin_no_passado_e_rejeitado_e_hoje_e_aceito(buscar):
    assert buscar(checkin=dia(-1), checkout=dia(2)).status_code == 400
    assert buscar(checkin=dia(0), checkout=dia(2)).status_code == 200


def test_preco_com_virgula_decimal_e_aceito(buscar):
    r = buscar(preco_max="150,00")
    assert r.status_code == 200
    assert ids(r) == [7]


# --------------------------------------------------------------------------- RF-14 filtros
def test_rf14_faixa_de_preco_inclusiva(buscar):
    assert sorted(ids(buscar(preco_min="280", preco_max="450"))) == [1, 10]
    assert ids(buscar(preco_min="1200")) == [3]
    assert ids(buscar(preco_max="149.99")) == []


def test_rf14_quantidade_minima_de_quartos_banheiros_camas(buscar):
    assert sorted(ids(buscar(quartos="2"))) == [1, 3, 10]
    assert sorted(ids(buscar(banheiros="2"))) == [3, 10]
    assert sorted(ids(buscar(camas="3"))) == [1, 3]
    assert ids(buscar(quartos="2", banheiros="2", camas="3")) == [3]


def test_rf14_filtros_combinados_sem_resultado_tem_mensagem(buscar):
    r = buscar(quartos="5")
    assert r.get_json()["total"] == 0
    assert r.get_json()["mensagem"]


# --------------------------------------------------------------------------- RF-16 ordenação
def test_rf16_ordenar_por_preco(buscar):
    assert ids(buscar(ordenar="preco_asc")) == [7, 10, 1, 3]
    assert ids(buscar(ordenar="preco_desc")) == [3, 1, 10, 7]


def test_rf16_ordenar_por_nota_sem_nota_vai_para_o_fim(buscar):
    # #1 = 4,67; #3 = 4,5; #7 e #10 sem avaliação (desempate por preço)
    assert ids(buscar(ordenar="nota_desc")) == [1, 3, 7, 10]


def test_ordenacao_padrao_e_relevancia(buscar):
    assert ids(buscar()) == ids(buscar(ordenar="relevancia"))


# --------------------------------------------------------------------------- paginação
def test_paginacao(monkeypatch, buscar):
    monkeypatch.setattr(regras_busca, "ITENS_POR_PAGINA", 3)
    p1 = buscar(ordenar="preco_asc").get_json()
    p2 = buscar(ordenar="preco_asc", pagina="2").get_json()
    assert p1["total"] == 4 and p1["totalPaginas"] == 2
    assert [i["id"] for i in p1["itens"]] == [7, 10, 1]
    assert [i["id"] for i in p2["itens"]] == [3]


def test_tempo_de_resposta_e_informado(buscar):
    assert buscar().headers["Server-Timing"].startswith("app;dur=")
