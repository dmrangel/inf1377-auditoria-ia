"""Serviço de CEP (ERS 3.3): "Preencher e validar o endereço da acomodação".

Dados trocados (3.3): CEP -> rua, bairro, cidade, estado.

A classe ServicoCepSimulado imita um cliente de um serviço como o ViaCEP:
recebe um CEP de 8 dígitos e devolve o endereço ou um erro. Nada sai da máquina.

Como simular cada resposta (também descrito no README):

    CEP           Resposta simulada
    22451-900     Encontrado: Rua Marquês de São Vicente, Gávea, Rio de Janeiro/RJ
    22071-001     Encontrado: Avenida Atlântica, Copacabana, Rio de Janeiro/RJ
    01310-100     Encontrado: Avenida Paulista, Bela Vista, São Paulo/SP
    30130-010     Encontrado: Avenida Afonso Pena, Centro, Belo Horizonte/MG
    35400-000     Encontrado SÓ a cidade (CEP geral de município): Ouro Preto/MG,
                  rua e bairro vêm vazios e o anfitrião completa
    99999-999     Serviço indisponível (simula timeout/queda do serviço)
    qualquer outro CEP válido (8 dígitos)   Não encontrado (UC05, fluxo 3a)
    texto que não tenha 8 dígitos           CEP inválido
"""

import re


class CepInvalido(ValueError):
    """O texto informado não é um CEP (8 dígitos)."""


class CepNaoEncontrado(LookupError):
    """O serviço respondeu, mas não conhece o CEP (UC05, fluxo alternativo 3a)."""


class ServicoCepIndisponivel(RuntimeError):
    """O serviço não respondeu (queda ou timeout)."""


def normalizar_cep(cep):
    """Remove pontuação e confere se sobram exatamente 8 dígitos."""
    digitos = re.sub(r"[.\-\s]", "", str(cep or ""))
    if not re.fullmatch(r"\d{8}", digitos):
        raise CepInvalido("O CEP deve ter 8 dígitos, por exemplo 22451-900.")
    return digitos


def formatar_cep(digitos):
    return f"{digitos[:5]}-{digitos[5:]}"


class ServicoCepSimulado:
    """Interface: buscar(cep) -> dict com cep, rua, bairro, cidade, estado."""

    CEP_INDISPONIVEL = "99999999"

    _BASE = {
        "22451900": ("Rua Marquês de São Vicente", "Gávea", "Rio de Janeiro", "RJ"),
        "22071001": ("Avenida Atlântica", "Copacabana", "Rio de Janeiro", "RJ"),
        "01310100": ("Avenida Paulista", "Bela Vista", "São Paulo", "SP"),
        "30130010": ("Avenida Afonso Pena", "Centro", "Belo Horizonte", "MG"),
        # CEP geral de município: o serviço real devolve só cidade e UF.
        "35400000": ("", "", "Ouro Preto", "MG"),
    }

    def buscar(self, cep):
        digitos = normalizar_cep(cep)
        if digitos == self.CEP_INDISPONIVEL:
            raise ServicoCepIndisponivel(
                "O serviço de CEP não respondeu. Preencha o endereço manualmente."
            )
        if digitos not in self._BASE:
            raise CepNaoEncontrado(
                "CEP não encontrado. Preencha o endereço manualmente."
            )
        rua, bairro, cidade, estado = self._BASE[digitos]
        return {
            "cep": formatar_cep(digitos),
            "rua": rua,
            "bairro": bairro,
            "cidade": cidade,
            "estado": estado,
        }
