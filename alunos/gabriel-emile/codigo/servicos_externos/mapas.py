"""Serviço de mapas (ERS 3.3) -- SIMULADO.

Na ERS, o serviço de mapas recebe cidade, bairro e coordenadas e serve para
"mostrar a localização aproximada do imóvel" (UC09 no diagrama B.2).

Interface (a mesma que um adaptador real, por exemplo para um provedor de
mapas, teria de implementar):

    localizacao_aproximada(cidade, bairro, estado) -> dict
        {"latitude": float, "longitude": float, "raio_metros": int,
         "descricao": "Bairro, Cidade - UF"}
        Lança LocalNaoEncontrado se o serviço não conhece o local.
        Lança ServicoIndisponivel se o serviço estiver fora do ar.

Importante (RNF-05): o sistema NUNCA envia rua ou número ao serviço de mapas,
só bairro e cidade, então o mapa mostra o centro do bairro e um raio, nunca o
ponto exato do imóvel.

Como simular cada resposta:
  * Sucesso: bairros cadastrados em BAIRROS_CONHECIDOS (ex.: Copacabana, Rio).
  * Local não encontrado: qualquer bairro fora da tabela (o seed tem a
    acomodação "Chalé na Serra", no bairro "Vale das Videiras", que não está).
  * Serviço fora do ar: iniciar o app com a variável de ambiente
    SIMULAR_FALHA_MAPAS=1 (ou app.config["SIMULAR_FALHA_MAPAS"] = True).
"""

from db import normalizar


class ServicoIndisponivel(Exception):
    pass


class LocalNaoEncontrado(Exception):
    pass


# (cidade normalizada, bairro normalizado) -> (lat, lng) do centro do bairro
BAIRROS_CONHECIDOS = {
    ("rio de janeiro", "copacabana"): (-22.9711, -43.1822),
    ("rio de janeiro", "ipanema"): (-22.9838, -43.2096),
    ("rio de janeiro", "leblon"): (-22.9847, -43.2233),
    ("rio de janeiro", "botafogo"): (-22.9519, -43.1840),
    ("rio de janeiro", "gavea"): (-22.9790, -43.2310),
    ("rio de janeiro", "santa teresa"): (-22.9213, -43.1883),
    ("sao paulo", "pinheiros"): (-23.5670, -46.6930),
    ("sao paulo", "vila madalena"): (-23.5530, -46.6910),
    ("sao paulo", "moema"): (-23.6010, -46.6650),
    ("salvador", "barra"): (-13.0090, -38.5320),
}


class ServicoMapasSimulado:
    RAIO_METROS = 800  # raio do círculo "aproximado" desenhado no mapa

    def __init__(self, falhar=False):
        self.falhar = falhar

    def localizacao_aproximada(self, cidade, bairro, estado):
        if self.falhar:
            raise ServicoIndisponivel("Serviço de mapas fora do ar (simulado).")
        chave = (normalizar(cidade), normalizar(bairro))
        if chave not in BAIRROS_CONHECIDOS:
            raise LocalNaoEncontrado(f"Local desconhecido: {bairro}, {cidade}")
        lat, lng = BAIRROS_CONHECIDOS[chave]
        return {
            "latitude": lat,
            "longitude": lng,
            "raio_metros": self.RAIO_METROS,
            "descricao": f"{bairro}, {cidade} - {estado}",
        }
