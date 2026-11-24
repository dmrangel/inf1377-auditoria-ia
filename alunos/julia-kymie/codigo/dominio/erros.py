"""Erros de negócio com status HTTP e mensagens em linguagem simples (ERS 3.1)."""


class ErroNegocio(Exception):
    """Erro previsto pelas regras. `campos` mapeia nome do campo -> mensagem,
    para a tela destacar os campos com erro (padrão do UC01, fluxo 4b)."""

    status = 400
    codigo = "ERRO_NEGOCIO"

    def __init__(self, mensagem, campos=None, detalhes=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campos = campos or {}
        self.detalhes = detalhes

    def para_json(self):
        corpo = {"erro": self.mensagem, "codigo": self.codigo}
        if self.campos:
            corpo["campos"] = self.campos
        if self.detalhes is not None:
            corpo["detalhes"] = self.detalhes
        return corpo


class ErroValidacao(ErroNegocio):
    status = 400
    codigo = "DADOS_INVALIDOS"


class NaoAutenticado(ErroNegocio):
    status = 401
    codigo = "NAO_AUTENTICADO"


class AcessoNegado(ErroNegocio):
    status = 403
    codigo = "ACESSO_NEGADO"


class NaoEncontrado(ErroNegocio):
    status = 404
    codigo = "NAO_ENCONTRADO"


class Conflito(ErroNegocio):
    status = 409
    codigo = "CONFLITO"


class ConfirmacaoNecessaria(Conflito):
    """A operação é permitida, mas tem efeito que o anfitrião precisa confirmar."""

    codigo = "CONFIRMACAO_NECESSARIA"


class ServicoIndisponivel(ErroNegocio):
    status = 503
    codigo = "SERVICO_INDISPONIVEL"
