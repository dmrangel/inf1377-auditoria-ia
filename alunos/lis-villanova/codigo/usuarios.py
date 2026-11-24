"""
usuarios.py - Regras de negócio de cadastro, autenticação e configurações de usuário.

Este módulo não conhece Flask nem HTTP: recebe uma conexão SQLite e dados
brutos, valida tudo e grava. As rotas (api.py) só traduzem HTTP <-> estas
funções. Isso deixa as regras testáveis diretamente (tests/test_usuarios.py).

Toda função que depende da hora aceita `agora` opcional para os testes.
Os códigos A-xx nos comentários apontam para AMBIGUIDADES.md.
"""

import hashlib
import re
import secrets
import sqlite3
from datetime import timedelta

from werkzeug.security import check_password_hash, generate_password_hash

import tempo

# ---------------------------------------------------------------------------
# Parâmetros das regras
# ---------------------------------------------------------------------------

VERSAO_TERMOS = "1.0"  # RNF-18 (A-16): versão dos termos que o usuário aceitou

MAX_TENTATIVAS_LOGIN = 5  # RNF-10
DURACAO_BLOQUEIO = timedelta(minutes=15)  # RNF-10

VALIDADE_TOKEN_RECUPERACAO = timedelta(hours=1)  # RF-04 (A-14: a ERS não define)
VALIDADE_TOKEN_CONFIRMACAO = timedelta(days=7)  # UC01 (A-06: a ERS não define)

SENHA_MIN, SENHA_MAX = 8, 128  # A-03
NOME_MIN, NOME_MAX = 2, 100  # A-05
EMAIL_MAX = 254  # limite prático de endereços de e-mail (RFC 5321)

TOKEN_CONFIRMACAO = "CONFIRMACAO_EMAIL"
TOKEN_RECUPERACAO = "RECUPERACAO_SENHA"

MSG_CREDENCIAIS = "E-mail ou senha incorretos."

RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Hash calculado uma vez e usado quando o e-mail não existe no login: assim a
# resposta leva o mesmo tempo que uma senha errada e não denuncia quais
# e-mails estão cadastrados pelo tempo de resposta (A-12).
_HASH_FICTICIO = generate_password_hash("senha-ficticia-para-igualar-o-tempo")


# ---------------------------------------------------------------------------
# Erros de negócio. As rotas convertem cada um em resposta HTTP com o
# status e o código abaixo, e a mensagem vai direto para a tela.
# ---------------------------------------------------------------------------

class ErroNegocio(Exception):
    status = 400
    codigo = "ERRO"

    def __init__(self, mensagem, campos=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        # campo -> mensagem; usado pela tela para destacar cada campo (UC01 4b)
        self.campos = campos or {}


class DadosInvalidos(ErroNegocio):
    status = 422
    codigo = "DADOS_INVALIDOS"


class EmailJaCadastrado(ErroNegocio):
    status = 409
    codigo = "EMAIL_JA_CADASTRADO"


class CredenciaisInvalidas(ErroNegocio):
    status = 401
    codigo = "CREDENCIAIS_INVALIDAS"


class ContaBloqueada(ErroNegocio):
    status = 423
    codigo = "CONTA_BLOQUEADA"


class SenhaAtualIncorreta(ErroNegocio):
    status = 403
    codigo = "SENHA_ATUAL_INCORRETA"


class TokenInvalido(ErroNegocio):
    status = 400
    codigo = "LINK_INVALIDO"


class JaEhAnfitriao(ErroNegocio):
    status = 409
    codigo = "JA_EH_ANFITRIAO"


class EmailJaConfirmado(ErroNegocio):
    status = 409
    codigo = "EMAIL_JA_CONFIRMADO"


class UsuarioNaoEncontrado(ErroNegocio):
    status = 404
    codigo = "USUARIO_NAO_ENCONTRADO"


# ---------------------------------------------------------------------------
# Validação e normalização de campos
# Cada validador devolve (valor_normalizado, mensagem_de_erro_ou_None).
# ---------------------------------------------------------------------------

def _texto(valor):
    """Aceita só strings; qualquer outro tipo vindo do JSON vira texto vazio."""
    return valor if isinstance(valor, str) else ""


def normalizar_email(email):
    # A-05: e-mail comparado sem diferenciar maiúsculas e sem espaços nas pontas.
    return _texto(email).strip().lower()


def validar_nome(nome):
    # A-05: espaços repetidos viram um só; 2 a 100 caracteres.
    valor = " ".join(_texto(nome).split())
    if not valor:
        return valor, "Informe o seu nome."
    if len(valor) < NOME_MIN or len(valor) > NOME_MAX:
        return valor, f"O nome deve ter entre {NOME_MIN} e {NOME_MAX} caracteres."
    return valor, None


def validar_email(email):
    valor = normalizar_email(email)
    if not valor:
        return valor, "Informe o seu e-mail."
    if len(valor) > EMAIL_MAX or not RE_EMAIL.match(valor):
        return valor, "Informe um e-mail válido, por exemplo nome@exemplo.com."
    return valor, None


def validar_telefone(telefone):
    # A-04: telefone brasileiro com DDD, 10 (fixo) ou 11 (celular) dígitos.
    # Pontuação é aceita na entrada e removida; grava-se só os dígitos.
    bruto = _texto(telefone).strip()
    digitos = re.sub(r"\D", "", bruto)
    if not bruto:
        return digitos, "Informe o seu telefone."
    if re.search(r"[^\d\s()+\-.]", bruto) or len(digitos) not in (10, 11):
        return digitos, "Informe o telefone com DDD, por exemplo (21) 99999-8888."
    return digitos, None


def validar_senha(senha):
    # A-03: a ERS não define política de senha. Adotado: 8 a 128 caracteres,
    # com pelo menos uma letra e um número. A senha não é alterada (sem strip).
    valor = _texto(senha)
    if not valor:
        return valor, "Informe uma senha."
    if len(valor) < SENHA_MIN or len(valor) > SENHA_MAX:
        return valor, f"A senha deve ter entre {SENHA_MIN} e {SENHA_MAX} caracteres."
    if not re.search(r"[A-Za-zÀ-ÿ]", valor) or not re.search(r"\d", valor):
        return valor, "A senha deve ter pelo menos uma letra e um número."
    return valor, None


def _validar(**campos):
    """Roda vários validadores e junta todos os erros, para a tela mostrar tudo de uma vez."""
    valores, erros = {}, {}
    for nome_campo, (validador, valor) in campos.items():
        normalizado, erro = validador(valor)
        valores[nome_campo] = normalizado
        if erro:
            erros[nome_campo] = erro
    if erros:
        raise DadosInvalidos("Corrija os campos destacados.", erros)
    return valores


def gerar_hash_senha(senha):
    # RNF-07: hash com salt aleatório por usuário. O Werkzeug usa scrypt e
    # embute o salt no próprio texto do hash (A-18).
    return generate_password_hash(senha)


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def obter(conn, usuario_id):
    return conn.execute("SELECT * FROM usuario WHERE id = ?", (usuario_id,)).fetchone()


def _obter_ou_erro(conn, usuario_id):
    usuario = obter(conn, usuario_id)
    if usuario is None:
        raise UsuarioNaoEncontrado("Conta não encontrada.")
    return usuario


def dados_publicos(usuario):
    """Dados do próprio usuário que podem ir para a tela. Nunca inclui senhaHash."""
    return {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "telefone": usuario["telefone"],
        "dataCadastro": usuario["dataCadastro"],
        "emailConfirmado": bool(usuario["emailConfirmado"]),
        "ehHospede": True,  # A-07: toda conta é de hóspede
        "ehAnfitriao": bool(usuario["ehAnfitriao"]),
        "dataAtivacaoAnfitriao": usuario["dataAtivacaoAnfitriao"],
    }


# ---------------------------------------------------------------------------
# Tokens dos links enviados por e-mail
# ---------------------------------------------------------------------------

def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _criar_token(conn, usuario_id, tipo, validade, agora):
    """Cria um token novo e invalida os anteriores do mesmo tipo (só o último link vale)."""
    conn.execute(
        "UPDATE token_usuario SET usadoEm = ? "
        "WHERE usuario_id = ? AND tipo = ? AND usadoEm IS NULL",
        (tempo.para_iso(agora), usuario_id, tipo),
    )
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO token_usuario (usuario_id, tipo, tokenHash, criadoEm, expiraEm) "
        "VALUES (?, ?, ?, ?, ?)",
        (usuario_id, tipo, _hash_token(token), tempo.para_iso(agora),
         tempo.para_iso(agora + validade)),
    )
    return token


def _consumir_token(conn, token, tipo, agora):
    """Valida o token (tipo, não usado, não expirado), marca como usado e devolve o usuario_id."""
    msg = "Este link é inválido, já foi usado ou expirou. Peça um novo."
    if not isinstance(token, str) or not token:
        raise TokenInvalido(msg)
    linha = conn.execute(
        "SELECT * FROM token_usuario WHERE tokenHash = ? AND tipo = ?",
        (_hash_token(token), tipo),
    ).fetchone()
    if linha is None or linha["usadoEm"] is not None or agora >= tempo.de_iso(linha["expiraEm"]):
        raise TokenInvalido(msg)
    # Marca como usado só se ainda não foi (protege contra dois cliques simultâneos).
    cur = conn.execute(
        "UPDATE token_usuario SET usadoEm = ? WHERE id = ? AND usadoEm IS NULL",
        (tempo.para_iso(agora), linha["id"]),
    )
    if cur.rowcount != 1:
        raise TokenInvalido(msg)
    return linha["usuario_id"]


# ---------------------------------------------------------------------------
# UC01 / RF-01 / RF-02 / RNF-07 / RNF-18 - Cadastrar usuário
# ---------------------------------------------------------------------------

def cadastrar(conn, nome, email, senha, telefone, aceitou_termos, agora=None):
    """
    Cria a conta e devolve (usuario_id, token_de_confirmacao).
    Quem chama é responsável por enviar o e-mail de confirmação (UC01 passo 5).
    """
    agora = agora or tempo.agora_utc()
    erros = {}
    try:
        valores = _validar(
            nome=(validar_nome, nome),
            email=(validar_email, email),
            senha=(validar_senha, senha),
            telefone=(validar_telefone, telefone),
        )
    except DadosInvalidos as e:
        erros.update(e.campos)
        valores = None
    # RNF-18 / UC01 passo 3: sem aceite explícito dos termos não há cadastro.
    # Só o booleano true vale; "sim", 1 etc. são recusados.
    if aceitou_termos is not True:
        erros["aceitouTermos"] = "É preciso aceitar os termos de uso e a política de privacidade."
    if erros:
        raise DadosInvalidos("Corrija os campos destacados.", erros)

    # RF-02 / UC01 4a: e-mail já cadastrado. A mensagem revela que o e-mail
    # existe porque o próprio UC01 4a manda informar e oferecer recuperação (A-12).
    existente = conn.execute(
        "SELECT 1 FROM usuario WHERE email = ?", (valores["email"],)
    ).fetchone()
    if existente:
        raise EmailJaCadastrado(
            "Já existe uma conta com este e-mail. Se for sua, recupere a senha.",
            {"email": "E-mail já cadastrado."},
        )

    agora_iso = tempo.para_iso(agora)
    try:
        cur = conn.execute(
            "INSERT INTO usuario (nome, email, senhaHash, telefone, dataCadastro, "
            "ehAnfitriao, emailConfirmado, consentimentoTermosEm, versaoTermos) "
            "VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)",
            (valores["nome"], valores["email"], gerar_hash_senha(valores["senha"]),
             valores["telefone"], agora_iso, agora_iso, VERSAO_TERMOS),
        )
    except sqlite3.IntegrityError as e:
        # Corrida: outro cadastro com o mesmo e-mail entrou entre o SELECT e o INSERT.
        conn.rollback()
        raise EmailJaCadastrado(
            "Já existe uma conta com este e-mail. Se for sua, recupere a senha.",
            {"email": "E-mail já cadastrado."},
        ) from e
    usuario_id = cur.lastrowid
    token = _criar_token(conn, usuario_id, TOKEN_CONFIRMACAO, VALIDADE_TOKEN_CONFIRMACAO, agora)
    conn.commit()
    return usuario_id, token


def confirmar_email(conn, token, agora=None):
    """Marca o e-mail como confirmado a partir do link enviado no cadastro (UC01 pós-condição)."""
    agora = agora or tempo.agora_utc()
    usuario_id = _consumir_token(conn, token, TOKEN_CONFIRMACAO, agora)
    conn.execute("UPDATE usuario SET emailConfirmado = 1 WHERE id = ?", (usuario_id,))
    conn.commit()
    return obter(conn, usuario_id)


def gerar_nova_confirmacao(conn, usuario_id, agora=None):
    """Gera um novo link de confirmação (o anterior deixa de valer)."""
    agora = agora or tempo.agora_utc()
    usuario = _obter_ou_erro(conn, usuario_id)
    if usuario["emailConfirmado"]:
        raise EmailJaConfirmado("Seu e-mail já está confirmado.")
    token = _criar_token(conn, usuario_id, TOKEN_CONFIRMACAO, VALIDADE_TOKEN_CONFIRMACAO, agora)
    conn.commit()
    return usuario, token


# ---------------------------------------------------------------------------
# UC02 / RF-03 / RNF-10 - Efetuar login
# ---------------------------------------------------------------------------

def _mensagem_bloqueio(ate, agora):
    minutos = max(1, -(-int((ate - agora).total_seconds()) // 60))  # arredonda para cima
    return (
        "Conta bloqueada temporariamente após 5 tentativas de login sem sucesso. "
        f"Tente novamente em {minutos} minuto(s) ou recupere a senha."
    )


def autenticar(conn, email, senha, agora=None):
    """
    Devolve a linha do usuário se e-mail e senha conferem.

    RNF-10 (A-11): 5 falhas seguidas bloqueiam a conta por 15 minutos. Durante
    o bloqueio nem a senha correta entra e as tentativas não prolongam o
    bloqueio. Um login com sucesso zera o contador.
    """
    agora = agora or tempo.agora_utc()
    email_n = normalizar_email(email)
    senha = _texto(senha)
    if not email_n or not senha:
        raise DadosInvalidos(
            "Informe e-mail e senha.",
            {k: "Campo obrigatório." for k, v in (("email", email_n), ("senha", senha)) if not v},
        )

    usuario = conn.execute("SELECT * FROM usuario WHERE email = ?", (email_n,)).fetchone()
    if usuario is None:
        check_password_hash(_HASH_FICTICIO, senha)  # mesmo custo de tempo (A-12)
        raise CredenciaisInvalidas(MSG_CREDENCIAIS)

    if usuario["bloqueadoAte"]:
        ate = tempo.de_iso(usuario["bloqueadoAte"])
        if agora < ate:
            # A senha nem é conferida: durante o bloqueio não há como testar senhas.
            raise ContaBloqueada(_mensagem_bloqueio(ate, agora))
        # Bloqueio venceu: limpa e segue o login normalmente.
        conn.execute(
            "UPDATE usuario SET bloqueadoAte = NULL, tentativasFalhas = 0 WHERE id = ?",
            (usuario["id"],),
        )
        conn.commit()

    if not check_password_hash(usuario["senhaHash"], senha):
        # Incremento atômico no banco, para dois logins simultâneos não perderem contagem.
        conn.execute(
            "UPDATE usuario SET tentativasFalhas = tentativasFalhas + 1 WHERE id = ?",
            (usuario["id"],),
        )
        falhas = conn.execute(
            "SELECT tentativasFalhas FROM usuario WHERE id = ?", (usuario["id"],)
        ).fetchone()[0]
        if falhas >= MAX_TENTATIVAS_LOGIN:
            ate = agora + DURACAO_BLOQUEIO
            # O contador volta a zero: depois do bloqueio, mais 5 tentativas.
            conn.execute(
                "UPDATE usuario SET bloqueadoAte = ?, tentativasFalhas = 0 WHERE id = ?",
                (tempo.para_iso(ate), usuario["id"]),
            )
            conn.commit()
            raise ContaBloqueada(_mensagem_bloqueio(ate, agora))
        conn.commit()
        raise CredenciaisInvalidas(MSG_CREDENCIAIS)

    conn.execute(
        "UPDATE usuario SET tentativasFalhas = 0, bloqueadoAte = NULL WHERE id = ?",
        (usuario["id"],),
    )
    conn.commit()
    return obter(conn, usuario["id"])


# ---------------------------------------------------------------------------
# RF-04 - Recuperação de senha por link enviado ao e-mail
# ---------------------------------------------------------------------------

def solicitar_recuperacao(conn, email, agora=None):
    """
    Devolve (usuario, token) se o e-mail existe, ou None se não existe.
    A rota responde a mesma coisa nos dois casos, para não revelar quais
    e-mails têm conta (A-12).
    """
    agora = agora or tempo.agora_utc()
    email_n, erro = validar_email(email)
    if erro:
        raise DadosInvalidos("Corrija os campos destacados.", {"email": erro})
    usuario = conn.execute("SELECT * FROM usuario WHERE email = ?", (email_n,)).fetchone()
    if usuario is None:
        return None
    token = _criar_token(conn, usuario["id"], TOKEN_RECUPERACAO, VALIDADE_TOKEN_RECUPERACAO, agora)
    conn.commit()
    return usuario, token


def redefinir_senha(conn, token, nova_senha, agora=None):
    """
    Troca a senha usando o link de recuperação.
    A-14: o link vale 1 hora e uma única vez. Redefinir a senha também
    desbloqueia a conta (quem tem acesso ao e-mail provou ser o dono) e
    encerra as sessões abertas em outros aparelhos.
    """
    agora = agora or tempo.agora_utc()
    # Valida a senha antes de consumir o token: senha fraca não gasta o link.
    valores = _validar(novaSenha=(validar_senha, nova_senha))
    usuario_id = _consumir_token(conn, token, TOKEN_RECUPERACAO, agora)
    conn.execute(
        "UPDATE usuario SET senhaHash = ?, tentativasFalhas = 0, bloqueadoAte = NULL, "
        "versaoSessao = versaoSessao + 1 WHERE id = ?",
        (gerar_hash_senha(valores["novaSenha"]), usuario_id),
    )
    conn.commit()
    return obter(conn, usuario_id)


# ---------------------------------------------------------------------------
# UC03 / RF-05 - Alterar dados cadastrais
# ---------------------------------------------------------------------------

def atualizar_perfil(conn, usuario_id, nome, telefone):
    """
    A-09: são editáveis nome e telefone. O e-mail é o login e a chave única
    (RF-02); trocá-lo exigiria reconfirmação, então fica fora desta versão.
    """
    _obter_ou_erro(conn, usuario_id)
    valores = _validar(nome=(validar_nome, nome), telefone=(validar_telefone, telefone))
    conn.execute(
        "UPDATE usuario SET nome = ?, telefone = ? WHERE id = ?",
        (valores["nome"], valores["telefone"], usuario_id),
    )
    conn.commit()
    return obter(conn, usuario_id)


def alterar_senha(conn, usuario_id, senha_atual, nova_senha):
    """
    A-10: exige a senha atual. Devolve a nova versaoSessao: a rota atualiza a
    sessão de quem fez a troca e todas as outras sessões deixam de valer.
    """
    usuario = _obter_ou_erro(conn, usuario_id)
    if not check_password_hash(usuario["senhaHash"], _texto(senha_atual)):
        raise SenhaAtualIncorreta(
            "A senha atual está incorreta.", {"senhaAtual": "Senha atual incorreta."}
        )
    valores = _validar(novaSenha=(validar_senha, nova_senha))
    conn.execute(
        "UPDATE usuario SET senhaHash = ?, versaoSessao = versaoSessao + 1 WHERE id = ?",
        (gerar_hash_senha(valores["novaSenha"]), usuario_id),
    )
    # Links de recuperação pendentes deixam de valer depois de uma troca de senha.
    conn.execute(
        "UPDATE token_usuario SET usadoEm = ? WHERE usuario_id = ? AND tipo = ? AND usadoEm IS NULL",
        (tempo.para_iso(tempo.agora_utc()), usuario_id, TOKEN_RECUPERACAO),
    )
    conn.commit()
    return obter(conn, usuario_id)["versaoSessao"]


# ---------------------------------------------------------------------------
# RF-06 / UC04 - Tornar-se anfitrião
# ---------------------------------------------------------------------------

def ativar_anfitriao(conn, usuario_id, agora=None):
    """
    A-08: ativa o papel de anfitrião na mesma conta. Não há pré-requisito na
    ERS e a ativação não pode ser desfeita nesta versão.
    """
    agora = agora or tempo.agora_utc()
    _obter_ou_erro(conn, usuario_id)
    # O WHERE ehAnfitriao = 0 torna a operação atômica: duas ativações
    # simultâneas não gravam duas datas diferentes.
    cur = conn.execute(
        "UPDATE usuario SET ehAnfitriao = 1, dataAtivacaoAnfitriao = ? "
        "WHERE id = ? AND ehAnfitriao = 0",
        (tempo.para_iso(agora), usuario_id),
    )
    if cur.rowcount == 0:
        raise JaEhAnfitriao("Sua conta já tem o papel de anfitrião.")
    conn.commit()
    return obter(conn, usuario_id)


# ---------------------------------------------------------------------------
# RNF-17 (LGPD) - consultar, exportar e excluir os próprios dados
# ---------------------------------------------------------------------------

def exportar_dados(conn, usuario_id, agora=None):
    """
    Exporta os dados pessoais guardados sobre o usuário. A-15: o hash da senha
    e os contadores de segurança não são dados úteis ao titular e expô-los
    facilitaria ataques, por isso ficam de fora.
    """
    agora = agora or tempo.agora_utc()
    usuario = _obter_ou_erro(conn, usuario_id)
    return {
        "exportadoEm": tempo.para_iso(agora),
        "dadosPessoais": {
            "nome": usuario["nome"],
            "email": usuario["email"],
            "telefone": usuario["telefone"],
            "dataCadastro": usuario["dataCadastro"],
            "emailConfirmado": bool(usuario["emailConfirmado"]),
        },
        "papeis": {
            "hospede": True,
            "anfitriao": bool(usuario["ehAnfitriao"]),
            "dataAtivacaoAnfitriao": usuario["dataAtivacaoAnfitriao"],
        },
        "consentimento": {
            "termosDeUsoEPoliticaDePrivacidade": True,
            "versaoTermos": usuario["versaoTermos"],
            "aceitoEm": usuario["consentimentoTermosEm"],
        },
    }


def excluir_conta(conn, usuario_id, senha):
    """
    Exclui a conta depois de confirmar a senha. Devolve (nome, email) para a
    rota enviar o aviso por e-mail.

    A-15: aqui só existem as tabelas usuario e token_usuario, então a exclusão
    é definitiva. Integrada às reservas e pagamentos, ela teria de anonimizar
    em vez de apagar, por causa do RNF-19 (pagamentos guardados por 5 anos).
    """
    usuario = _obter_ou_erro(conn, usuario_id)
    if not check_password_hash(usuario["senhaHash"], _texto(senha)):
        raise SenhaAtualIncorreta("Senha incorreta.", {"senha": "Senha incorreta."})
    conn.execute("DELETE FROM usuario WHERE id = ?", (usuario_id,))  # tokens: ON DELETE CASCADE
    conn.commit()
    return usuario["nome"], usuario["email"]
