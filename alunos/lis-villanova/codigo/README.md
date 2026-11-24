# Cadastro, autenticação e configurações de usuário

Módulo da Plataforma de Hospedagem que implementa a **Seção 4.1** (Cadastro e autenticação de usuários) e a **Seção 5.3** (Segurança da informação) da ERS v1.1. Cobre os casos de uso **UC01** (Cadastrar usuário), **UC02** (Efetuar login), **UC03** (Alterar dados cadastrais) e o **RF-06 / UC04** (Tornar-se anfitrião).

O fluxo do usuário começa quando um visitante cria a conta ou entra na plataforma. Depois ele pode editar nome, telefone e senha e, se quiser, ativar o papel de anfitrião na mesma conta. Todas as regras são verificadas no servidor.

Documentos complementares:

- [RASTREABILIDADE.md](RASTREABILIDADE.md): onde cada requisito foi implementado e como testar, além do que ficou de fora.
- [AMBIGUIDADES.md](AMBIGUIDADES.md): trechos ambíguos, incompletos ou contraditórios da ERS e a decisão tomada em cada um.

## Como rodar

Requer Python 3.10 ou mais recente.

```bash
pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000. O banco `hospedagem.db` é criado na primeira execução, já com as contas de exemplo. Para recomeçar do zero, pare o servidor e apague o arquivo `hospedagem.db`.

Variáveis de ambiente opcionais:

| Variável | Efeito |
|---|---|
| `SECRET_KEY` | Chave que assina o cookie de sessão. Sem ela, o app gera uma chave aleatória a cada início, e reiniciar o servidor encerra todas as sessões. |
| `EMAIL_SIMULAR_FALHA=1` | O serviço de e-mail simulado começa fora do ar. |
| `SESSION_COOKIE_SECURE=1` | O cookie só trafega por HTTPS. Use em produção (Seção 3.4). |
| `FLASK_DEBUG=1` | Modo de depuração do Flask. |

## Como rodar os testes

```bash
python -m pytest
```

São 128 testes: [tests/test_usuarios.py](tests/test_usuarios.py) testa as regras de negócio diretamente e [tests/test_rotas.py](tests/test_rotas.py) testa pelo HTTP (sessão, controle de acesso, códigos de resposta). Cada teste usa um banco SQLite novo numa pasta temporária, nunca o `hospedagem.db` do app. As regras que dependem de tempo (bloqueio de 15 minutos, sessão de 30 minutos, validade dos links) são testadas com um relógio simulado, sem esperar de verdade.

Cobertura medida com `pytest-cov` (que não está no `requirements.txt`): cerca de 94% do código da aplicação, acima dos 70% do RNF-15.

## Contas de exemplo

Todas usam a senha **`Senha123`**.

| E-mail | Situação | Serve para testar |
|---|---|---|
| `ana@exemplo.com` | Hóspede, e-mail confirmado | Login, edição de perfil, troca de senha, tornar-se anfitrião |
| `bruno@exemplo.com` | Hóspede e anfitrião | Conta que já é anfitriã; cadastro com e-mail duplicado |
| `carla@exemplo.com` | **Bloqueada** nos 15 minutos seguintes à criação do banco | Mensagem de conta bloqueada; desbloqueio pela recuperação de senha |
| `diego@exemplo.com` | E-mail **não** confirmado | Aviso de e-mail não confirmado e reenvio da confirmação |

## Sistemas externos simulados

Só o **serviço de e-mail** (Seção 3.3) é usado por este módulo. Ele fica em [servicos/email.py](servicos/email.py) e tem a interface que um serviço real teria, `enviar(destinatario, modelo, dados)`. Em vez de mandar o e-mail, guarda a mensagem numa caixa de saída em memória e imprime um resumo no terminal.

- **Ver os e-mails "enviados":** abra **E-mails (simulação)** no menu (`/emails`). Cada mensagem com link tem o botão **Abrir link**, que equivale a clicar no link do e-mail.
- **Simular sucesso:** é o comportamento padrão.
- **Simular falha (serviço fora do ar):** marque **Simular falha do serviço de e-mail** em `/emails`, ou inicie o app com `EMAIL_SIMULAR_FALHA=1`.
- A caixa de saída fica em memória e é apagada quando o servidor reinicia.
- Em produção a página `/emails` não deve existir: ela expõe os links de todos os usuários. Para desligá-la, crie o app com `create_app({"SIMULACAO_VISIVEL": False})`.

## Telas

| Tela | Endereço | O que faz |
|---|---|---|
| Início | `/` | Boas-vindas; mostra os papéis do usuário logado |
| Cadastrar | `/cadastro` | UC01 |
| Entrar | `/login` | UC02 |
| Recuperar senha | `/recuperar-senha` | RF-04: pede o link |
| Nova senha | `/redefinir-senha?token=...` | RF-04: aberta pelo link do e-mail |
| Confirmação de e-mail | `/confirmar-email?token=...` | UC01: aberta pelo link do e-mail |
| Configurações | `/configuracoes` | UC03, RF-06, RNF-17 (exige login) |
| E-mails (simulação) | `/emails` | Caixa de saída do e-mail simulado |

Todas as telas têm o botão **Ajuda** (Seção 3.1).

## API

Todas as rotas que alteram dados exigem `Content-Type: application/json`, como proteção contra CSRF (ver A-21). Erros voltam como `{"erro": "...", "codigo": "...", "campos": {"campo": "mensagem"}}`.

| Método e rota | Login | Requisito | Respostas |
|---|---|---|---|
| `POST /api/cadastro` | não | RF-01, RF-02, RNF-18 | 201; 409 e-mail duplicado; 422 dados inválidos |
| `POST /api/login` | não | RF-03, RNF-10 | 200; 401 credenciais; 423 conta bloqueada; 422 campos vazios |
| `POST /api/logout` | não | UC02 | 200 |
| `GET /api/me` | sim | — | 200 |
| `PUT /api/perfil` | sim | RF-05 | 200; 422 |
| `PUT /api/perfil/senha` | sim | UC03 | 200; 403 senha atual incorreta; 422 |
| `POST /api/perfil/reenviar-confirmacao` | sim | UC01 | 200; 409 já confirmado; 503 e-mail fora do ar |
| `POST /api/perfil/tornar-anfitriao` | sim | RF-06 | 200; 409 já é anfitrião |
| `POST /api/recuperar-senha` | não | RF-04 | sempre 200 (não revela se a conta existe); 422 e-mail mal formado |
| `POST /api/redefinir-senha` | não | RF-04 | 200; 400 link inválido, usado ou expirado; 422 |
| `GET /api/meus-dados` | sim | RNF-17 | 200, arquivo JSON para download |
| `DELETE /api/conta` | sim | RNF-17 | 200; 403 senha incorreta |

Sem login, as rotas protegidas respondem **401** com o código `NAO_AUTENTICADO`, `SESSAO_EXPIRADA` (RNF-09) ou `SESSAO_INVALIDADA` (senha trocada em outro aparelho ou conta excluída). Nenhuma rota recebe o id do usuário pelo navegador: a conta alterada é sempre a da sessão.

## Como testar cada cenário

O teste automatizado correspondente aparece entre colchetes.

### Cadastro (UC01)

1. **Caminho feliz:** em **Cadastrar**, preencha tudo, marque o aceite dos termos e envie. Aparece "Conta criada". Em **E-mails (simulação)** está o e-mail de confirmação; clique em **Abrir link** e o e-mail fica confirmado. [`test_uc01_cadastro_cria_conta_e_envia_email_de_confirmacao`]
2. **E-mail já cadastrado (4a):** cadastre `bruno@exemplo.com` (ou `BRUNO@exemplo.com`). Aparece o erro com o link **Recuperar senha**. [`test_uc01_4a_email_duplicado_responde_409`, `test_rf02_*`]
3. **Dados inválidos (4b):** envie nome vazio, e-mail sem `@`, telefone `123` e senha `abc`. Cada campo é destacado com sua mensagem e os outros continuam preenchidos. [`test_uc01_4b_*`]
4. **Sem aceitar os termos (RNF-18):** desmarque o aceite. O cadastro é recusado. [`test_rnf18_*`]
5. **E-mail fora do ar:** ligue a falha em `/emails` e cadastre. A conta é criada e um aviso amarelo diz que o e-mail não foi enviado. [`test_uc01_falha_do_email_nao_impede_o_cadastro`]
6. **Link de confirmação usado ou inventado:** abra `/confirmar-email?token=qualquer` ou clique duas vezes no mesmo link. Aparece "Não foi possível confirmar". [`test_uc01_link_*`]

### Login (UC02, RNF-09, RNF-10)

1. **Caminho feliz:** entre com `ana@exemplo.com` / `Senha123`. Abre **Configurações**. [`test_uc02_login_abre_sessao_e_me_nao_expoe_hash`]
2. **Senha incorreta:** use `ana@exemplo.com` com outra senha. Aparece "E-mail ou senha incorretos.", a mesma mensagem de um e-mail inexistente. [`test_rf03_*`]
3. **Bloqueio (RNF-10):** erre a senha de `ana@exemplo.com` 5 vezes seguidas. A 5ª resposta já avisa o bloqueio de 15 minutos, e nem a senha correta entra. A conta `carla@exemplo.com` já começa bloqueada. [`test_rnf10_*`]
4. **Desbloqueio pela recuperação:** com a conta bloqueada, faça a recuperação de senha. Com a senha nova, o login funciona na hora. [`test_rf04_redefinir_desbloqueia_a_conta`]
5. **Sessão expirada (RNF-09):** depois de 30 minutos sem usar o site, qualquer ação leva à tela de entrada com o aviso de sessão expirada. Para não esperar, veja `test_rnf09_*`, que avança o relógio.
6. **Página protegida sem login:** saia e abra `/configuracoes`. Você é levado para **Entrar**. [`test_pagina_de_configuracoes_redireciona_visitante`]

### Recuperação de senha (RF-04)

1. **Caminho feliz:** em **Entrar > Esqueci minha senha**, informe `ana@exemplo.com`. Em `/emails`, abra o link, crie uma senha nova e entre com ela. [`test_rf04_fluxo_completo_pelo_link_do_email`]
2. **E-mail inexistente:** a resposta é a mesma do caso anterior, mas nenhum e-mail é enviado. [`test_rf04_resposta_igual_para_email_existente_e_inexistente`]
3. **Link reutilizado:** use o mesmo link de novo. Aparece "Este link é inválido, já foi usado ou expirou". [`test_rf04_link_so_pode_ser_usado_uma_vez`]
4. **Dois pedidos seguidos:** só o link mais recente funciona. [`test_rf04_novo_pedido_invalida_o_link_anterior`]
5. **Link expirado (1 hora):** [`test_rf04_link_expira_em_1_hora`]

### Configurações (UC03, RF-05)

1. **Alterar nome e telefone:** em **Configurações > Meus dados**, mude e salve. [`test_rf05_*`]
2. **Dados inválidos:** apague o nome e salve. O campo é destacado e nada é gravado. [`test_rf05_dados_invalidos_nao_alteram_nada`]
3. **E-mail não editável:** o campo aparece só para leitura, e o servidor ignora um `email` enviado à API. [`test_rf05_perfil_atualiza_so_nome_e_telefone`]
4. **Alterar senha:** informe a senha atual e a nova. Esta sessão continua, e uma sessão aberta em outro navegador é encerrada. [`test_uc03_troca_de_senha_mantem_esta_sessao_e_derruba_as_outras`]
5. **Senha atual errada:** o campo **Senha atual** é destacado. [`test_uc03_troca_de_senha_com_senha_atual_errada`]
6. **Reenviar confirmação:** entre como `diego@exemplo.com` e clique em **Reenviar e-mail de confirmação**. [`test_uc01_reenviar_confirmacao`]

### Tornar-se anfitrião (RF-06)

1. **Caminho feliz:** entre como `ana@exemplo.com`, vá em **Configurações > Papel de anfitrião** e clique em **Quero ser anfitrião**. A tela passa a mostrar o selo "Anfitrião". [`test_rf06_tornar_se_anfitriao`]
2. **Já é anfitrião:** como `bruno@exemplo.com`, o botão não aparece, e a API responde 409 se for chamada. [`test_rf06_nao_ativa_duas_vezes`]
3. **Conta de outra pessoa:** mandar `usuarioId` de outra conta não tem efeito. [`test_rf06_nao_ativa_anfitriao_de_outra_conta`]

### Privacidade (RNF-17)

1. **Exportar:** **Configurações > Exportar meus dados** baixa `meus-dados.json`, sem o hash da senha. [`test_rnf17_exportar_meus_dados_baixa_arquivo`]
2. **Excluir conta:** informe a senha e confirme. A sessão é encerrada e o e-mail fica livre para um novo cadastro. Com a senha errada, nada acontece. [`test_rnf17_*`]

## Estrutura

```
codigo/
├── app.py              cria o app Flask e a configuração
├── usuarios.py         regras de negócio (sem Flask): validação, cadastro, login, bloqueio, tokens
├── seguranca.py        sessão, expiração por inatividade, login obrigatório, proteção CSRF
├── api.py              rotas JSON
├── paginas.py          rotas das telas
├── database.py         esquema SQLite e conexão
├── dados_exemplo.py    contas de teste
├── tempo.py            relógio único (substituível nos testes)
├── servicos/email.py   serviço de e-mail simulado
├── templates/          HTML (Jinja)
├── static/             CSS e JavaScript puro
└── tests/              pytest
```
