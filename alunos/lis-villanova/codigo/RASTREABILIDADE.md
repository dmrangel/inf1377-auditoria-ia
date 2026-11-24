# Rastreabilidade

Para cada requisito, regra ou passo de caso de uso da ERS v1.1 relevante para este módulo: onde foi implementado e como testar. Os testes estão em [tests/test_usuarios.py](tests/test_usuarios.py) (regras) e [tests/test_rotas.py](tests/test_rotas.py) (HTTP). O passo a passo manual de cada cenário está no [README](README.md#como-testar-cada-cenário). Os códigos A-xx apontam para [AMBIGUIDADES.md](AMBIGUIDADES.md).

## Requisitos funcionais

| ID | Requisito | Onde foi implementado | Como testar |
|---|---|---|---|
| RF-01 | Cadastro com nome, e-mail, senha e telefone | `usuarios.py`: `cadastrar`, `validar_nome`, `validar_email`, `validar_senha`, `validar_telefone`; `api.py`: `cadastrar`; `templates/cadastro.html`, `static/js/cadastro.js` | `test_rf01_*`, `test_uc01_4b_*` |
| RF-02 | Impedir dois usuários com o mesmo e-mail | `usuarios.py`: `cadastrar` (consulta prévia e captura de `IntegrityError` em caso de corrida), `normalizar_email`; `database.py`: `email UNIQUE COLLATE NOCASE` | `test_rf02_email_duplicado_e_recusado`, `test_rf02_banco_tambem_impede_duplicado`, `test_uc01_4a_email_duplicado_responde_409` |
| RF-03 | Autenticar por e-mail e senha | `usuarios.py`: `autenticar`; `api.py`: `login`, `logout`; `seguranca.py`: `iniciar_sessao`, `carregar_usuario` | `test_rf03_*`, `test_uc02_*`, `test_logout_encerra_a_sessao` |
| RF-04 | Recuperar a senha por link enviado ao e-mail | `usuarios.py`: `solicitar_recuperacao`, `redefinir_senha`, `_criar_token`, `_consumir_token`; `api.py`: `recuperar_senha`, `redefinir_senha`; `templates/recuperar_senha.html`, `templates/redefinir_senha.html` | `test_rf04_*` (os dois arquivos) |
| RF-05 | Editar os dados de perfil | `usuarios.py`: `atualizar_perfil`, `alterar_senha`; `api.py`: `atualizar_perfil`, `alterar_senha`; `templates/configuracoes.html` | `test_rf05_*`, `test_uc03_*` |
| RF-06 | Hóspede ativa o papel de anfitrião na mesma conta | `usuarios.py`: `ativar_anfitriao`; `api.py`: `tornar_anfitriao`; `templates/configuracoes.html` | `test_rf06_*` |

## Casos de uso

| Passo | Descrição | Onde foi implementado | Como testar |
|---|---|---|---|
| UC01 1–2 | Visitante escolhe "Cadastrar" e vê o formulário | `paginas.py`: `cadastro`; `templates/cadastro.html` | `test_telas_publicas_abrem_e_tem_botao_de_ajuda` |
| UC01 3 | Preenche os dados e aceita os termos | `usuarios.py`: `cadastrar` (aceite precisa ser `true`) | `test_rnf18_cadastro_sem_aceite_explicito_e_recusado` |
| UC01 4 | Sistema valida e cria a conta com `dataCadastro` | `usuarios.py`: `cadastrar`, `_validar` | `test_rf01_cadastro_valido_grava_todos_os_campos` |
| UC01 4a | E-mail já cadastrado: informa e oferece a recuperação | `usuarios.py`: `EmailJaCadastrado`; `static/js/cadastro.js` (link "Recuperar senha") | `test_uc01_4a_email_duplicado_responde_409` |
| UC01 4b | Dados inválidos: destaca os campos e mantém os demais | `usuarios.py`: `_validar` devolve todos os erros por campo; `static/js/comum.js`: `mostrarErrosCampos` | `test_uc01_4b_*`; manual: README, Cadastro item 3 |
| UC01 5 | Envia o e-mail de confirmação | `api.py`: `cadastrar`, `_enviar_email`; `servicos/email.py` | `test_uc01_cadastro_cria_conta_e_envia_email_de_confirmacao`, `test_uc01_falha_do_email_nao_impede_o_cadastro` |
| UC01 pós | Link de confirmação confirma o e-mail | `usuarios.py`: `confirmar_email`, `gerar_nova_confirmacao`; `paginas.py`: `confirmar_email`; `api.py`: `reenviar_confirmacao` | `test_uc01_link_*`, `test_uc01_novo_link_*`, `test_uc01_reenviar_*` |
| UC02 | Efetuar login (derivado de RF-03, RNF-09, RNF-10; A-02) | ver RF-03 | ver RF-03, RNF-09, RNF-10 |
| UC03 | Alterar dados cadastrais (derivado de RF-05; A-02) | ver RF-05 | ver RF-05 |
| UC04 | Tornar-se anfitrião | ver RF-06 | ver RF-06 |

## Requisitos não funcionais e interfaces

| ID | Requisito | Onde foi implementado | Como testar |
|---|---|---|---|
| RNF-07 | Senha com hash e salt, nunca em texto puro | `usuarios.py`: `gerar_hash_senha` (scrypt do Werkzeug, A-18) | `test_rnf07_senha_nunca_gravada_em_texto_puro`, `test_rnf07_mesma_senha_gera_hashes_diferentes_salt` |
| RNF-09 | Sessão expira após 30 minutos de inatividade | `seguranca.py`: `carregar_usuario`; `app.py`: `TEMPO_INATIVIDADE` | `test_rnf09_*` |
| RNF-10 | Bloqueio de 15 minutos após 5 tentativas sem sucesso | `usuarios.py`: `autenticar`, `MAX_TENTATIVAS_LOGIN`, `DURACAO_BLOQUEIO` | `test_rnf10_*` (os dois arquivos); manual com `carla@exemplo.com` |
| RNF-11 (por analogia) | Só o dono altera os próprios dados | `api.py`: toda rota usa `g.usuario` da sessão e nunca um id vindo do navegador; `seguranca.py`: `login_obrigatorio` | `test_rf05_cada_usuario_so_altera_a_propria_conta`, `test_rf06_nao_ativa_anfitriao_de_outra_conta`, `test_rotas_protegidas_recusam_visitante` |
| RNF-14 | WCAG 2.1 AA (parcial) | Rótulos em todos os campos, `aria-invalid` e `aria-describedby` nos erros, `aria-live` nas mensagens, foco visível, link para pular ao conteúdo, contraste dos tons principais | Manual; não houve auditoria com ferramenta (ver "Não implementados") |
| RNF-15 | Cobertura de testes de pelo menos 70% | `tests/` | Cerca de 94% do código da aplicação, medido com `pytest --cov=.` (`pytest-cov` instalado à parte) |
| RNF-16 | Telas de 360 px a 1920 px | `static/css/estilo.css` (grade com `auto-fit`, menu que quebra linha) | Manual: redimensionar o navegador |
| RNF-17 | Consultar, exportar e excluir os próprios dados | `usuarios.py`: `exportar_dados`, `excluir_conta`; `api.py`: `exportar_dados`, `excluir_conta`; tela de Configurações | `test_rnf17_*` (os dois arquivos) |
| RNF-18 | Registrar o consentimento com os termos e a política | `usuarios.py`: `cadastrar`, `VERSAO_TERMOS`; colunas `consentimentoTermosEm` e `versaoTermos` | `test_rnf18_*` |
| 3.1 | Botão de ajuda em todas as telas e mensagens simples | `templates/base.html` (diálogo de ajuda) e o bloco `ajuda` de cada tela; mensagens em `usuarios.py` | `test_telas_publicas_abrem_e_tem_botao_de_ajuda` |
| 3.3 | Serviço de e-mail (externo, simulado) | `servicos/email.py`: `ServicoEmailSimulado.enviar`, com os modelos de mensagem | Testes que usam a fixture `caixa`; manual em `/emails` |
| 3.4 | API REST com JSON | `api.py` | Todos os testes de `test_rotas.py` |
| 3.4 | HTTPS com TLS 1.2 ou superior | Só a preparação: `SESSION_COOKIE_SECURE` em `app.py` | Não testável localmente (ver abaixo) |

## Requisitos relevantes que NÃO foram implementados

| ID | Requisito | Por quê |
|---|---|---|
| 3.4 (HTTPS) | Comunicação por HTTPS | O servidor local roda em HTTP. O HTTPS é responsabilidade da implantação (proxy reverso com certificado). O cookie seguro já pode ser ligado por variável de ambiente. |
| 3.4 (push) | Notificações por push no aplicativo móvel | Não há aplicativo móvel neste módulo; os avisos vão só por e-mail. |
| 3.2 | Câmera para a foto do perfil | O RF-01 e o B.4 não têm foto de perfil, e o armazenamento de arquivos é outro sistema externo. |
| RNF-01 a RNF-04 | Desempenho (tempos, 10.000 usuários simultâneos) | Não medidos. O servidor de desenvolvimento do Flask com SQLite não é ambiente para teste de carga. |
| RNF-12 | Disponibilidade de 99,5% | Requisito de operação, não de código. |
| RNF-13 | Novo usuário conclui uma reserva em 5 minutos | Envolve o fluxo de reserva, de outro módulo; exige teste com usuários. |
| RNF-14 | WCAG 2.1 AA completo | Há cuidados básicos (ver acima), mas não houve auditoria com leitor de tela nem com ferramenta automática. |
| RNF-20 | Preparação para outros idiomas | Os textos estão escritos direto em português nos templates e em `usuarios.py`, sem arquivo de tradução. |
| RNF-21 | Backup diário retido por 30 dias | Requisito de operação do banco. |
| RNF-22 | Auditoria de mudanças de status | Vale só para reserva e pagamento, que não existem neste módulo. |
| RF-36 | Bloquear usuário quando a denúncia procede | Depende do módulo de denúncias e de uma coluna que o B.4 não tem (A-22). |
| — | Trocar o e-mail da conta | Decisão A-09: exigiria reconfirmação do endereço novo. |
| — | Desativar o papel de anfitrião | Decisão A-08: a ERS não define o que acontece com anúncios e reservas. |
| — | Limite de requisições por IP (cadastro e recuperação) | A ERS não pede; o risco está registrado em A-21. |
