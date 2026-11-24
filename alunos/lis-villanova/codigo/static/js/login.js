// login.js - UC02 Efetuar login.
"use strict";

document.getElementById("form-login").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  limparErros(form);
  mostrarMensagem("");

  const botao = form.querySelector("button[type=submit]");
  botao.disabled = true;
  const r = await chamarApi("POST", "/api/login", lerFormulario(form));
  botao.disabled = false;

  if (r.ok) {
    window.location.href = "/configuracoes";
    return;
  }
  form.elements["senha"].value = "";
  mostrarErroDaApi(form, r);
});
