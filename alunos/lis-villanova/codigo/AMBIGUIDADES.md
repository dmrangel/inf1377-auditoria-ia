# Ambiguidades e decisões

Pontos em que a ERS v1.1 é ambígua, incompleta ou contraditória para este módulo. Para cada um: o trecho, a interpretação adotada e a alternativa descartada. Os códigos **A-xx** aparecem nos comentários do código.

Os pontos mais importantes para a auditoria, porque afetam segurança ou contradizem outra parte da ERS, são **A-11**, **A-12**, **A-15** e **A-21**.

---

### A-01. Versão da ERS

- **Trecho:** o prompt e o PDF anexado são a ERS **v1.1**; o repositório tem `requisitos/ERS_v1.2_Plataforma_de_Hospedagem.pdf`.
- **Adotado:** a v1.1 anexada é a referência. Não comparei com a v1.2.
- **Descartado:** usar a v1.2 do repositório, que o prompt não cita.

### A-02. UC02 e UC03 não têm descrição

- **Trecho:** o prompt pede UC02 (Efetuar login) e UC03 (Alterar dados cadastrais). O diagrama de casos de uso (B.2) mostra os dois, mas o B.3 só descreve UC01, UC05, UC10, UC16, UC12 e UC18.
- **Adotado:** os fluxos foram derivados de RF-03, RF-05, RNF-09, RNF-10 e da Seção 4.1.2. Pré-condições, fluxos alternativos e pós-condições são decisões minhas, registradas aqui.
- **Descartado:** escrever descrições completas de UC02 e UC03 e tratá-las como se fossem da ERS.

### A-03. Política de senha

- **Trecho:** RF-01 ("cadastro... com senha") e RNF-07 tratam só de armazenamento. Não há regra de tamanho nem de composição.
- **Adotado:** de 8 a 128 caracteres, com pelo menos uma letra e um número. A senha não é alterada (sem remover espaços). O limite de 128 evita entradas enormes.
- **Descartado:** aceitar qualquer senha não vazia, que é fraca demais; e exigir maiúscula, minúscula e símbolo, que é mais rígido do que a ERS sugere e pior para o usuário.

### A-04. Formato do telefone

- **Trecho:** RF-01 pede telefone, sem formato. A ERS não diz se é obrigatório nem se precisa de confirmação.
- **Adotado:** obrigatório, brasileiro com DDD, com 10 dígitos (fixo) ou 11 (celular). Pontuação é aceita e removida, e o banco guarda só os dígitos. Não há confirmação por SMS.
- **Descartado:** formato internacional (E.164). O RNF-20 trata de idiomas e moedas "em versões futuras", e aceitar qualquer formato agora impediria validar.

### A-05. Normalização de nome e e-mail

- **Trecho:** RF-02 diz "dois usuários com o mesmo e-mail", sem dizer se `Ana@x.com` e `ana@x.com` são o mesmo.
- **Adotado:** o e-mail é gravado em minúsculas e sem espaços nas pontas, e a coluna tem `UNIQUE COLLATE NOCASE` no banco. O nome tem espaços repetidos reduzidos e de 2 a 100 caracteres.
- **Descartado:** comparar o e-mail exatamente como digitado. Isso permitiria duas contas com o "mesmo" e-mail e confundiria o login e a recuperação de senha.

### A-06. Conta usável antes de confirmar o e-mail

- **Trecho:** a Seção 4.1.2 e a pós-condição do UC01 dizem que o sistema "envia um e-mail de confirmação", mas não dizem o que a confirmação libera nem quanto tempo o link vale. O B.4 não tem coluna para isso.
- **Adotado:** a conta funciona logo após o cadastro, e a confirmação só marca `emailConfirmado = 1`. O link vale **7 dias** e uma única vez. O usuário pode pedir um novo link em Configurações, e o anterior deixa de valer.
- **Descartado:** bloquear o login até a confirmação. Seria mais seguro, mas a ERS não pede e isso mudaria o fluxo do UC01, que termina com a conta criada.

### A-07. Papel escolhido no cadastro

- **Trecho:** a Seção 4.1.1 diz que a pessoa acessa "como hóspede, anfitrião ou ambos"; o RF-06 diz que "um hóspede ative o papel de anfitrião na mesma conta".
- **Adotado:** toda conta nasce como hóspede, e o papel de anfitrião é ativado depois, em Configurações (RF-06). O "ambos" da 4.1.1 é alcançado por esse caminho.
- **Descartado:** perguntar o papel no formulário de cadastro. Seria um segundo caminho para a mesma coisa, e o RF-01 lista só nome, e-mail, senha e telefone.

### A-08. Pré-requisitos e reversão do papel de anfitrião

- **Trecho:** o RF-06 não diz se é preciso algo para virar anfitrião (e-mail confirmado, documento, telefone verificado) nem se o papel pode ser desativado.
- **Adotado:** não há pré-requisito, e a ativação não pode ser desfeita nesta versão; a tela avisa isso antes de confirmar. É gravada a data de ativação (`dataAtivacaoAnfitriao`). Ativar duas vezes responde 409. Os atributos `superhost` e `taxaResposta` do diagrama de classes ficam para o módulo de acomodações e avaliações.
- **Descartado:** exigir e-mail confirmado. Seria razoável, mas não está na ERS. Permitir desativar exigiria definir o que acontece com anúncios e reservas existentes, o que está fora deste módulo.

### A-09. Quais dados do perfil são editáveis

- **Trecho:** RF-05 diz "editar seus dados de perfil", sem listar quais.
- **Adotado:** nome e telefone, mais a senha (com a senha atual). O **e-mail não é editável**: ele é o login e a chave única (RF-02), e trocá-lo exigiria reconfirmar o endereço novo. O servidor ignora qualquer outro campo enviado (`email`, `id`, `ehAnfitriao`).
- **Descartado:** permitir trocar o e-mail sem reconfirmação, porque quem roubasse a sessão poderia trocar o e-mail e tomar a conta pela recuperação de senha.

### A-10. Efeitos da troca de senha

- **Trecho:** a ERS não trata da troca de senha pelo próprio usuário.
- **Adotado:** exige a senha atual e aplica a política do A-03. A sessão atual continua, mas as sessões em outros aparelhos são encerradas, por meio da coluna `versaoSessao`. Links de recuperação pendentes deixam de valer, e um e-mail avisa da troca.
- **Descartado:** trocar sem pedir a senha atual, porque quem pegasse um computador já logado poderia tomar a conta.

### A-11. Detalhes do bloqueio por tentativas (RNF-10)

- **Trecho:** "A conta deve ser bloqueada por 15 minutos após 5 tentativas de login sem sucesso."
- **Problemas:** a ERS não diz se as tentativas são **seguidas** ou numa janela de tempo, se um login certo zera a contagem, o que acontece com tentativas feitas durante o bloqueio, se a mensagem revela o bloqueio, nem se o bloqueio é por conta ou por IP.
- **Adotado:**
  - São 5 falhas **seguidas**, e um login com sucesso zera o contador.
  - A 5ª falha bloqueia por 15 minutos a partir dela. Ao bloquear, o contador volta a zero, então depois do bloqueio há mais 5 tentativas.
  - Durante o bloqueio, **nem a senha correta entra**, a senha nem é conferida, e as tentativas não prolongam o bloqueio.
  - O bloqueio é **por conta**, como diz o texto.
  - A mensagem avisa que a conta está bloqueada e por quantos minutos, seguindo a Seção 3.1 ("mensagens de erro em linguagem simples"). Isso revela que a conta existe (ver A-12).
  - Redefinir a senha pelo link do e-mail desbloqueia a conta (A-14).
  - Errar a senha atual em Configurações ou na exclusão da conta **não** conta como tentativa de login.
- **Descartado:** janela deslizante (5 falhas em X minutos), porque a ERS não dá o X. Prolongar o bloqueio a cada tentativa, porque permitiria a qualquer pessoa manter a conta de outra bloqueada para sempre. Bloqueio por IP, porque não é o que o texto diz.
- **Risco registrado:** o bloqueio por conta permite que alguém bloqueie a conta de outra pessoa errando a senha de propósito. A ERS não trata isso; a recuperação de senha é a saída.

### A-12. Revelar ou não que um e-mail tem conta

- **Trecho:** o UC01 4a manda informar "E-mail já cadastrado" e oferecer a recuperação. Isso revela quem tem conta, o que conflita com a boa prática de não confirmar a existência de contas.
- **Adotado:**
  - **Cadastro:** segue o UC01 4a e revela que o e-mail existe, porque a ERS manda.
  - **Login:** a mesma mensagem ("E-mail ou senha incorretos.") para e-mail inexistente e senha errada. Para e-mail inexistente, o servidor calcula um hash fictício, para o tempo de resposta não denunciar a diferença.
  - **Recuperação de senha:** sempre a mesma resposta, e só a conta real recebe o e-mail.
  - **Bloqueio:** revela que a conta existe (A-11).
- **Descartado:** esconder a existência também no cadastro, que contraria o UC01 4a. O cadastro continua sendo um caminho para descobrir contas; vale a ERS reavaliar o 4a.

### A-13. O que conta como inatividade (RNF-09)

- **Trecho:** "A sessão deve expirar após 30 minutos de inatividade."
- **Adotado:** inatividade é o tempo desde a última requisição ao servidor com a sessão. A verificação é no servidor, em toda requisição (exceto arquivos estáticos). Passados 30 minutos, a sessão é apagada e a próxima ação leva à tela de entrada com o aviso. Não há opção "lembrar de mim".
- **Descartado:** só um temporizador em JavaScript, que o usuário pode desligar, e expiração fixa de 30 minutos após o login, que é outra regra.

### A-14. Recuperação de senha (RF-04)

- **Trecho:** "recuperação de senha por link enviado ao e-mail cadastrado", sem validade, número de usos nem efeitos.
- **Adotado:**
  - O link vale **1 hora** e **uma única vez**, e um pedido novo invalida o anterior.
  - O token é guardado no banco só como hash SHA-256.
  - Uma senha nova fraca não gasta o link.
  - Redefinir a senha desbloqueia a conta (quem tem acesso ao e-mail provou ser o dono), encerra as sessões abertas e manda um e-mail avisando.
- **Descartado:** link sem prazo, porque um e-mail antigo vazado daria acesso à conta. Manter o bloqueio após a redefinição, porque deixaria o dono legítimo sem acesso.

### A-15. Excluir dados (RNF-17) e guardar pagamentos por 5 anos (RNF-19)

- **Trecho:** o RNF-17 diz que o usuário pode "excluir seus dados pessoais"; o RNF-19 manda guardar os registros de pagamento por 5 anos. A ERS também não diz se a exclusão apaga a conta ou só alguns dados, nem o que acontece com reservas e anúncios.
- **Contradição:** no sistema completo, apagar o usuário apagaria ou deixaria órfãos os pagamentos ligados às reservas dele.
- **Adotado:** neste módulo só existem as tabelas `usuario` e `token_usuario`, então "excluir dados" apaga a conta, depois de confirmar a senha. O comentário em `usuarios.excluir_conta` registra que, integrado às reservas, seria preciso **anonimizar** (manter o registro sem nome, e-mail e telefone) em vez de apagar. A exportação traz dados pessoais, papéis e consentimento, mas **não** o hash da senha nem os contadores de segurança, que não servem ao titular e facilitariam ataques. A "consulta" do RNF-17 é a própria tela de Configurações.
- **Descartado:** só desativar a conta, que não atende a "excluir"; e apagar sem confirmar a senha, que permitiria a quem pegasse a sessão destruir a conta.

### A-16. O que registrar do consentimento (RNF-18)

- **Trecho:** "O cadastro deve registrar o consentimento do usuário com os termos de uso e a política de privacidade." A ERS não diz o que registrar, e os textos dos termos não existem.
- **Adotado:** o cadastro só é aceito com o booleano `true` (nem `"sim"` nem `1` valem). São gravadas a data e hora do aceite (`consentimentoTermosEm`) e a versão dos termos (`versaoTermos = "1.0"`), para saber com qual versão a pessoa concordou se os termos mudarem.
- **Descartado:** gravar só "aceitou = sim", que não prova quando nem com qual versão.

### A-17. Colunas que não estão no B.4

- **Trecho:** a tabela `usuario` do B.4 tem `id, nome, email, senhaHash, telefone, dataCadastro, ehAnfitriao`. Vários requisitos da própria ERS precisam guardar mais estado.
- **Adotado (colunas extras):**

  | Coluna ou tabela | Por quê |
  |---|---|
  | `consentimentoTermosEm`, `versaoTermos` | RNF-18 (A-16) |
  | `emailConfirmado` | Confirmação do UC01 (A-06) |
  | `tentativasFalhas`, `bloqueadoAte` | RNF-10 (A-11) |
  | `versaoSessao` | Encerrar sessões ao trocar a senha (A-10, A-14) |
  | `dataAtivacaoAnfitriao` | Registrar quando o RF-06 foi usado |
  | tabela `token_usuario` | Links de confirmação e recuperação (A-06, A-14) |

- **Divergência registrada:** o diagrama de classes chama o atributo de `Usuario.senha`, o B.4 de `senhaHash`. Usei `senhaHash`.
- **Descartado:** guardar esse estado fora do banco (por exemplo, em memória), porque se perderia ao reiniciar.

### A-18. Algoritmo de hash (RNF-07)

- **Trecho:** "hash e salt (por exemplo, bcrypt)".
- **Adotado:** a função `generate_password_hash` do Werkzeug, que já vem com o Flask. Ela usa **scrypt** com salt aleatório por senha, gravado junto do hash. O RNF-07 dá o bcrypt como exemplo, não como obrigação.
- **Descartado:** instalar o pacote `bcrypt` só para isso.

### A-19. Serviço de e-mail fora do ar

- **Trecho:** a ERS não diz o que fazer se o e-mail de confirmação não puder ser enviado.
- **Adotado:** a conta é criada mesmo assim, a tela avisa, e o usuário pode pedir o reenvio em Configurações. Na recuperação de senha a resposta continua a mesma (A-12). No reenvio de confirmação, a falha é informada (503).
- **Descartado:** desfazer o cadastro quando o e-mail falha, porque a pessoa perderia o que preencheu por um problema que não é dela.

### A-20. Login automático após o cadastro

- **Trecho:** o UC01 termina com "usuário cadastrado e e-mail de confirmação enviado", sem dizer se a pessoa já fica logada.
- **Adotado:** não há login automático. A tela leva para **Entrar** com o e-mail já preenchido.
- **Descartado:** login automático. É mais cômodo, mas a ERS separa o cadastro (passo 2) do login (passo 3) na Seção 4.1.2.

### A-21. Proteções web que a ERS não cita

- **Trecho:** a Seção 3.4 pede HTTPS e uma API REST com JSON, e a 5.3 lista senhas, cartões, sessão, bloqueio e posse de acomodações. Não há nada sobre CSRF, cookies ou cabeçalhos.
- **Adotado:**
  - As rotas que alteram dados só aceitam `application/json`; um formulário de outro site não consegue enviar esse tipo sem permissão de CORS.
  - O cookie de sessão é `HttpOnly` e `SameSite=Lax`, e é assinado com uma chave aleatória quando não há `SECRET_KEY`.
  - As respostas levam os cabeçalhos `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` e `Referrer-Policy: no-referrer` (para os tokens na URL não vazarem).
  - O HTTPS fica para a implantação: `SESSION_COOKIE_SECURE=1` liga o cookie seguro.
- **Descartado:** CSRF com token em cada formulário. Também funcionaria, mas é mais código para o mesmo efeito numa API só de JSON.
- **Não tratado:** não há limite de requisições por IP no cadastro e na recuperação de senha. A ERS não pede, mas sem isso alguém pode lotar a caixa de e-mail de outra pessoa pedindo links de recuperação.

### A-22. Usuário bloqueado por denúncia (RF-36) e administrador

- **Trecho:** o RF-36 diz que o sistema deve "bloquear o usuário quando o parecer for procedente", e a Seção 2.3 cita o Administrador. O B.4 não tem coluna para usuário bloqueado nem para o papel de administrador.
- **Adotado:** fora do escopo. O bloqueio deste módulo é só o temporário do RNF-10. Quando o módulo de denúncias existir, o login (`usuarios.autenticar`) precisará recusar usuários bloqueados por parecer, e o B.4 precisará da coluna.
- **Descartado:** criar agora uma coluna de bloqueio permanente sem a regra que a usa.

### A-23. Campo "repita a senha"

- **Trecho:** o RF-01 lista só nome, e-mail, senha e telefone.
- **Adotado:** as telas pedem a senha duas vezes, e a conferência é feita **só no navegador**, porque é uma conveniência para evitar erro de digitação. Todas as regras de senha (A-03) são verificadas no servidor.
- **Descartado:** mandar a confirmação para o servidor, que receberia um dado que o RF-01 não prevê.

### A-24. Escopo de "Configurações de Usuário"

- **Trecho:** o prompt chama a funcionalidade de "Configurações de Usuário" e cita a Seção 4.1, a 5.3, UC01 a UC03 e RF-06. O RNF-17 (LGPD: consultar, exportar e excluir) e o RNF-18 (consentimento) estão na Seção 6, que o prompt não cita.
- **Adotado:** o RNF-18 foi implementado porque o UC01 o lista entre os requisitos relacionados. O RNF-17 foi implementado porque consultar, exportar e excluir os próprios dados é uma configuração de usuário e não depende de outros módulos.
- **Descartado:** deixar o RNF-17 para depois, porque um módulo de conta sem exclusão de dados ficaria fora da LGPD.
