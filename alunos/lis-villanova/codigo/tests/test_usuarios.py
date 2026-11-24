"""
Testes das regras de negócio (usuarios.py), sem passar por HTTP.
O nome de cada teste começa pelo requisito que ele verifica.
"""

from datetime import timedelta

import pytest

import tempo
import usuarios
from conftest import SENHA, criar_usuario


# ---------------------------------------------------------------------------
# RF-01 / UC01 - Cadastro
# ---------------------------------------------------------------------------

def test_rf01_cadastro_valido_grava_todos_os_campos(conn, relogio):
    uid, token = criar_usuario(conn, email="  Ana@Teste.COM ", telefone="(21) 99999-8888")
    u = usuarios.obter(conn, uid)
    assert u["nome"] == "Ana Teste"
    assert u["email"] == "ana@teste.com"  # normalizado (A-05)
    assert u["telefone"] == "21999998888"  # só dígitos (A-04)
    assert u["dataCadastro"] == tempo.para_iso(relogio.agora)  # UC01 pós-condição
    assert u["ehAnfitriao"] == 0  # A-07: nasce só hóspede
    assert u["emailConfirmado"] == 0
    assert token


def test_rf01_nome_com_espacos_repetidos_e_normalizado(conn):
    uid, _ = criar_usuario(conn, nome="  Ana    Maria  ")
    assert usuarios.obter(conn, uid)["nome"] == "Ana Maria"


@pytest.mark.parametrize("campo, valor", [
    ("nome", ""), ("nome", "A"), ("nome", "x" * 101), ("nome", None), ("nome", 123),
    ("email", ""), ("email", "sem-arroba"), ("email", "a@b"), ("email", "a b@c.com"),
    ("email", "a@" + "b" * 260 + ".com"),
    ("senha", ""), ("senha", "curta1"), ("senha", "somenteletras"), ("senha", "12345678"),
    ("senha", "a1" * 65),
    ("telefone", ""), ("telefone", "123"), ("telefone", "219999988881"), ("telefone", "21abc999988"),
])
def test_uc01_4b_campo_invalido_e_recusado_e_apontado(conn, campo, valor):
    dados = {"nome": "Ana Teste", "email": "ana@teste.com", "senha": SENHA, "telefone": "21999998888"}
    dados[campo] = valor
    with pytest.raises(usuarios.DadosInvalidos) as erro:
        usuarios.cadastrar(conn, dados["nome"], dados["email"], dados["senha"], dados["telefone"], True)
    assert campo in erro.value.campos
    assert conn.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 0


def test_uc01_4b_varios_erros_sao_devolvidos_juntos(conn):
    with pytest.raises(usuarios.DadosInvalidos) as erro:
        usuarios.cadastrar(conn, "", "invalido", "123", "1", False)
    assert set(erro.value.campos) == {"nome", "email", "senha", "telefone", "aceitouTermos"}


def test_rf01_telefone_fixo_com_10_digitos_e_aceito(conn):
    uid, _ = criar_usuario(conn, telefone="(21) 3333-4444")
    assert usuarios.obter(conn, uid)["telefone"] == "2133334444"


# ---------------------------------------------------------------------------
# RNF-18 - Consentimento
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("aceite", [False, None, "true", 1, "sim"])
def test_rnf18_cadastro_sem_aceite_explicito_e_recusado(conn, aceite):
    with pytest.raises(usuarios.DadosInvalidos) as erro:
        usuarios.cadastrar(conn, "Ana Teste", "ana@teste.com", SENHA, "21999998888", aceite)
    assert "aceitouTermos" in erro.value.campos


def test_rnf18_consentimento_registrado_com_data_e_versao(conn, relogio):
    uid, _ = criar_usuario(conn)
    u = usuarios.obter(conn, uid)
    assert u["consentimentoTermosEm"] == tempo.para_iso(relogio.agora)
    assert u["versaoTermos"] == usuarios.VERSAO_TERMOS


# ---------------------------------------------------------------------------
# RF-02 / UC01 4a - E-mail único
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("variacao", ["ana@teste.com", "ANA@TESTE.COM", "  ana@teste.com  "])
def test_rf02_email_duplicado_e_recusado(conn, variacao):
    criar_usuario(conn)
    with pytest.raises(usuarios.EmailJaCadastrado):
        criar_usuario(conn, email=variacao)
    assert conn.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 1


def test_rf02_banco_tambem_impede_duplicado(conn):
    # Defesa em profundidade: mesmo um INSERT direto, sem normalizar, é barrado.
    criar_usuario(conn)
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO usuario (nome, email, senhaHash, telefone, dataCadastro, "
            "consentimentoTermosEm, versaoTermos) VALUES ('X', 'ANA@teste.com', 'h', '1', 'd', 'd', '1')"
        )


# ---------------------------------------------------------------------------
# RNF-07 - Senha com hash e salt
# ---------------------------------------------------------------------------

def test_rnf07_senha_nunca_gravada_em_texto_puro(conn):
    uid, _ = criar_usuario(conn)
    linha = conn.execute("SELECT * FROM usuario WHERE id = ?", (uid,)).fetchone()
    for valor in tuple(linha):
        assert SENHA not in str(valor)
    assert linha["senhaHash"].startswith(("scrypt:", "pbkdf2:"))


def test_rnf07_mesma_senha_gera_hashes_diferentes_salt(conn):
    a, _ = criar_usuario(conn, email="a@teste.com")
    b, _ = criar_usuario(conn, email="b@teste.com")
    assert usuarios.obter(conn, a)["senhaHash"] != usuarios.obter(conn, b)["senhaHash"]


# ---------------------------------------------------------------------------
# UC01 - Confirmação de e-mail
# ---------------------------------------------------------------------------

def test_uc01_link_de_confirmacao_confirma_o_email(conn):
    uid, token = criar_usuario(conn)
    usuarios.confirmar_email(conn, token)
    assert usuarios.obter(conn, uid)["emailConfirmado"] == 1


def test_uc01_link_de_confirmacao_so_vale_uma_vez(conn):
    _, token = criar_usuario(conn)
    usuarios.confirmar_email(conn, token)
    with pytest.raises(usuarios.TokenInvalido):
        usuarios.confirmar_email(conn, token)


def test_uc01_link_de_confirmacao_expira_em_7_dias(conn, relogio):
    _, token = criar_usuario(conn)
    relogio.avancar(timedelta(days=7))
    with pytest.raises(usuarios.TokenInvalido):
        usuarios.confirmar_email(conn, token)


def test_uc01_novo_link_de_confirmacao_invalida_o_anterior(conn):
    uid, antigo = criar_usuario(conn)
    _, novo = usuarios.gerar_nova_confirmacao(conn, uid)
    with pytest.raises(usuarios.TokenInvalido):
        usuarios.confirmar_email(conn, antigo)
    usuarios.confirmar_email(conn, novo)
    with pytest.raises(usuarios.EmailJaConfirmado):
        usuarios.gerar_nova_confirmacao(conn, uid)


def test_uc01_token_de_recuperacao_nao_serve_para_confirmar_email(conn):
    criar_usuario(conn)
    _, token = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    with pytest.raises(usuarios.TokenInvalido):
        usuarios.confirmar_email(conn, token)


def test_uc01_token_gravado_apenas_como_hash(conn):
    _, token = criar_usuario(conn)
    linha = conn.execute("SELECT tokenHash FROM token_usuario").fetchone()
    assert linha["tokenHash"] != token
    assert token not in linha["tokenHash"]


# ---------------------------------------------------------------------------
# RF-03 / UC02 - Login
# ---------------------------------------------------------------------------

def test_rf03_login_com_credenciais_corretas(conn):
    uid, _ = criar_usuario(conn)
    assert usuarios.autenticar(conn, " ANA@teste.com ", SENHA)["id"] == uid


def test_rf03_login_funciona_antes_de_confirmar_email(conn):
    # A-06: confirmar o e-mail não é pré-requisito para entrar.
    uid, _ = criar_usuario(conn)
    assert usuarios.autenticar(conn, "ana@teste.com", SENHA)["id"] == uid


def test_rf03_senha_incorreta_e_recusada(conn):
    criar_usuario(conn)
    with pytest.raises(usuarios.CredenciaisInvalidas):
        usuarios.autenticar(conn, "ana@teste.com", "Errada999")


def test_rf03_email_inexistente_tem_a_mesma_mensagem_da_senha_errada(conn):
    criar_usuario(conn)
    with pytest.raises(usuarios.CredenciaisInvalidas) as a:
        usuarios.autenticar(conn, "ninguem@teste.com", SENHA)
    with pytest.raises(usuarios.CredenciaisInvalidas) as b:
        usuarios.autenticar(conn, "ana@teste.com", "Errada999")
    assert a.value.mensagem == b.value.mensagem


def test_rf03_senha_diferencia_maiusculas(conn):
    criar_usuario(conn)
    with pytest.raises(usuarios.CredenciaisInvalidas):
        usuarios.autenticar(conn, "ana@teste.com", SENHA.upper())


def test_rf03_campos_vazios_sao_recusados(conn):
    with pytest.raises(usuarios.DadosInvalidos):
        usuarios.autenticar(conn, "", "")


# ---------------------------------------------------------------------------
# RNF-10 - Bloqueio após 5 tentativas
# ---------------------------------------------------------------------------

def _errar(conn, vezes):
    for _ in range(vezes):
        with pytest.raises((usuarios.CredenciaisInvalidas, usuarios.ContaBloqueada)):
            usuarios.autenticar(conn, "ana@teste.com", "Errada999")


def test_rnf10_quatro_falhas_nao_bloqueiam(conn, relogio):
    criar_usuario(conn)
    _errar(conn, 4)
    assert usuarios.autenticar(conn, "ana@teste.com", SENHA)


def test_rnf10_quinta_falha_bloqueia_a_conta(conn, relogio):
    criar_usuario(conn)
    _errar(conn, 4)
    with pytest.raises(usuarios.ContaBloqueada):
        usuarios.autenticar(conn, "ana@teste.com", "Errada999")


def test_rnf10_conta_bloqueada_recusa_ate_a_senha_correta(conn, relogio):
    criar_usuario(conn)
    _errar(conn, 5)
    relogio.avancar(timedelta(minutes=14, seconds=59))
    with pytest.raises(usuarios.ContaBloqueada):
        usuarios.autenticar(conn, "ana@teste.com", SENHA)


def test_rnf10_desbloqueia_apos_15_minutos(conn, relogio):
    criar_usuario(conn)
    _errar(conn, 5)
    relogio.avancar(timedelta(minutes=15))
    assert usuarios.autenticar(conn, "ana@teste.com", SENHA)


def test_rnf10_tentativas_durante_o_bloqueio_nao_prolongam_o_bloqueio(conn, relogio):
    criar_usuario(conn)
    _errar(conn, 5)
    relogio.avancar(timedelta(minutes=10))
    _errar(conn, 10)  # todas recusadas como ContaBloqueada, sem contar
    relogio.avancar(timedelta(minutes=5))
    assert usuarios.autenticar(conn, "ana@teste.com", SENHA)


def test_rnf10_login_com_sucesso_zera_o_contador(conn, relogio):
    criar_usuario(conn)
    _errar(conn, 4)
    usuarios.autenticar(conn, "ana@teste.com", SENHA)
    _errar(conn, 4)
    assert usuarios.autenticar(conn, "ana@teste.com", SENHA)


def test_rnf10_apos_o_bloqueio_vencer_o_contador_recomeca(conn, relogio):
    criar_usuario(conn)
    _errar(conn, 5)
    relogio.avancar(timedelta(minutes=15))
    _errar(conn, 4)  # 4 falhas depois do bloqueio ainda não bloqueiam de novo
    assert usuarios.autenticar(conn, "ana@teste.com", SENHA)


def test_rnf10_bloqueio_e_por_conta(conn, relogio):
    criar_usuario(conn)
    criar_usuario(conn, email="bia@teste.com")
    _errar(conn, 5)
    assert usuarios.autenticar(conn, "bia@teste.com", SENHA)


# ---------------------------------------------------------------------------
# RF-04 - Recuperação de senha
# ---------------------------------------------------------------------------

def test_rf04_email_inexistente_nao_gera_link(conn):
    assert usuarios.solicitar_recuperacao(conn, "ninguem@teste.com") is None
    assert conn.execute("SELECT COUNT(*) FROM token_usuario").fetchone()[0] == 0


def test_rf04_email_invalido_e_recusado(conn):
    with pytest.raises(usuarios.DadosInvalidos):
        usuarios.solicitar_recuperacao(conn, "invalido")


def test_rf04_redefinir_com_link_valido_troca_a_senha(conn):
    criar_usuario(conn)
    _, token = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    usuarios.redefinir_senha(conn, token, "NovaSenha1")
    assert usuarios.autenticar(conn, "ana@teste.com", "NovaSenha1")
    with pytest.raises(usuarios.CredenciaisInvalidas):
        usuarios.autenticar(conn, "ana@teste.com", SENHA)


def test_rf04_link_so_pode_ser_usado_uma_vez(conn):
    criar_usuario(conn)
    _, token = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    usuarios.redefinir_senha(conn, token, "NovaSenha1")
    with pytest.raises(usuarios.TokenInvalido):
        usuarios.redefinir_senha(conn, token, "OutraSenha2")


def test_rf04_link_expira_em_1_hora(conn, relogio):
    criar_usuario(conn)
    _, token = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    relogio.avancar(timedelta(hours=1))
    with pytest.raises(usuarios.TokenInvalido):
        usuarios.redefinir_senha(conn, token, "NovaSenha1")


def test_rf04_link_ainda_vale_um_pouco_antes_de_1_hora(conn, relogio):
    criar_usuario(conn)
    _, token = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    relogio.avancar(timedelta(minutes=59, seconds=59))
    usuarios.redefinir_senha(conn, token, "NovaSenha1")


def test_rf04_novo_pedido_invalida_o_link_anterior(conn):
    criar_usuario(conn)
    _, antigo = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    _, novo = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    with pytest.raises(usuarios.TokenInvalido):
        usuarios.redefinir_senha(conn, antigo, "NovaSenha1")
    usuarios.redefinir_senha(conn, novo, "NovaSenha1")


def test_rf04_senha_fraca_nao_gasta_o_link(conn):
    criar_usuario(conn)
    _, token = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    with pytest.raises(usuarios.DadosInvalidos):
        usuarios.redefinir_senha(conn, token, "fraca")
    usuarios.redefinir_senha(conn, token, "NovaSenha1")


@pytest.mark.parametrize("token", ["", None, "inventado", 123])
def test_rf04_link_inventado_e_recusado(conn, token):
    criar_usuario(conn)
    with pytest.raises(usuarios.TokenInvalido):
        usuarios.redefinir_senha(conn, token, "NovaSenha1")


def test_rf04_redefinir_desbloqueia_a_conta(conn, relogio):
    criar_usuario(conn)
    _errar(conn, 5)
    _, token = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    usuarios.redefinir_senha(conn, token, "NovaSenha1")
    assert usuarios.autenticar(conn, "ana@teste.com", "NovaSenha1")


def test_rf04_redefinir_invalida_as_sessoes(conn):
    uid, _ = criar_usuario(conn)
    antes = usuarios.obter(conn, uid)["versaoSessao"]
    _, token = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    usuarios.redefinir_senha(conn, token, "NovaSenha1")
    assert usuarios.obter(conn, uid)["versaoSessao"] == antes + 1


# ---------------------------------------------------------------------------
# RF-05 / UC03 - Alterar dados cadastrais
# ---------------------------------------------------------------------------

def test_rf05_atualiza_nome_e_telefone(conn):
    uid, _ = criar_usuario(conn)
    u = usuarios.atualizar_perfil(conn, uid, "Ana Maria", "(11) 98888-7777")
    assert (u["nome"], u["telefone"]) == ("Ana Maria", "11988887777")


def test_rf05_dados_invalidos_nao_alteram_nada(conn):
    uid, _ = criar_usuario(conn)
    with pytest.raises(usuarios.DadosInvalidos) as erro:
        usuarios.atualizar_perfil(conn, uid, "", "123")
    assert set(erro.value.campos) == {"nome", "telefone"}
    u = usuarios.obter(conn, uid)
    assert (u["nome"], u["telefone"]) == ("Ana Teste", "21999998888")


def test_rf05_usuario_inexistente(conn):
    with pytest.raises(usuarios.UsuarioNaoEncontrado):
        usuarios.atualizar_perfil(conn, 999, "Ana", "21999998888")


def test_uc03_alterar_senha_exige_a_senha_atual(conn):
    uid, _ = criar_usuario(conn)
    with pytest.raises(usuarios.SenhaAtualIncorreta):
        usuarios.alterar_senha(conn, uid, "Errada999", "NovaSenha1")
    assert usuarios.autenticar(conn, "ana@teste.com", SENHA)


def test_uc03_alterar_senha_aplica_a_politica(conn):
    uid, _ = criar_usuario(conn)
    with pytest.raises(usuarios.DadosInvalidos):
        usuarios.alterar_senha(conn, uid, SENHA, "fraca")


def test_uc03_alterar_senha_troca_e_invalida_sessoes(conn):
    uid, _ = criar_usuario(conn)
    nova_versao = usuarios.alterar_senha(conn, uid, SENHA, "NovaSenha1")
    assert nova_versao == 2
    assert usuarios.autenticar(conn, "ana@teste.com", "NovaSenha1")


def test_uc03_alterar_senha_invalida_link_de_recuperacao_pendente(conn):
    uid, _ = criar_usuario(conn)
    _, token = usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    usuarios.alterar_senha(conn, uid, SENHA, "NovaSenha1")
    with pytest.raises(usuarios.TokenInvalido):
        usuarios.redefinir_senha(conn, token, "OutraSenha2")


# ---------------------------------------------------------------------------
# RF-06 / UC04 - Tornar-se anfitrião
# ---------------------------------------------------------------------------

def test_rf06_hospede_ativa_papel_de_anfitriao_na_mesma_conta(conn, relogio):
    uid, _ = criar_usuario(conn)
    u = usuarios.ativar_anfitriao(conn, uid)
    assert u["id"] == uid
    assert u["ehAnfitriao"] == 1
    assert u["dataAtivacaoAnfitriao"] == tempo.para_iso(relogio.agora)
    assert usuarios.dados_publicos(u)["ehHospede"] is True  # continua hóspede


def test_rf06_nao_ativa_duas_vezes(conn, relogio):
    uid, _ = criar_usuario(conn)
    usuarios.ativar_anfitriao(conn, uid)
    data = usuarios.obter(conn, uid)["dataAtivacaoAnfitriao"]
    relogio.avancar(timedelta(days=1))
    with pytest.raises(usuarios.JaEhAnfitriao):
        usuarios.ativar_anfitriao(conn, uid)
    assert usuarios.obter(conn, uid)["dataAtivacaoAnfitriao"] == data


def test_rf06_usuario_inexistente(conn):
    with pytest.raises(usuarios.UsuarioNaoEncontrado):
        usuarios.ativar_anfitriao(conn, 999)


# ---------------------------------------------------------------------------
# RNF-17 (LGPD) - Exportar e excluir
# ---------------------------------------------------------------------------

def test_rnf17_exportacao_traz_os_dados_e_nao_traz_o_hash(conn):
    uid, _ = criar_usuario(conn)
    dados = usuarios.exportar_dados(conn, uid)
    assert dados["dadosPessoais"]["email"] == "ana@teste.com"
    assert dados["consentimento"]["versaoTermos"] == usuarios.VERSAO_TERMOS
    texto = str(dados)
    assert "senhaHash" not in texto
    assert usuarios.obter(conn, uid)["senhaHash"] not in texto


def test_rnf17_exclusao_exige_senha(conn):
    uid, _ = criar_usuario(conn)
    with pytest.raises(usuarios.SenhaAtualIncorreta):
        usuarios.excluir_conta(conn, uid, "Errada999")
    assert usuarios.obter(conn, uid) is not None


def test_rnf17_exclusao_apaga_usuario_e_tokens(conn):
    uid, _ = criar_usuario(conn)
    usuarios.solicitar_recuperacao(conn, "ana@teste.com")
    usuarios.excluir_conta(conn, uid, SENHA)
    assert usuarios.obter(conn, uid) is None
    assert conn.execute("SELECT COUNT(*) FROM token_usuario").fetchone()[0] == 0
    # O e-mail fica livre para um novo cadastro.
    criar_usuario(conn)
