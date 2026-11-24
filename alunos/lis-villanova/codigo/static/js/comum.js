// comum.js - Funções usadas por todas as telas.
// O JavaScript só melhora a experiência: toda regra é verificada de novo no servidor.

"use strict";

/**
 * Chama a API e devolve {ok, status, dados}. Envia sempre JSON nas alterações
 * (o servidor recusa outro formato, como proteção contra CSRF).
 */
async function chamarApi(metodo, url, corpo) {
  const opcoes = { method: metodo, headers: { Accept: "application/json" }, credentials: "same-origin" };
  if (metodo !== "GET") {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo || {});
  }
  let resposta;
  try {
    resposta = await fetch(url, opcoes);
  } catch (e) {
    return { ok: false, status: 0, dados: { erro: "Sem conexão com o servidor. Tente de novo." } };
  }
  let dados = {};
  try { dados = await resposta.json(); } catch (e) { /* resposta sem JSON */ }
  // Sessão vencida (RNF-09) ou encerrada: leva para a tela de entrada com o aviso.
  if (resposta.status === 401 && (dados.codigo === "SESSAO_EXPIRADA" || dados.codigo === "SESSAO_INVALIDADA")) {
    window.location.href = "/login?motivo=" + dados.codigo.toLowerCase();
  }
  return { ok: resposta.ok, status: resposta.status, dados: dados };
}

/** Lê os campos de um formulário como objeto; caixas de seleção viram true/false. */
function lerFormulario(form) {
  const dados = {};
  for (const el of form.elements) {
    if (!el.name) continue;
    dados[el.name] = el.type === "checkbox" ? el.checked : el.value;
  }
  return dados;
}

/** Mostra uma mensagem geral (sucesso, erro ou alerta) na área #mensagem. */
function mostrarMensagem(texto, tipo) {
  const area = document.getElementById("mensagem");
  if (!area) return;
  area.textContent = texto;
  area.className = "aviso aviso-" + (tipo || "sucesso");
  area.hidden = !texto;
  if (texto) area.scrollIntoView({ block: "nearest" });
}

/** Limpa os erros de campo de um formulário. */
function limparErros(form) {
  form.querySelectorAll(".erro").forEach((p) => { p.textContent = ""; });
  form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
}

/**
 * Destaca os campos com erro (UC01 4b) sem apagar o que foi digitado nos outros.
 * `campos` é o objeto {campo: mensagem} devolvido pelo servidor.
 */
function mostrarErrosCampos(form, campos) {
  let primeiro = null;
  for (const [nome, mensagem] of Object.entries(campos || {})) {
    const p = form.querySelector("#erro-" + nome);
    const el = form.elements[nome];
    if (p) p.textContent = mensagem;
    if (el && el.setAttribute) {
      el.setAttribute("aria-invalid", "true");
      if (!primeiro) primeiro = el;
    }
  }
  if (primeiro) primeiro.focus();
}

/** Trata a resposta de erro padrão do servidor: mensagem geral + campos. */
function mostrarErroDaApi(form, resposta) {
  mostrarMensagem(resposta.dados.erro || "Algo deu errado. Tente de novo.", "erro");
  if (form) mostrarErrosCampos(form, resposta.dados.campos);
}

/** Confere no navegador se as duas senhas digitadas são iguais (só conveniência, A-23). */
function senhasConferem(form, campoSenha) {
  const conf = form.elements["confirmacaoSenha"];
  if (conf && conf.value !== form.elements[campoSenha].value) {
    mostrarErrosCampos(form, { confirmacaoSenha: "As senhas digitadas não são iguais." });
    return false;
  }
  return true;
}

/** Mostra datas ISO no formato brasileiro. */
function formatarDatas() {
  document.querySelectorAll("time.data").forEach((el) => {
    const d = new Date(el.getAttribute("datetime"));
    if (!isNaN(d)) el.textContent = d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  formatarDatas();

  // Seção 3.1: botão de ajuda em todas as telas.
  const dialogo = document.getElementById("dialogo-ajuda");
  document.getElementById("botao-ajuda").addEventListener("click", () => dialogo.showModal());

  const sair = document.getElementById("botao-sair");
  if (sair) {
    sair.addEventListener("click", async () => {
      await chamarApi("POST", "/api/logout");
      window.location.href = "/";
    });
  }
});
