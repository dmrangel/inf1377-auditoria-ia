/* Funções compartilhadas pelas páginas (JavaScript puro, sem frameworks). */
"use strict";

const Comum = (() => {
  const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  const nota = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 2 });

  /** Cria um elemento com atributos e filhos. Texto entra sempre como
   *  textContent (nunca innerHTML), evitando injeção de HTML vinda dos dados. */
  function el(tag, attrs = {}, ...filhos) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") e.className = v;
      else if (k === "text") e.textContent = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? "" : v);
    }
    for (const f of filhos.flat()) {
      if (f === null || f === undefined || f === false) continue;
      e.append(f instanceof Node ? f : document.createTextNode(String(f)));
    }
    return e;
  }

  async function api(caminho, opcoes = {}) {
    let resp;
    try {
      resp = await fetch(caminho, {
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        ...opcoes,
      });
    } catch (e) {
      throw { status: 0, erro: "Não foi possível falar com o servidor. Verifique sua conexão e tente de novo." };
    }
    let corpo = null;
    try { corpo = await resp.json(); } catch (e) { /* sem corpo JSON */ }
    if (!resp.ok) {
      throw { status: resp.status, erro: (corpo && corpo.erro) || "Algo deu errado. Tente de novo.", campos: corpo && corpo.campos };
    }
    return corpo;
  }

  function formatarMoeda(v) { return moeda.format(v); }
  function formatarNota(v) { return v === null || v === undefined ? null : nota.format(v); }
  function formatarData(iso) {
    const [a, m, d] = iso.split("-");
    return `${d}/${m}/${a}`;
  }
  function isoHojeMais(dias) {
    const d = new Date();
    d.setDate(d.getDate() + dias);
    const off = d.getTimezoneOffset();
    return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
  }

  /** Mostra erros de validação do servidor ao lado de cada campo (UC08: erros
   *  em linguagem simples, campo destacado e demais valores mantidos). */
  function mostrarErrosCampos(form, campos = {}) {
    form.querySelectorAll(".erro-campo").forEach((n) => n.remove());
    form.querySelectorAll("[aria-invalid]").forEach((n) => n.removeAttribute("aria-invalid"));
    let primeiro = null;
    for (const [nome, msg] of Object.entries(campos)) {
      const input = form.elements[nome];
      if (!input || !input.closest(".campo")) continue;
      const id = `erro-${nome}`;
      input.setAttribute("aria-invalid", "true");
      input.setAttribute("aria-describedby", id);
      input.closest(".campo").append(el("p", { class: "erro-campo", id, text: msg }));
      primeiro = primeiro || input;
    }
    if (primeiro) primeiro.focus();
  }

  /** Cabeçalho comum: logo, usuário de teste (login simulado) e ajuda. */
  async function montarCabecalho() {
    const alvo = document.getElementById("usuario-teste");
    if (!alvo) return;
    try {
      const [sessao, usuarios] = await Promise.all([api("/api/sessao"), api("/api/usuarios-teste")]);
      const select = el("select", { id: "seletor-usuario", "aria-describedby": "dica-usuario" },
        el("option", { value: "", text: "Visitante (sem login)" }),
        usuarios.map((u) => el("option", { value: String(u.id), text: u.nome + (u.ehAnfitriao ? " (anfitrião)" : " (hóspede)") })));
      select.value = sessao.usuario ? String(sessao.usuario.id) : "";
      select.addEventListener("change", async () => {
        const id = select.value ? Number(select.value) : null;
        await api("/api/sessao", { method: "POST", body: JSON.stringify({ usuario_id: id }) });
        location.reload();
      });
      alvo.replaceChildren(
        el("label", { for: "seletor-usuario", text: "Usuário de teste:" }),
        select,
        el("span", { id: "dica-usuario", class: "sr-only", text: "Simula o login. Trocar o usuário recarrega a página." }),
      );
    } catch (e) {
      alvo.textContent = "";
    }
  }

  document.addEventListener("DOMContentLoaded", montarCabecalho);

  return { el, api, formatarMoeda, formatarNota, formatarData, isoHojeMais, mostrarErrosCampos };
})();
