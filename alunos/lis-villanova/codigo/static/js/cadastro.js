// cadastro.js - UC01 Cadastrar usuário.
"use strict";

document.getElementById("form-cadastro").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  limparErros(form);
  mostrarMensagem("");
  if (!senhasConferem(form, "senha")) return;

  const d = lerFormulario(form);
  const botao = form.querySelector("button[type=submit]");
  botao.disabled = true;
  const r = await chamarApi("POST", "/api/cadastro", {
    nome: d.nome, email: d.email, telefone: d.telefone, senha: d.senha, aceitouTermos: d.aceitouTermos,
  });
  botao.disabled = false;

  if (r.ok) {
    form.reset();
    mostrarMensagem(r.dados.mensagem, r.dados.emailEnviado ? "sucesso" : "alerta");
    const link = document.createElement("a");
    link.href = "/login?email=" + encodeURIComponent(r.dados.email);
    link.textContent = " Ir para Entrar";
    document.getElementById("mensagem").appendChild(link);
    return;
  }
  mostrarErroDaApi(form, r);
  // UC01 4a: e-mail já cadastrado -> oferecer a recuperação de senha.
  if (r.dados.codigo === "EMAIL_JA_CADASTRADO") {
    const link = document.createElement("a");
    link.href = "/recuperar-senha?email=" + encodeURIComponent(d.email);
    link.textContent = " Recuperar senha";
    document.getElementById("mensagem").appendChild(link);
  }
});
