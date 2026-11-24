# Tabela de rastreabilidade

Funcionalidade: **busca e visualização de acomodações** (ERS v1.2, seção 4.3, RNF-01, RNF-05, UC08, UC09).
Caminhos relativos a `codigo/`. "Teste" indica o teste pytest automatizado; "Manual" indica o roteiro do [README](README.md#roteiro-de-testes-manuais).

## Requisitos implementados

| ID | Requisito (resumo) | Onde foi implementado | Como testar |
|---|---|---|---|
| **RF-12** | Buscar por localização (bairro e cidade, refinável até a rua), período e nº de hóspedes | `regras/busca.py` → `validar_parametros`, `buscar`; `db.py` → `normalizar` (função SQL `norm`); `paginas/index.html`, `static/js/inicio.js` | Teste: `test_busca.py::test_rf12_*`, `test_cenario_demonstracao_lista_somente_disponiveis`. Manual: M1, M3 |
| **RF-13** | Só acomodações livres no período e com capacidadeMaxima ≥ hóspedes | `regras/disponibilidade.py` → `sql_livre_no_periodo`, `sql_reserva_ocupa`; `regras/busca.py` → `buscar` (filtro de capacidade) | Teste: `test_busca.py::test_rf13_*`, `test_checkout_no_dia_do_checkin_nao_conflita`, `test_reserva_cancelada_nao_ocupa`, `test_sobreposicao_parcial_conflita`. Manual: M1 |
| **RF-14** | Filtrar por faixa de preço e por quartos, banheiros e camas | `regras/busca.py` → `validar_parametros`, `buscar`; `paginas/resultados.html`, `static/js/resultados.js` | Teste: `test_busca.py::test_rf14_*`, `test_preco_com_virgula_decimal_e_aceito`. Manual: M2 |
| **RF-15** | Exibir nota média e comentários de cada acomodação | `regras/avaliacoes.py` → `sql_notas_por_acomodacao`, `resumo_notas`, `listar_avaliacoes_publicas`; `rotas.py` → `listar_avaliacoes`; `static/js/anuncio.js` → `carregarAvaliacoes` | Teste: `test_avaliacoes.py` (todo o arquivo), `test_busca.py::test_resultado_tem_campos_da_pagina_de_resultados`. Manual: M4, M7 |
| **RF-16** | Ordenar por preço ou por nota | `regras/busca.py` → `ORDENACOES`, `buscar`; `paginas/resultados.html` (select "Ordenar por") | Teste: `test_busca.py::test_rf16_*`, `test_ordenacao_padrao_e_relevancia`. Manual: M2 |
| **RNF-01** | Busca em até 2 s em 95% das requisições | `regras/busca.py` → `buscar` (consulta única, paginação); `schema.sql` (índices, inclusive o de expressão `norm(cidade), norm(bairro)`); `rotas.py` → `registrar_tempo` (cabeçalho `Server-Timing` e log quando passa de 2 s) | Teste: `test_desempenho.py::test_rnf01_busca_em_ate_2s_no_percentil_95` (3.000 acomodações, p95). Manual: aba Rede do navegador, cabeçalho `Server-Timing` |
| **RNF-05** | Endereço exato só após reserva CONFIRMADA; antes, só o bairro | `regras/detalhe.py` → `pode_ver_endereco_exato`, `montar_localizacao`; `regras/busca.py` → `buscar` (nunca seleciona rua, número nem CEP); `servicos_externos/mapas.py` (recebe só bairro e cidade) | Teste: `test_detalhe.py::test_rnf05_*`, `test_busca.py::test_rnf05_resultado_nunca_traz_endereco_exato`. Manual: M5 |
| **UC08** passo 1 (4.3.2-1) | Informar localização, datas e hóspedes e receber a lista | `paginas/index.html`, `static/js/inicio.js`, `rotas.py` → `buscar_acomodacoes` | Manual: M1. Teste: `test_busca.py` |
| **UC08** passo 2 (4.3.2-2) | Aplicar filtros e o sistema atualiza a lista | `static/js/resultados.js` → `carregar` (sem recarregar a página; URL atualizada) | Manual: M2 |
| **UC08** alternativo: dados inválidos | Mensagens simples por campo, demais campos mantidos | `regras/busca.py` → `ErroValidacao`; `static/js/comum.js` → `mostrarErrosCampos` | Teste: `test_busca.py::test_parametros_invalidos_retornam_400_com_mensagem` (21 casos). Manual: M8 |
| **UC08** alternativo: sem resultados | Mensagem com sugestão | `rotas.py` → `buscar_acomodacoes` (campo `mensagem`) | Teste: `test_bairro_de_outra_cidade_nao_aparece`, `test_rf14_filtros_combinados_sem_resultado_tem_mensagem`. Manual: M8 |
| **UC09** (4.3.2-3) | Abrir anúncio: detalhes, avaliações e calendário | `regras/detalhe.py` → `carregar_acomodacao`, `montar_detalhe`, `verificar_periodo`, `montar_calendario`; `rotas.py` → `detalhar_acomodacao`, `calendario`; `paginas/anuncio.html`, `static/js/anuncio.js` | Teste: `test_detalhe.py`, `test_calendario.py`. Manual: M4 |
| **UC09** + Serviço de mapas (B.2) | Localização aproximada | `servicos_externos/mapas.py` → `ServicoMapasSimulado`; `regras/detalhe.py` → `montar_localizacao`; `static/js/anuncio.js` → `desenharMapa` | Teste: `test_detalhe.py::test_mapa_*`. Manual: M6 |
| **UC20** (estende UC09) | Consultar avaliações | `rotas.py` → `listar_avaliacoes`; `regras/avaliacoes.py` | Teste: `test_avaliacoes.py` |
| **3.1** página de resultados | Foto, título, bairro e cidade, precoNoite, nota média; filtros de preço, quartos e camas | `static/js/resultados.js` → `cartao`; `paginas/resultados.html` | Teste: `test_resultado_tem_campos_da_pagina_de_resultados`. Manual: M1 |
| **3.1** página do anúncio | Fotos, descrição, capacidade, regras da casa, avaliações, calendário | `paginas/anuncio.html`, `static/js/anuncio.js` | Teste: `test_detalhe.py::test_detalhe_tem_fotos_descricao_capacidade_regras`. Manual: M4 |
| **3.1** padrões gerais | Botão de ajuda em todas as telas; erros em linguagem simples | `paginas/*.html` (`.botao-ajuda`), `paginas/ajuda.html`; mensagens em `regras/busca.py` e `regras/detalhe.py` | Teste: `test_sessao_e_paginas.py::test_paginas_html_respondem` |
| **3.3** Armazenamento de arquivos | Fotos dos anúncios | `servicos_externos/armazenamento.py` → `ArmazenamentoSimulado`; `rotas.py` → `baixar_arquivo`; fallback de imagem em `static/js/anuncio.js` e `resultados.js` | Teste: `test_detalhe.py::test_foto_*`, `test_armazenamento_fora_do_ar_503`. Manual: M6 |
| **3.4** | API REST com JSON | `rotas.py` (blueprint `api`) | Todos os testes usam a API |
| **RN-01** | Check-out posterior ao check-in, mínimo de 1 noite | `regras/busca.py` → `validar_datas` (também usada na página do anúncio) | Teste: `test_rn01_*`, `test_periodo_invalido_retorna_erros_sem_quebrar_a_pagina` |
| **RN-02** | Hóspedes ≤ capacidadeMaxima | `regras/busca.py` → `buscar`; `regras/detalhe.py` → `verificar_periodo` | Teste: `test_rf13_capacidade_*`, `test_periodo_acima_da_capacidade_informa` |
| **RN-04** (efeito na disponibilidade) | PENDENTE vale por 30 min | `regras/disponibilidade.py` → `PRAZO_PENDENTE_MINUTOS`, `limite_pendente`, `sql_reserva_ocupa` | Teste: `test_rn04_*`, `test_pendente_vence_exatamente_aos_30_minutos`, `test_calendario.py::test_pendente_valida_ocupa_e_vencida_nao` |
| **RN-06** + 4.6.2-3 (efeito na exibição) | Avaliação publicada quando ambos avaliam ou o prazo de 14 dias termina | `regras/avaliacoes.py` → `SQL_AVALIACAO_PUBLICA_DO_HOSPEDE`, `data_limite_prazo` | Teste: `test_avaliacao_nao_publicada_*`, `test_avaliacao_publicada_*` |
| **RF-08** (efeito na exibição) | Anúncio precisa de 5 a 30 fotos | `regras/disponibilidade.py` → `sql_publicado` (`MINIMO_FOTOS`) | Teste: `test_rf08_*`, `test_anuncio_com_menos_de_5_fotos_oculto` |
| **RF-09** (efeito na exibição) | Anúncio desativado não aparece | `regras/disponibilidade.py` → `sql_publicado`; `regras/detalhe.py` → `carregar_acomodacao` | Teste: `test_rf09_*`, `test_anuncio_desativado_404_para_publico_e_visivel_para_dono` |
| **RF-10** (efeito na disponibilidade) | Datas bloqueadas pelo anfitrião | `schema.sql` (`bloqueio_data`); `regras/disponibilidade.py` → `sql_livre_no_periodo`, `noites_ocupadas` | Teste: `test_rf10_*`, `test_calendario.py::test_bloqueio_do_anfitriao_ocupa` |
| **RNF-06** (ocultação) | Anúncio com denúncia de risco em análise fica oculto | `regras/disponibilidade.py` → `sql_publicado` (`MOTIVO_RISCO_SEGURANCA`) | Teste: `test_rnf06_*`, `test_denuncia_*`, `test_anuncio_sob_denuncia_de_risco_oculto_para_publico` |
| **RNF-11** (parcial) | Só o dono vê o que é privado do anúncio | `regras/detalhe.py` → `carregar_acomodacao` (dono vê anúncio desativado ou oculto), `pode_ver_endereco_exato` | Teste: `test_anuncio_desativado_404_para_publico_e_visivel_para_dono` |
| **RNF-14** (parcial) | WCAG 2.1 AA | HTML semântico, `label` em todos os campos, `aria-live`/`role=alert`, link "pular para o conteúdo", foco visível, contraste ≥ 4,5:1, alvos de 44 px, calendário em `<table>` com rótulos por dia (`static/css/estilo.css`, `paginas/*.html`) | Manual: navegar só com teclado (Tab) e com leitor de tela. **Não houve auditoria formal** com ferramenta. |
| **RNF-15** | Cobertura de testes ≥ 70% | `tests/` | `python -m pytest --cov=.` (99% medidos) |
| **RNF-16** | Telas de 360 a 1920 px | `static/css/estilo.css` (grid fluido, media queries) | Manual: largura de 375 px verificada sem rolagem horizontal |
| **RNF-22** (leitura) | Histórico de status de reserva | Lido em `regras/disponibilidade.py` → `sql_reserva_ocupa` para saber a idade da PENDENTE; gravado só pelo seed | Teste: `test_pendente_vence_exatamente_aos_30_minutos` |
| **B.4** | Projeto de tabelas | `schema.sql` (nomes de colunas iguais ao B.4) | Abrir `instancia/plataforma.db` em qualquer cliente SQLite |

## Requisitos relevantes NÃO implementados

| ID | Motivo |
|---|---|
| RF-01 a RF-06, RNF-07, RNF-09, RNF-10 (cadastro, login, sessão, bloqueio de conta) | Fora do escopo: o enunciado permite usuário de teste. O login é simulado (`sessao.py`). As senhas do seed usam hash (werkzeug), mas não há tela de login. |
| RF-07 a RF-11 (gestão de acomodações) | Pertencem ao UC05/UC06/UC07. Aqui só são **lidos** os efeitos (ativo, fotos, bloqueios). |
| RF-17 a RF-22, RN-03, RN-05, RN-07 (cálculo), RN-08 (reserva) | A reserva fica fora desta tarefa (enunciado). A página do anúncio só informa se o período está livre. O total com taxa (RF-18) **não** é exibido para não duplicar regra do módulo de reservas. O cancelamento automático da RN-04 não é executado aqui: apenas a PENDENTE vencida deixa de ocupar datas. |
| RF-23 a RF-28 (pagamento) | Fora do escopo. As tabelas `pagamento` e `historico_status_pagamento` não foram criadas. |
| RF-29 a RF-33 (criar avaliações, atribuir superhost) | Fora do escopo. A tarefa só **exibe** avaliações (RF-15) e o selo já gravado em `usuario.superhost`. |
| RF-34 a RF-36 (denúncias e moderação) | Fora do escopo. Só o efeito do RNF-06 (ocultar) foi implementado. O bloqueio de usuário (RF-36) não tem coluna no B.4, então os anúncios de um anfitrião bloqueado **não** são ocultados. |
| RNF-02, RNF-04 (pagamento em 10 s; carga em 4G) | RNF-02 é de pagamento. RNF-04 não foi medido: as páginas são leves (sem frameworks, fotos com `loading=lazy`), mas não houve teste em rede 4G. |
| RNF-03 (10.000 usuários simultâneos), RNF-12 (99,5%), RNF-21 (backup) | Requisitos de infraestrutura e operação. SQLite e o servidor de desenvolvimento do Flask **não** atendem a esses níveis; em produção seriam necessários banco servidor, réplicas, monitoramento e backup diário. |
| 3.4 HTTPS/TLS 1.2, push no app móvel | O ambiente local usa HTTP. TLS seria configurado no proxy reverso em produção. |
| 3.2 Localização do dispositivo (sugerir destinos próximos) | Não pedido para esta tarefa e sem regra detalhada na ERS. |
| RNF-17, RNF-18 (LGPD: exportar e excluir dados, consentimento) | Fora do escopo. Foi aplicada só a minimização dos dados exibidos (primeiro nome, sem contatos). |
| RNF-20 (internacionalização) | Não implementado: textos fixos em português e valores em BRL formatados com `Intl` (o que facilitaria a troca futura). |
