// configuracoes.js - UC03 (dados e senha), RF-06 (anfitrião) e RNF-17 (exclusão).
"use strict";

// UC03 / RF-05: nome e telefone.
document.getElementById("form-perfil").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  limparErros(form);
  const d = lerFormulario(form);
  const r = await chamarApi("PUT", "/api/perfil", { nome: d.nome, telefone: d.telefone });
  if (r.ok) {
    form.elements["nome"].value = r.dados.usuario.nome;
    form.elements["telefone"].value = r.dados.usuario.telefone;
    mostrarMensagem(r.dados.mensagem, "sucesso");
  } else {
    mostrarErroDaApi(form, r);
  }
});

// UC03: troca de senha.
document.getElementById("form-senha").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  limparErros(form);
  if (!senhasConferem(form, "novaSenha")) return;
  const d = lerFormulario(form);
  const r = await chamarApi("PUT", "/api/perfil/senha", { senhaAtual: d.senhaAtual, novaSenha: d.novaSenha });
  if (r.ok) {
    form.reset();
    mostrarMensagem(r.dados.mensagem, "sucesso");
  } else {
    mostrarErroDaApi(form, r);
  }
});

// Reenvio do e-mail de confirmação.
const reenviar = document.getElementById("botao-reenviar");
if (reenviar) {
  reenviar.addEventListener("click", async () => {
    const r = await chamarApi("POST", "/api/perfil/reenviar-confirmacao");
    mostrarMensagem(r.ok ? r.dados.mensagem : r.dados.erro, r.ok ? "sucesso" : "erro");
  });
}

// RF-06: tornar-se anfitrião.
const anfitriao = document.getElementById("botao-anfitriao");
if (anfitriao) {
  anfitriao.addEventListener("click", async () => {
    if (!window.confirm("Ativar o papel de anfitrião na sua conta? Nesta versão não é possível desfazer.")) return;
    const r = await chamarApi("POST", "/api/perfil/tornar-anfitriao");
    if (r.ok) {
      window.location.reload();
    } else {
      mostrarMensagem(r.dados.erro, "erro");
    }
  });
}

// RNF-17: exclusão da conta.
document.getElementById("form-excluir").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  limparErros(form);
  if (!window.confirm("Excluir sua conta definitivamente? Esta ação não pode ser desfeita.")) return;
  const r = await chamarApi("DELETE", "/api/conta", { senha: form.elements["senha"].value });
  if (r.ok) {
    window.alert(r.dados.mensagem);
    window.location.href = "/";
  } else {
    mostrarErroDaApi(form, r);
  }
});
