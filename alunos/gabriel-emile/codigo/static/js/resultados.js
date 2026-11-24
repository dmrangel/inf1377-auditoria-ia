/* Página de resultados (UC08, passos 1 e 2; RF-13 a RF-16). */
"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const { el, api, formatarMoeda, formatarNota } = Comum;
  const formBusca = document.getElementById("form-busca");
  const formFiltros = document.getElementById("form-filtros");
  const resumo = document.getElementById("resumo");
  const lista = document.getElementById("lista");
  const mensagem = document.getElementById("mensagem");
  const paginacao = document.getElementById("paginacao");
  const ordenar = document.getElementById("ordenar");

  for (const nome of ["quartos", "banheiros", "camas"]) {
    const s = document.getElementById(nome);
    s.append(el("option", { value: "", text: "Qualquer" }));
    for (let i = 1; i <= 5; i++) s.append(el("option", { value: String(i), text: `${i} ou mais` }));
  }

  const inicial = new URLSearchParams(location.search);
  FormBusca.preencher(formBusca, inicial);
  FormBusca.preencher(formFiltros, inicial);
  FormBusca.ajustarDatas(formBusca);

  let pagina = Number(inicial.get("pagina") || 1);

  function parametrosAtuais() {
    const p = FormBusca.paraParametros(formBusca, formFiltros);
    if (pagina > 1) p.set("pagina", String(pagina));
    return p;
  }

  function cartao(item, params) {
    // Leva o período e os hóspedes para a página do anúncio (UC09).
    const q = new URLSearchParams();
    for (const k of ["checkin", "checkout", "hospedes"]) if (params.get(k)) q.set(k, params.get(k));
    const notaTxt = item.notaMedia === null
      ? el("p", { class: "nota" }, "Novo (sem avaliações)")
      : el("p", { class: "nota" },
          el("span", { "aria-hidden": "true" }, "★ "),
          `Nota ${formatarNota(item.notaMedia)} de 5 (${item.totalAvaliacoes} avaliação${item.totalAvaliacoes === 1 ? "" : "ões"})`);
    const img = item.foto.url
      ? el("img", { class: "foto", src: item.foto.url, alt: item.foto.legenda, loading: "lazy", width: "640", height: "420" })
      : el("div", { class: "foto", role: "img", "aria-label": "Sem foto" });
    img.addEventListener("error", () => img.replaceWith(el("div", { class: "foto", role: "img", "aria-label": "Foto indisponível" })));
    return el("li", { class: "cartao" },
      el("a", { href: `/acomodacao/${item.id}?${q.toString()}` },
        img,
        el("div", { class: "corpo" },
          el("h3", { text: item.titulo }),
          // RNF-05: só bairro e cidade, nunca a rua.
          el("p", { class: "local", text: `${item.bairro}, ${item.cidade} - ${item.estado}` }),
          el("p", { class: "local", text: `Até ${item.capacidadeMaxima} hóspede(s) · ${item.quartos} quarto(s) · ${item.banheiros} banheiro(s) · ${item.camas} cama(s)` }),
          el("p", { class: "preco" }, `${formatarMoeda(item.precoNoite)} `, el("span", { class: "local" }, "por noite")),
          notaTxt,
          item.superhost ? el("p", { style: "margin:0" }, el("span", { class: "selo", text: "Superhost" })) : null,
        )));
  }

  function montarPaginacao(r) {
    paginacao.replaceChildren();
    if (r.totalPaginas <= 1) return;
    const ir = (n) => { pagina = n; carregar(true); };
    paginacao.append(
      el("button", { class: "botao secundario", type: "button", disabled: r.pagina <= 1, onclick: () => ir(r.pagina - 1) }, "Anterior"),
      el("span", { text: `Página ${r.pagina} de ${r.totalPaginas}` }),
      el("button", { class: "botao secundario", type: "button", disabled: r.pagina >= r.totalPaginas, onclick: () => ir(r.pagina + 1) }, "Próxima"),
    );
  }

  async function carregar(focarResultados = false) {
    const params = parametrosAtuais();
    history.replaceState(null, "", "/busca?" + params.toString());
    resumo.textContent = "Carregando…";
    mensagem.replaceChildren();
    Comum.mostrarErrosCampos(formBusca, {});
    Comum.mostrarErrosCampos(formFiltros, {});
    try {
      const r = await api("/api/acomodacoes/busca?" + params.toString());
      lista.replaceChildren(...r.itens.map((i) => cartao(i, params)));
      resumo.classList.remove("carregando");
      resumo.textContent = r.total === 0
        ? "Nenhuma acomodação encontrada."
        : `${r.total} acomodação${r.total === 1 ? "" : "ões"} disponível${r.total === 1 ? "" : "is"} para ${r.noites} noite${r.noites === 1 ? "" : "s"}.`;
      if (r.mensagem) mensagem.replaceChildren(el("p", { class: "aviso", text: r.mensagem }));
      montarPaginacao(r);
      if (focarResultados) document.getElementById("resultados").focus();
    } catch (e) {
      lista.replaceChildren();
      paginacao.replaceChildren();
      resumo.textContent = "";
      mensagem.replaceChildren(el("p", { class: "aviso erro", text: e.erro }));
      const campos = e.campos || {};
      const doFiltro = Object.fromEntries(Object.entries(campos).filter(([k]) => FormBusca.CAMPOS_FILTRO.includes(k)));
      const daBusca = Object.fromEntries(Object.entries(campos).filter(([k]) => !FormBusca.CAMPOS_FILTRO.includes(k)));
      Comum.mostrarErrosCampos(formFiltros, doFiltro);
      Comum.mostrarErrosCampos(formBusca, daBusca);
    }
  }

  formBusca.addEventListener("submit", (ev) => { ev.preventDefault(); pagina = 1; carregar(); });
  formFiltros.addEventListener("submit", (ev) => { ev.preventDefault(); pagina = 1; carregar(true); });
  ordenar.addEventListener("change", () => { pagina = 1; carregar(); });
  document.getElementById("limpar-filtros").addEventListener("click", () => {
    for (const nome of ["preco_min", "preco_max", "quartos", "banheiros", "camas"]) formFiltros.elements[nome].value = "";
    pagina = 1;
    carregar();
  });

  carregar();
});
