// Tela "Minhas acomodações" (RF-11) com desativar/reativar (RF-09, UC07).
"use strict";

const area = document.getElementById("lista-acomodacoes");

async function carregar() {
  const r = await api("/api/minhas-acomodacoes");
  area.setAttribute("aria-busy", "false");
  if (!r.ok) {
    area.replaceChildren(el("p", { class: "mensagem erro" }, r.dados.erro));
    return;
  }
  if (r.dados.length === 0) {
    area.replaceChildren(el("p", {}, "Você ainda não tem anúncios. ",
      el("a", { href: "/anfitriao/acomodacoes/nova" }, "Anuncie seu primeiro espaço.")));
    return;
  }
  area.replaceChildren(...r.dados.map(cartao));
}

function cartao(a) {
  const idTitulo = `acomodacao-${a.id}`;
  return el("article", { class: `acomodacao${a.ativo ? "" : " inativa"}`, "aria-labelledby": idTitulo },
    a.capa ? el("img", { src: a.capa, alt: `Foto de capa de ${a.titulo}` }) : el("div"),
    el("div", {},
      el("h2", { id: idTitulo }, a.titulo),
      el("p", {},
        el("span", { class: `selo ${a.ativo ? "ativo" : "inativo"}` }, a.ativo ? "Publicado" : "Desativado"),
        ` ${a.bairro}, ${a.cidade}/${a.estado} · ${formatarMoeda(a.precoNoite)} por noite · até ${a.capacidadeMaxima} hóspedes · ${a.totalFotos} fotos`),
      el("div", { class: "acoes" },
        el("a", { class: "botao", href: `/anfitriao/acomodacoes/${a.id}/editar` }, "Editar"),
        el("a", { class: "botao", href: `/anfitriao/acomodacoes/${a.id}/calendario` }, "Calendário"),
        a.ativo
          ? el("button", { type: "button", class: "botao perigo", onclick: () => desativar(a) }, "Desativar")
          : el("button", { type: "button", class: "botao", onclick: () => reativar(a) }, "Reativar")),
      tabelaReservas(a)));
}

function tabelaReservas(a) {
  if (a.reservas.length === 0) return el("p", { class: "explicacao" }, "Nenhuma reserva recebida.");
  return el("div", { class: "tabela-rolagem" },
    el("table", {},
      el("caption", {}, `Reservas recebidas (${a.reservas.length})`),
      el("thead", {}, el("tr", {},
        ["Hóspede", "Check-in", "Check-out", "Pessoas", "Valor total", "Status"].map(t => el("th", { scope: "col" }, t)))),
      el("tbody", {}, a.reservas.map(r => el("tr", {},
        el("td", {}, r.hospede),
        el("td", {}, formatarData(r.checkIn)),
        el("td", {}, formatarData(r.checkOut)),
        el("td", {}, r.numHospedes),
        el("td", {}, formatarMoeda(r.valorTotal)),
        el("td", { class: `status-${r.status}` }, NOMES_STATUS[r.status] || r.status))))));
}

async function desativar(a, confirmar = false) {
  if (!confirmar && !window.confirm(`Desativar "${a.titulo}"? Ele deixará de aparecer nas buscas.`)) return;
  const r = await api(`/api/acomodacoes/${a.id}/desativar`, { method: "POST", json: { confirmar } });
  if (r.status === 409 && r.dados.codigo === "CONFIRMACAO_NECESSARIA") {
    // Há reservas futuras: o anfitrião precisa saber que elas continuam valendo.
    const lista = r.dados.detalhes.map(x =>
      `• ${x.hospede}: ${formatarData(x.checkIn)} a ${formatarData(x.checkOut)} (${NOMES_STATUS[x.status]})`).join("\n");
    if (window.confirm(`${r.dados.erro}\n\n${lista}`)) return desativar(a, true);
    return;
  }
  mostrarMensagem(r.ok ? r.dados.mensagem : r.dados.erro, r.ok ? "ok" : "erro");
  carregar();
}

async function reativar(a) {
  const r = await api(`/api/acomodacoes/${a.id}/reativar`, { method: "POST", json: {} });
  mostrarMensagem(r.ok ? r.dados.mensagem : r.dados.erro, r.ok ? "ok" : "erro");
  carregar();
}

carregar();
