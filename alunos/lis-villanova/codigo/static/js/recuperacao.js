// recuperacao.js - RF-04: pedir o link e criar a nova senha.
"use strict";

const formRecuperar = document.getElementById("form-recuperar");
if (formRecuperar) {
  formRecuperar.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparErros(formRecuperar);
    const r = await chamarApi("POST", "/api/recuperar-senha", lerFormulario(formRecuperar));
    if (r.ok) mostrarMensagem(r.dados.mensagem, "sucesso");
    else mostrarErroDaApi(formRecuperar, r);
  });
}

const formRedefinir = document.getElementById("form-redefinir");
if (formRedefinir) {
  formRedefinir.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparErros(formRedefinir);
    mostrarMensagem("");
    if (!senhasConferem(formRedefinir, "novaSenha")) return;
    const d = lerFormulario(formRedefinir);
    const r = await chamarApi("POST", "/api/redefinir-senha", { token: d.token, novaSenha: d.novaSenha });
    if (r.ok) {
      formRedefinir.hidden = true;
      mostrarMensagem(r.dados.mensagem, "sucesso");
      const link = document.createElement("a");
      link.href = "/login";
      link.textContent = " Ir para Entrar";
      document.getElementById("mensagem").appendChild(link);
    } else {
      mostrarErroDaApi(formRedefinir, r);
    }
  });
}
