// Funções compartilhadas pelas telas. JavaScript puro, sem frameworks.
"use strict";

/** Chama a API. Devolve { ok, status, dados }. Nunca lança por erro HTTP. */
async function api(url, opcoes = {}) {
  const config = { credentials: "same-origin", ...opcoes };
  if (opcoes.json !== undefined) {
    config.body = JSON.stringify(opcoes.json);
    config.headers = { "Content-Type": "application/json", ...(opcoes.headers || {}) };
    delete config.json;
  }
  let resposta;
  try {
    resposta = await fetch(url, config);
  } catch (e) {
    return { ok: false, status: 0, dados: { erro: "Sem conexão com o servidor. Tente novamente." } };
  }
  let dados = null;
  const texto = await resposta.text();
  try { dados = texto ? JSON.parse(texto) : null; } catch (e) { dados = { erro: "Resposta inesperada do servidor." }; }
  return { ok: resposta.ok, status: resposta.status, dados };
}

/** Escreve texto com segurança (sem innerHTML com dados do usuário). */
function el(tag, atributos = {}, ...filhos) {
  const no = document.createElement(tag);
  for (const [chave, valor] of Object.entries(atributos)) {
    if (valor === false || valor === null || valor === undefined) continue;
    if (chave === "class") no.className = valor;
    else if (chave.startsWith("on")) no.addEventListener(chave.slice(2), valor);
    else no.setAttribute(chave, valor === true ? "" : valor);
  }
  for (const f of filhos.flat()) {
    if (f === null || f === undefined || f === false) continue;
    no.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return no;
}

function mostrarMensagem(texto, tipo = "ok") {
  const area = document.getElementById("mensagens");
  area.replaceChildren(el("p", { class: `mensagem ${tipo}` }, texto));
  area.scrollIntoView({ block: "nearest" });
}

function limparMensagem() {
  document.getElementById("mensagens").replaceChildren();
}

function formatarMoeda(valor) {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatarData(iso) {
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

const NOMES_STATUS = { PENDENTE: "Pendente", CONFIRMADA: "Confirmada", CANCELADA: "Cancelada", CONCLUIDA: "Concluída" };

/** Seletor de "quem está logado" (login simulado). */
async function prepararSessao() {
  const seletor = document.getElementById("seletor-usuario");
  const [usuarios, sessao] = await Promise.all([api("/api/usuarios-teste"), api("/api/sessao")]);
  if (!usuarios.ok) return null;
  for (const u of usuarios.dados) {
    seletor.append(el("option", { value: u.id }, `${u.nome}${u.ehAnfitriao ? " (anfitrião)" : " (só hóspede)"}`));
  }
  if (sessao.ok) seletor.value = sessao.dados.id;
  seletor.addEventListener("change", async () => {
    const r = await api("/api/sessao", { method: "POST", json: { usuarioId: Number(seletor.value) } });
    if (r.ok) window.location.reload();
    else mostrarMensagem(r.dados.erro, "erro");
  });
  return sessao.ok ? sessao.dados : null;
}

function prepararAjuda() {
  const dialogo = document.getElementById("ajuda");
  document.getElementById("abrir-ajuda").addEventListener("click", () => dialogo.showModal());
}

const sessaoPronta = prepararSessao();
prepararAjuda();
