"""
servicos/email.py - Serviço de e-mail SIMULADO.

A ERS (Seção 3.3) define o serviço de e-mail como sistema externo que recebe
"endereço de e-mail e modelo da mensagem". A interface aqui é a mesma:
enviar(destinatario, modelo, dados). Para trocar por um serviço real basta
outra classe com o mesmo método enviar().

Em vez de mandar o e-mail, a simulação:
  - guarda a mensagem numa caixa de saída em memória (vista em /emails);
  - imprime um resumo no terminal do servidor.

Como simular cada resposta:
  - sucesso: comportamento padrão;
  - falha (serviço fora do ar): iniciar com EMAIL_SIMULAR_FALHA=1, ou ligar o
    interruptor na página /emails. enviar() passa a lançar ErroEnvioEmail.
"""

import threading
import uuid

import tempo


class ErroEnvioEmail(Exception):
    """O serviço de e-mail recusou ou não respondeu."""


# Modelos de mensagem: (assunto, corpo). {link} é opcional.
MODELOS = {
    "CONFIRMACAO_CADASTRO": (
        "Confirme seu e-mail",
        "Olá, {nome}! Sua conta foi criada. Para confirmar seu e-mail, abra o link: {link}",
    ),
    "RECUPERACAO_SENHA": (
        "Recuperação de senha",
        "Olá, {nome}. Recebemos um pedido para redefinir sua senha. "
        "O link vale por 1 hora e pode ser usado uma única vez: {link} "
        "Se não foi você, ignore esta mensagem.",
    ),
    "SENHA_ALTERADA": (
        "Sua senha foi alterada",
        "Olá, {nome}. A senha da sua conta acabou de ser alterada. "
        "Se não foi você, recupere o acesso pela opção \"Esqueci minha senha\".",
    ),
    "ANFITRIAO_ATIVADO": (
        "Você agora é anfitrião",
        "Olá, {nome}. O papel de anfitrião foi ativado na sua conta. "
        "Você já pode anunciar espaços.",
    ),
    "CONTA_EXCLUIDA": (
        "Sua conta foi excluída",
        "Olá, {nome}. Conforme solicitado, sua conta e seus dados pessoais foram excluídos.",
    ),
}


class ServicoEmailSimulado:
    def __init__(self, simular_falha=False):
        self.simular_falha = simular_falha
        self._caixa = []
        self._trava = threading.Lock()

    def enviar(self, destinatario, modelo, dados):
        """Envia (simula) a mensagem. Devolve o id da mensagem ou lança ErroEnvioEmail."""
        if self.simular_falha:
            raise ErroEnvioEmail("Serviço de e-mail indisponível (falha simulada).")
        if modelo not in MODELOS:
            raise ValueError(f"Modelo de e-mail desconhecido: {modelo}")
        assunto, corpo = MODELOS[modelo]
        mensagem = {
            "id": uuid.uuid4().hex,
            "para": destinatario,
            "modelo": modelo,
            "assunto": assunto,
            "corpo": corpo.format(link=dados.get("link", ""), nome=dados.get("nome", "")),
            "link": dados.get("link"),
            "enviadoEm": tempo.para_iso(tempo.agora_utc()),
        }
        with self._trava:
            self._caixa.append(mensagem)
        print(f"[e-mail simulado] para={destinatario} assunto={assunto!r}", flush=True)
        return mensagem["id"]

    def listar(self):
        """Mensagens enviadas, da mais recente para a mais antiga."""
        with self._trava:
            return list(reversed(self._caixa))

    def limpar(self):
        with self._trava:
            self._caixa.clear()
