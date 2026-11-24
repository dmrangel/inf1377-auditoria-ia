# Tabela de rastreabilidade

Legenda das colunas:

- **Onde:** arquivo e função.
- **Teste automatizado:** arquivo e teste em `tests/`.
- **Teste manual:** cenário do [README](README.md#cenários-de-teste-manual).
- `acom.` = `dominio/acomodacoes.py`; `val.` = `dominio/validacao.py`.

## Requisitos funcionais

| ID | Requisito (resumo) | Onde | Teste automatizado | Teste manual |
|---|---|---|---|---|
| RF-07 | Cadastro com título, descrição, preço, capacidade, quartos, banheiros, camas, regras e endereço completo | `acom.criar_acomodacao`; `val.validar_dados_acomodacao`; `rotas/api.py::criar`; `templates/formulario.html`, `static/js/formulario.js` | `test_cadastro.py::test_caminho_feliz_publica_anuncio_com_endereco_do_cep`, `test_campos_obrigatorios_rf07`, `test_valores_invalidos`, `test_formatos_de_preco`, `test_todos_os_erros_aparecem_juntos` | M1, M4 |
| RF-08 | De 5 a 30 fotos por acomodação | `val.validar_quantidade_fotos`, `val.validar_foto`; `acom.criar_acomodacao`, `acom.adicionar_fotos`, `acom.remover_foto` | `test_cadastro.py::test_menos_de_5_fotos_impede_publicacao`, `test_exatamente_30_fotos_e_aceito`, `test_mais_de_30_fotos_e_recusado`; `test_edicao.py::test_adicionar_fotos_nao_passa_de_30`, `test_remover_foto_que_deixaria_menos_de_5_e_bloqueado` | M5, M6, M10, M11 |
| RF-09 (editar) | Anfitrião edita o anúncio | `acom.atualizar_acomodacao`; `rotas/api.py::atualizar` | `test_edicao.py::test_dono_edita_titulo_e_preco`, `test_edicao_valida_campos`, `test_edicao_troca_cep_e_endereco_vem_do_servico`, `test_capacidade_nao_pode_ficar_menor_que_reserva_ativa` | M9, M12 |
| RF-09 (desativar) | Anfitrião desativa o anúncio | `acom.desativar`, `acom.reativar` | `test_edicao.py::test_desativar_sem_reservas_futuras`, `test_desativar_com_reservas_futuras_pede_confirmacao`, `test_desativar_confirmado_mantem_reservas`, `test_reativar` | M13, M14 |
| RF-10 | Bloquear datas no calendário | `acom.bloquear_datas`, `acom.desbloquear_datas`, `acom.calendario`; `val.validar_periodo_bloqueio`; `static/js/calendario.js` | `test_calendario_e_lista.py::test_bloquear_periodo_livre`, `test_nao_bloqueia_noite_com_reserva_ativa`, `test_dia_do_checkout_pode_ser_bloqueado`, `test_nao_bloqueia_data_passada`, `test_limite_de_366_noites`, `test_desbloquear` | M15, M16 |
| RF-11 | Listar ao anfitrião todas as acomodações e reservas recebidas | `acom.listar_do_anfitriao`, `acom.reservas_da_acomodacao`; `static/js/lista.js` | `test_calendario_e_lista.py::test_lista_traz_todas_as_acomodacoes_do_anfitriao_e_so_dele`, `test_lista_traz_reservas_em_todos_os_status`, `test_bruno_ve_so_as_dele`, `test_lista_nao_expoe_contato_do_hospede` | M0 |

## Casos de uso

| Passo | Descrição | Onde | Teste automatizado | Teste manual |
|---|---|---|---|---|
| UC05 pré-condição | Anfitrião está logado | `autenticacao.usuario_atual`; `acom.exigir_anfitriao` | `test_cadastro.py::test_sem_login_retorna_401`, `test_usuario_que_nao_e_anfitriao_nao_pode_anunciar` | M17 |
| UC05 1–2 | "Anunciar espaço" exibe o formulário | `rotas/paginas.py::nova`; `templates/formulario.html` | `test_calendario_e_lista.py::test_paginas_abrem_e_fazem_login_de_teste` | M1 |
| UC05 3 | CEP preenche o endereço | `servicos_externos/cep.py::ServicoCepSimulado.buscar`; `rotas/api.py::consultar_cep`; `acom.resolver_endereco`; `formulario.js::buscarCep` | `test_cadastro.py::test_servico_cep_prevalece_sobre_endereco_digitado`; `test_calendario_e_lista.py::test_consulta_cep` | M1 |
| UC05 3a | CEP não encontrado: preenchimento manual | `acom.resolver_endereco` | `test_cadastro.py::test_cep_nao_encontrado_aceita_endereco_manual`, `test_cep_nao_encontrado_sem_endereco_manual_falha` | M2 |
| UC05 3 (extensão) | Serviço de CEP fora do ar / CEP geral de cidade | `acom.resolver_endereco` | `test_servico_cep_indisponivel_aceita_endereco_manual`, `test_cep_geral_de_cidade_completa_rua_e_bairro_manualmente` | M3 |
| UC05 4 | Dados do espaço | ver RF-07 | ver RF-07 | M1 |
| UC05 5 | Envio das fotos ao armazenamento | `servicos_externos/armazenamento.py`; `acom._gravar_fotos` | `test_cadastro.py::test_jpeg_e_aceito`, `test_foto_que_nao_e_jpeg_nem_png_e_recusada`, `test_foto_maior_que_10mb_e_recusada`, `test_falha_do_armazenamento_nao_deixa_nada_gravado` | M6, M7, M8 |
| UC05 5a | Menos de 5 fotos: impede e informa o mínimo | `val.validar_quantidade_fotos`; `formulario.js::enviar` | `test_cadastro.py::test_menos_de_5_fotos_impede_publicacao` | M5 |
| UC05 6 / pós-condição | Valida, publica e fica visível | `acom.criar_acomodacao` (`ativo = 1`); `acom.anuncios_publicos` | `test_cadastro.py::test_caminho_feliz_publica_anuncio_com_endereco_do_cep` | M1 |
| UC06 | Alterar acomodação (dados, endereço via CEP, fotos via armazenamento) | `acom.atualizar_acomodacao`, `adicionar_fotos`, `remover_foto` | `test_edicao.py` (seção "edição de dados" e "fotos") | M9–M12 |
| UC07 | Remover acomodação (= desativar, A02) | `acom.desativar` | `test_edicao.py` (seção "desativar / reativar") | M13, M14 |

## Interfaces e requisitos não funcionais

| ID | Descrição | Onde | Teste automatizado | Teste manual |
|---|---|---|---|---|
| 3.3 CEP | Serviço de CEP (simulado, mesma interface de um cliente real) | `servicos_externos/cep.py` | `test_calendario_e_lista.py::test_consulta_cep`, `test_cadastro.py::test_cep_invalido` | M1–M3 |
| 3.3 Armazenamento | JPEG/PNG de até 10 MB (simulado) | `servicos_externos/armazenamento.py`; `val.validar_foto`, `val.detectar_tipo_imagem`; `rotas/api.py::servir_arquivo` | `test_cadastro.py::test_foto_de_exatamente_10mb_e_aceita`, `test_foto_maior_que_10mb_e_recusada`; `test_edicao.py::test_arquivo_de_foto_e_servido` | M6–M8 |
| 3.4 | API REST com JSON | `rotas/api.py` | todos os testes de API | — |
| 3.1 | Painel do anfitrião com anúncios e reservas; botão de ajuda em todas as telas; erros em linguagem simples | `templates/base.html` (`#abrir-ajuda`), `lista.html`; `dominio/erros.py` | — (visual) | M0, M18 |
| **RNF-11** | Só o anfitrião dono edita ou vê as reservas | `acom.obter_do_dono`, usado em todas as operações por id | `test_edicao.py::test_outro_anfitriao_nao_edita_nem_ve_reservas` (9 rotas), `test_put_de_outro_anfitriao_nao_altera_nada`, `test_hospede_nao_ve_reservas_da_acomodacao`, `test_bruno_nao_desativa_anuncio_da_ana`; `test_cadastro.py::test_anuncio_fica_com_o_usuario_logado_e_nao_com_o_enviado` | M17 |
| RNF-05 | Antes da confirmação, só o bairro é exibido | `acom.anuncios_publicos` | `test_calendario_e_lista.py::test_vitrine_nao_mostra_endereco_exato_nem_inativos` | M14 |
| RNF-07 | Senhas com hash e salt (só nos dados de exemplo) | `banco.semear` (`generate_password_hash`) | `test_calendario_e_lista.py::test_senhas_dos_exemplos_tem_hash` | — |
| RNF-09 | Sessão expira após 30 min de inatividade | `app.py` (`PERMANENT_SESSION_LIFETIME`, `SESSION_REFRESH_EACH_REQUEST`); `autenticacao.entrar_como` | `test_calendario_e_lista.py::test_sessao_expira_em_30_minutos` | — |
| RNF-14 | WCAG 2.1 AA (parcial) | rótulos em todos os campos, `aria-invalid`/`aria-describedby`, resumo de erros com foco, `aria-live`, link "pular para o conteúdo", contraste ≥ 4,5:1, alvos ≥ 44 px | — (não auditado com ferramenta) | M18 |
| RNF-15 | Cobertura de testes ≥ 70% | `tests/` | `pytest --cov=.` (98% na última execução) | — |
| RNF-16 | Telas de 360 a 1920 px | `static/css/estilo.css` | — (verificado no navegador a 360 px, sem rolagem horizontal) | M18 |
| RN-02 | Hóspedes ≤ capacidade | preservada na edição: `acom.atualizar_acomodacao` | `test_edicao.py::test_capacidade_nao_pode_ficar_menor_que_reserva_ativa` | M12 |
| RF-18 | `valorTotal` gravado na reserva | o preço novo não altera reservas | `test_edicao.py::test_mudar_preco_nao_altera_valor_de_reservas_existentes` | — |
| B.4 | Projeto de tabelas | `schema.sql` (usuario, acomodacao, reserva, historico_status_reserva conforme B.4; foto e bloqueio_data acrescentadas) | todos | — |

## Requisitos relevantes NÃO implementados (ou só em parte)

| ID | Motivo |
|---|---|
| RF-01 a RF-06, UC02 (login real) | Fora do escopo. Login **simulado** (seletor de usuário); as permissões são conferidas no servidor. O RF-06 (tornar-se anfitrião) só é citado na mensagem de 403. |
| RF-12 a RF-16 (busca, filtros, UC08/UC09) | Fora do escopo. Há só uma vitrine mínima para demonstrar o efeito de publicar e desativar (A18). A busca futura deve considerar `ativo = 1` e a tabela `bloqueio_data` (RF-13). |
| RF-17 a RF-22, RN-01, RN-03 a RN-05, RN-07 | Fora do escopo. As reservas existem só como dados de exemplo para RF-11, RF-10 e A03/A12. |
| 3.3 Serviço de mapas | Usado no UC09 (detalhes), fora do escopo; o B.4 não tem coordenadas. |
| 3.2 Câmera | O campo de arquivo aceita imagens, e no celular o sistema oferece a câmera; não há captura direta. |
| 3.4 HTTPS/TLS 1.2+ | O servidor local de desenvolvimento roda em HTTP. Em produção, colocar atrás de um proxy com TLS e ativar `SESSION_COOKIE_SECURE`. |
| 3.4 Notificações push / e-mail | A ERS não pede notificação nesta funcionalidade. **Lacuna:** desativar um anúncio ou mudar o endereço com reservas confirmadas não avisa o hóspede (ver A03/A12). |
| RNF-06* | Ocultar anúncio denunciado durante a análise depende de denúncias (RF-34 a RF-36), fora do escopo. A coluna `ativo` é o mecanismo que o RF-36 usaria. |
| RNF-10 (bloqueio após 5 tentativas de login) | Não há login real. |
| RNF-17 a RNF-19, RNF-21 | LGPD, retenção fiscal e backup são operacionais ou de outras funcionalidades. A exclusão lógica (A02) preserva o histórico exigido pelo RNF-19. |
| RNF-22 (auditoria) | Exige histórico de status de **reserva e pagamento**, que esta funcionalidade não altera. Mudanças em acomodação (editar, desativar, bloquear) **não** são auditadas; a ERS não pede, mas seria recomendável. |
| RNF-01 a RNF-04, RNF-12, RNF-13 | Desempenho, carga e disponibilidade não foram medidos; exigem ambiente de produção. |
| RNF-14 completo | Acessibilidade tratada nas práticas listadas, sem auditoria formal (axe/WAVE, leitor de tela). |
| Reordenar fotos / escolher capa | Não pedido pela ERS. A capa é a primeira foto enviada. |
