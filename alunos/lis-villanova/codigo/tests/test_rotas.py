"""
Testes pelas rotas HTTP: sessão, controle de acesso no servidor, códigos de
resposta e integração com o serviço de e-mail simulado.
"""

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest

import usuarios
from conftest import SENHA, criar_usuario, entrar

DADOS_CADASTRO = {
    "nome": "Ana Teste", "email": "ana@teste.com", "senha": SENHA,
    "telefone": "(21) 99999-8888", "aceitouTermos": True,
}


def _token_do_link(link):
    return parse_qs(urlparse(link).query)["token"][0]


# ---------------------------------------------------------------------------
# UC01 - Cadastro
# ---------------------------------------------------------------------------

def test_uc01_cadastro_cria_conta_e_envia_email_de_confirmacao(client, conn, caixa):
    r = client.post("/api/cadastro", json=DADOS_CADASTRO)
    assert r.status_code == 201
    assert r.get_json()["emailEnviado"] is True
    [msg] = caixa.listar()
    assert msg["para"] == "ana@teste.com"
    assert msg["modelo"] == "CONFIRMACAO_CADASTRO"
    # O link do e-mail confirma a conta (UC01 pós-condição).
    r = client.get(urlparse(msg["link"]).path + "?" + urlparse(msg["link"]).query)
    assert r.status_code == 200
    assert conn.execute("SELECT emailConfirmado FROM usuario").fetchone()[0] == 1


def test_uc01_cadastro_nao_faz_login_automatico(client):
    client.post("/api/cadastro", json=DADOS_CADASTRO)
    assert client.get("/api/me").status_code == 401


def test_uc01_4a_email_duplicado_responde_409(client):
    client.post("/api/cadastro", json=DADOS_CADASTRO)
    r = client.post("/api/cadastro", json={**DADOS_CADASTRO, "email": "ANA@teste.com"})
    assert r.status_code == 409
    assert r.get_json()["codigo"] == "EMAIL_JA_CADASTRADO"
    assert "email" in r.get_json()["campos"]


def test_uc01_4b_campos_invalidos_responde_422_com_campos(client):
    r = client.post("/api/cadastro", json={**DADOS_CADASTRO, "senha": "123", "nome": ""})
    assert r.status_code == 422
    assert set(r.get_json()["campos"]) == {"senha", "nome"}


def test_uc01_falha_do_email_nao_impede_o_cadastro(client, conn, caixa):
    caixa.simular_falha = True
    r = client.post("/api/cadastro", json=DADOS_CADASTRO)
    assert r.status_code == 201
    assert r.get_json()["emailEnviado"] is False
    assert conn.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 1


def test_uc01_link_de_confirmacao_invalido_mostra_erro(client):
    r = client.get("/confirmar-email?token=inventado")
    assert r.status_code == 400


def test_corpo_que_nao_e_objeto_json_e_tratado_como_vazio(client):
    r = client.post("/api/cadastro", json=["lista", "não", "objeto"])
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# UC02 - Login, sessão e RNF-10
# ---------------------------------------------------------------------------

def test_uc02_login_abre_sessao_e_me_nao_expoe_hash(client, conn):
    criar_usuario(conn)
    r = entrar(client)
    assert r.status_code == 200
    me = client.get("/api/me").get_json()["usuario"]
    assert me["email"] == "ana@teste.com"
    assert "senhaHash" not in me


def test_uc02_senha_errada_responde_401(client, conn):
    criar_usuario(conn)
    r = entrar(client, senha="Errada999")
    assert r.status_code == 401
    assert r.get_json()["codigo"] == "CREDENCIAIS_INVALIDAS"
    assert client.get("/api/me").status_code == 401


def test_rnf10_quinta_falha_responde_423(client, conn):
    criar_usuario(conn)
    for _ in range(4):
        assert entrar(client, senha="Errada999").status_code == 401
    r = entrar(client, senha="Errada999")
    assert r.status_code == 423
    assert r.get_json()["codigo"] == "CONTA_BLOQUEADA"
    assert entrar(client).status_code == 423  # nem a senha certa entra


def test_logout_encerra_a_sessao(client, conn):
    criar_usuario(conn)
    entrar(client)
    assert client.post("/api/logout", json={}).status_code == 200
    assert client.get("/api/me").status_code == 401


# ---------------------------------------------------------------------------
# RNF-09 - Sessão expira após 30 minutos de inatividade
# ---------------------------------------------------------------------------

def test_rnf09_sessao_expira_apos_30_minutos_sem_atividade(client, conn, relogio):
    criar_usuario(conn)
    entrar(client)
    relogio.avancar(timedelta(minutes=30, seconds=1))
    r = client.get("/api/me")
    assert r.status_code == 401
    assert r.get_json()["codigo"] == "SESSAO_EXPIRADA"
    # E a sessão foi apagada: voltar no tempo não a ressuscita.
    relogio.avancar(timedelta(minutes=-30))
    assert client.get("/api/me").get_json()["codigo"] == "NAO_AUTENTICADO"


def test_rnf09_atividade_renova_o_prazo(client, conn, relogio):
    criar_usuario(conn)
    entrar(client)
    for _ in range(3):  # 3 x 29 min = 87 min de uso contínuo
        relogio.avancar(timedelta(minutes=29))
        assert client.get("/api/me").status_code == 200


def test_rnf09_pagina_protegida_com_sessao_expirada_redireciona_para_login(client, conn, relogio):
    criar_usuario(conn)
    entrar(client)
    relogio.avancar(timedelta(minutes=31))
    r = client.get("/configuracoes")
    assert r.status_code == 302
    assert "/login?motivo=sessao_expirada" in r.headers["Location"]


# ---------------------------------------------------------------------------
# Controle de acesso no servidor
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("metodo, url", [
    ("GET", "/api/me"), ("PUT", "/api/perfil"), ("PUT", "/api/perfil/senha"),
    ("POST", "/api/perfil/tornar-anfitriao"), ("POST", "/api/perfil/reenviar-confirmacao"),
    ("GET", "/api/meus-dados"), ("DELETE", "/api/conta"),
])
def test_rotas_protegidas_recusam_visitante(client, metodo, url):
    r = client.open(url, method=metodo, json={} if metodo != "GET" else None)
    assert r.status_code == 401
    assert r.get_json()["codigo"] == "NAO_AUTENTICADO"


def test_pagina_de_configuracoes_redireciona_visitante(client):
    r = client.get("/configuracoes")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_cookie_de_sessao_adulterado_e_ignorado(client, conn):
    criar_usuario(conn)
    client.set_cookie("session", "eyJ1c3VhcmlvX2lkIjoxfQ.forjado.assinatura")
    assert client.get("/api/me").status_code == 401


def test_alteracao_sem_json_e_recusada_csrf(client, conn):
    criar_usuario(conn)
    entrar(client)
    # Um formulário HTML de outro site só consegue mandar form-data.
    r = client.post("/api/perfil/tornar-anfitriao", data={"x": "1"})
    assert r.status_code == 415
    assert conn.execute("SELECT ehAnfitriao FROM usuario").fetchone()[0] == 0


# ---------------------------------------------------------------------------
# UC03 / RF-05 - Alterar dados cadastrais
# ---------------------------------------------------------------------------

def test_rf05_perfil_atualiza_so_nome_e_telefone(client, conn):
    uid, _ = criar_usuario(conn)
    entrar(client)
    r = client.put("/api/perfil", json={
        "nome": "Ana Maria", "telefone": "11988887777",
        # Campos que o navegador não pode mudar são ignorados:
        "email": "outro@teste.com", "ehAnfitriao": True, "id": 999,
    })
    assert r.status_code == 200
    u = usuarios.obter(conn, uid)
    assert (u["nome"], u["telefone"], u["email"], u["ehAnfitriao"]) == \
        ("Ana Maria", "11988887777", "ana@teste.com", 0)


def test_rf05_cada_usuario_so_altera_a_propria_conta(app, conn):
    a, _ = criar_usuario(conn, email="a@teste.com", nome="Usuario A")
    b, _ = criar_usuario(conn, email="b@teste.com", nome="Usuario B")
    cliente_a = app.test_client()
    entrar(cliente_a, "a@teste.com")
    cliente_a.put("/api/perfil", json={"nome": "Hackeado", "telefone": "21999998888", "id": b})
    assert usuarios.obter(conn, b)["nome"] == "Usuario B"
    assert usuarios.obter(conn, a)["nome"] == "Hackeado"


def test_uc03_troca_de_senha_mantem_esta_sessao_e_derruba_as_outras(app, conn, caixa):
    criar_usuario(conn)
    aqui, outro_aparelho = app.test_client(), app.test_client()
    entrar(aqui)
    entrar(outro_aparelho)
    r = aqui.put("/api/perfil/senha", json={"senhaAtual": SENHA, "novaSenha": "NovaSenha1"})
    assert r.status_code == 200
    assert aqui.get("/api/me").status_code == 200
    r = outro_aparelho.get("/api/me")
    assert r.status_code == 401 and r.get_json()["codigo"] == "SESSAO_INVALIDADA"
    assert caixa.listar()[0]["modelo"] == "SENHA_ALTERADA"


def test_uc03_troca_de_senha_com_senha_atual_errada(client, conn):
    criar_usuario(conn)
    entrar(client)
    r = client.put("/api/perfil/senha", json={"senhaAtual": "Errada999", "novaSenha": "NovaSenha1"})
    assert r.status_code == 403
    assert "senhaAtual" in r.get_json()["campos"]


def test_uc01_reenviar_confirmacao(client, conn, caixa):
    criar_usuario(conn)
    entrar(client)
    r = client.post("/api/perfil/reenviar-confirmacao", json={})
    assert r.status_code == 200
    link = caixa.listar()[0]["link"]
    assert client.get("/confirmar-email?token=" + _token_do_link(link)).status_code == 200
    assert client.post("/api/perfil/reenviar-confirmacao", json={}).status_code == 409


def test_uc01_reenviar_confirmacao_com_email_fora_do_ar(client, conn, caixa):
    criar_usuario(conn)
    entrar(client)
    caixa.simular_falha = True
    assert client.post("/api/perfil/reenviar-confirmacao", json={}).status_code == 503


# ---------------------------------------------------------------------------
# RF-04 - Recuperação de senha
# ---------------------------------------------------------------------------

def test_rf04_resposta_igual_para_email_existente_e_inexistente(client, conn, caixa):
    criar_usuario(conn)
    existente = client.post("/api/recuperar-senha", json={"email": "ana@teste.com"})
    inexistente = client.post("/api/recuperar-senha", json={"email": "ninguem@teste.com"})
    assert existente.status_code == inexistente.status_code == 200
    assert existente.get_json() == inexistente.get_json()
    assert len(caixa.listar()) == 1  # só a conta real recebe e-mail


def test_rf04_fluxo_completo_pelo_link_do_email(client, conn, caixa):
    criar_usuario(conn)
    client.post("/api/recuperar-senha", json={"email": "ana@teste.com"})
    token = _token_do_link(caixa.listar()[0]["link"])
    assert client.get("/redefinir-senha?token=" + token).status_code == 200
    r = client.post("/api/redefinir-senha", json={"token": token, "novaSenha": "NovaSenha1"})
    assert r.status_code == 200
    assert entrar(client, senha="NovaSenha1").status_code == 200
    r = client.post("/api/redefinir-senha", json={"token": token, "novaSenha": "OutraSenha2"})
    assert r.status_code == 400 and r.get_json()["codigo"] == "LINK_INVALIDO"


# ---------------------------------------------------------------------------
# RF-06 - Tornar-se anfitrião
# ---------------------------------------------------------------------------

def test_rf06_tornar_se_anfitriao(client, conn, caixa):
    uid, _ = criar_usuario(conn)
    entrar(client)
    r = client.post("/api/perfil/tornar-anfitriao", json={})
    assert r.status_code == 200
    assert r.get_json()["usuario"]["ehAnfitriao"] is True
    assert r.get_json()["usuario"]["ehHospede"] is True
    assert usuarios.obter(conn, uid)["ehAnfitriao"] == 1
    assert client.post("/api/perfil/tornar-anfitriao", json={}).status_code == 409


def test_rf06_nao_ativa_anfitriao_de_outra_conta(app, conn):
    criar_usuario(conn, email="a@teste.com")
    b, _ = criar_usuario(conn, email="b@teste.com")
    cliente_a = app.test_client()
    entrar(cliente_a, "a@teste.com")
    cliente_a.post("/api/perfil/tornar-anfitriao", json={"usuarioId": b})
    assert usuarios.obter(conn, b)["ehAnfitriao"] == 0


# ---------------------------------------------------------------------------
# RNF-17 - LGPD
# ---------------------------------------------------------------------------

def test_rnf17_exportar_meus_dados_baixa_arquivo(client, conn):
    criar_usuario(conn)
    entrar(client)
    r = client.get("/api/meus-dados")
    assert r.status_code == 200
    assert "attachment" in r.headers["Content-Disposition"]
    assert r.get_json()["dadosPessoais"]["email"] == "ana@teste.com"


def test_rnf17_excluir_conta_encerra_a_sessao(client, conn):
    uid, _ = criar_usuario(conn)
    entrar(client)
    assert client.delete("/api/conta", json={"senha": "Errada999"}).status_code == 403
    assert client.delete("/api/conta", json={"senha": SENHA}).status_code == 200
    assert usuarios.obter(conn, uid) is None
    assert client.get("/api/me").status_code == 401
    assert entrar(client).status_code == 401


# ---------------------------------------------------------------------------
# Telas e simulação
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", ["/", "/cadastro", "/login", "/recuperar-senha",
                                 "/redefinir-senha?token=x", "/emails"])
def test_telas_publicas_abrem_e_tem_botao_de_ajuda(client, url):
    r = client.get(url)
    assert r.status_code == 200
    assert b'id="botao-ajuda"' in r.data


def test_tela_de_configuracoes_abre_logado(client, conn):
    criar_usuario(conn)
    entrar(client)
    r = client.get("/configuracoes")
    assert r.status_code == 200 and b"Ana Teste" in r.data


def test_login_mostra_somente_mensagens_fixas(client):
    r = client.get("/login?motivo=<script>alert(1)</script>")
    assert b"<script>alert(1)</script>" not in r.data


def test_simulacao_some_quando_desligada(app, client):
    app.config["SIMULACAO_VISIVEL"] = False
    assert client.get("/emails").status_code == 404
    assert client.get("/api/simulacao/emails").status_code == 404


def test_banco_dos_testes_nao_e_o_banco_do_app(app):
    import app as modulo_app
    assert app.config["DATABASE"] != modulo_app.BANCO_PADRAO
