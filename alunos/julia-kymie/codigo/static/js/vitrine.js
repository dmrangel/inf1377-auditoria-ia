// Vitrine pública mínima: anúncios ativos, só bairro e cidade (RNF-05).
"use strict";

(async () => {
  const lista = document.getElementById("vitrine");
  const r = await api("/api/anuncios");
  lista.setAttribute("aria-busy", "false");
  if (!r.ok) { lista.replaceChildren(el("li", { class: "mensagem erro" }, r.dados.erro)); return; }
  if (!r.dados.length) { lista.replaceChildren(el("li", {}, "Nenhum anúncio publicado.")); return; }
  lista.replaceChildren(...r.dados.map(a => el("li", { class: "cartao" },
    a.capa ? el("img", { src: a.capa, alt: `Foto de ${a.titulo}` }) : null,
    el("h2", {}, a.titulo),
    el("p", {}, `${a.bairro}, ${a.cidade}/${a.estado}`),
    el("p", {}, `${formatarMoeda(a.precoNoite)} por noite · até ${a.capacidadeMaxima} hóspedes`))));
})();
