/* Página do anúncio (UC09 e UC20; RF-15; RNF-05; ERS 3.1). */
"use strict";

document.addEventListener("DOMContentLoaded", async () => {
  const { el, api, formatarMoeda, formatarNota, formatarData } = Comum;
  const id = Number(location.pathname.split("/").pop());
  const params = new URLSearchParams(location.search);
  const estado = document.getElementById("estado-pagina");
  const MESES_VISIVEIS = 2;

  // "Voltar" leva de volta à busca com os mesmos critérios, se houver.
  if (document.referrer.includes("/busca?")) document.getElementById("voltar").href = document.referrer;

  let dados;
  try {
    const q = new URLSearchParams();
    for (const k of ["checkin", "checkout", "hospedes"]) if (params.get(k)) q.set(k, params.get(k));
    dados = await api(`/api/acomodacoes/${id}?${q.toString()}`);
  } catch (e) {
    estado.classList.remove("carregando");
    estado.replaceChildren(el("p", { class: "aviso erro", text: e.erro }), el("p", {}, el("a", { href: "/" }, "Fazer uma nova busca")));
    return;
  }

  document.title = `${dados.titulo} - Hospeda`;
  document.getElementById("titulo").textContent = dados.titulo;
  const loc = dados.localizacao;
  const notaTxt = dados.avaliacoes.notaMedia === null ? "Novo (sem avaliações)" : `★ ${formatarNota(dados.avaliacoes.notaMedia)} (${dados.avaliacoes.totalAvaliacoes})`;
  document.getElementById("subtitulo").textContent = `${loc.bairro}, ${loc.cidade} - ${loc.estado} · ${notaTxt}`;

  if (dados.ehDono) {
    document.getElementById("aviso-dono").append(el("p", { class: "aviso" },
      dados.ativo ? "Você é o anfitrião deste anúncio." : "Você é o anfitrião deste anúncio. Ele está desativado e não aparece para o público."));
  }

  // ---- fotos (armazenamento simulado) ----
  const galeria = document.getElementById("galeria");
  dados.fotos.slice(0, 5).forEach((f, i) => {
    const img = el("img", { src: f.url, alt: f.legenda || `Foto ${i + 1}`, loading: i ? "lazy" : "eager" });
    const fig = el("figure", {}, img);
    img.addEventListener("error", () => img.replaceWith(el("div", { class: "foto-falhou", text: `Foto indisponível: ${f.legenda || ""}` })));
    galeria.append(fig);
  });
  if (dados.fotos.length > 5) {
    galeria.after(el("p", { class: "dica", text: `Mais ${dados.fotos.length - 5} foto(s) neste anúncio.` }));
  }

  // ---- detalhes ----
  document.getElementById("fatos").append(
    el("li", { text: `Até ${dados.capacidadeMaxima} hóspede(s)` }),
    el("li", { text: `${dados.quartos} quarto(s)` }),
    el("li", { text: `${dados.banheiros} banheiro(s)` }),
    el("li", { text: `${dados.camas} cama(s)` }),
  );
  document.getElementById("anfitriao").append(
    `Anfitrião: ${dados.anfitriao.nome}`,
    dados.anfitriao.desde ? ` · na plataforma desde ${dados.anfitriao.desde} ` : " ",
    dados.anfitriao.superhost ? el("span", { class: "selo", text: "Superhost" }) : "",
  );
  document.getElementById("descricao").textContent = dados.descricao;
  document.getElementById("regras").textContent = dados.regras || "O anfitrião não definiu regras.";

  // ---- localização (RNF-05) ----
  const endereco = document.getElementById("endereco");
  if (loc.enderecoExato) {
    endereco.append(el("strong", {}, "Endereço: "), `${loc.rua}, ${loc.numero} - ${loc.bairro}, ${loc.cidade} - ${loc.estado}, CEP ${loc.cep}`);
  } else {
    endereco.append(`${loc.bairro}, ${loc.cidade} - ${loc.estado}. `,
      el("span", { class: "dica" }, "O endereço exato aparece depois que a sua reserva for confirmada."));
  }
  desenharMapa(loc.mapa);

  // ---- período vindo da busca ----
  const hPeriodo = document.getElementById("h-periodo");
  const periodo = document.getElementById("periodo");
  hPeriodo.append(formatarMoeda(dados.precoNoite), el("span", { class: "local" }, " por noite"));
  if (dados.periodo && dados.periodo.erros) {
    periodo.append(el("p", { class: "aviso erro" }, Object.values(dados.periodo.erros).join(" ")));
  } else if (dados.periodo) {
    const p = dados.periodo;
    periodo.append(
      el("p", {}, `${formatarData(p.checkin)} a ${formatarData(p.checkout)} · ${p.noites} noite(s)` + (p.hospedes ? ` · ${p.hospedes} hóspede(s)` : "")),
      p.disponivel
        ? el("p", { class: "aviso ok", text: "Disponível nessas datas." })
        : el("p", { class: "aviso erro", text: p.mensagens.join(" ") }),
    );
  } else {
    periodo.append(el("p", { class: "dica", text: "Escolha as datas na busca para ver a disponibilidade do seu período." }));
  }

  estado.hidden = true;
  document.getElementById("anuncio").hidden = false;

  carregarAvaliacoes();
  let inicioCalendario = mesDe(params.get("checkin")) || mesDe(Comum.isoHojeMais(0));
  carregarCalendario();
  document.getElementById("mes-anterior").addEventListener("click", () => { inicioCalendario = somarMeses(inicioCalendario, -MESES_VISIVEIS); carregarCalendario(); });
  document.getElementById("mes-seguinte").addEventListener("click", () => { inicioCalendario = somarMeses(inicioCalendario, MESES_VISIVEIS); carregarCalendario(); });

  // ------------------------------------------------------------------------
  function desenharMapa(mapa) {
    const alvo = document.getElementById("mapa");
    if (!mapa.disponivel) {
      alvo.append(el("p", { class: "aviso", text: mapa.mensagem }));
      return;
    }
    // Mapa esquemático (sem biblioteca externa): só o centro do bairro e um
    // círculo de raio aproximado, nunca o ponto exato (RNF-05).
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 400 220");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", `Mapa aproximado: ${mapa.descricao}, área de cerca de ${mapa.raio_metros} metros de raio.`);
    const add = (tag, attrs, texto) => {
      const n = document.createElementNS(ns, tag);
      for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
      if (texto) n.textContent = texto;
      svg.append(n);
    };
    add("rect", { width: 400, height: 220, fill: "#e9eef3" });
    for (let i = 0; i < 400; i += 40) add("line", { x1: i, y1: 0, x2: i + 60, y2: 220, stroke: "#ffffff", "stroke-width": 6 });
    for (let j = 20; j < 220; j += 50) add("line", { x1: 0, y1: j, x2: 400, y2: j + 15, stroke: "#ffffff", "stroke-width": 4 });
    add("circle", { cx: 200, cy: 110, r: 70, fill: "rgba(179,25,74,.18)", stroke: "#b3194a", "stroke-width": 2 });
    add("text", { x: 200, y: 115, "text-anchor": "middle", "font-size": 14, "font-family": "sans-serif", fill: "#1d1f23" }, mapa.descricao);
    add("text", { x: 8, y: 212, "font-size": 11, "font-family": "sans-serif", fill: "#4a4f57" },
      `Centro aproximado: ${mapa.latitude.toFixed(3)}, ${mapa.longitude.toFixed(3)} · serviço de mapas simulado`);
    alvo.append(svg);
  }

  async function carregarAvaliacoes() {
    const resumo = document.getElementById("resumo-avaliacoes");
    const lista = document.getElementById("avaliacoes");
    try {
      const r = await api(`/api/acomodacoes/${id}/avaliacoes`);
      if (r.totalAvaliacoes === 0) {
        resumo.textContent = "Esta acomodação ainda não tem avaliações publicadas.";
        return;
      }
      resumo.textContent = `Nota média ${formatarNota(r.notaMedia)} de 5, com ${r.totalAvaliacoes} avaliação(ões).`;
      lista.replaceChildren(...r.avaliacoes.map((a) => el("li", {},
        el("p", { style: "margin:0" },
          el("span", { class: "estrelas", "aria-hidden": "true" }, "★".repeat(a.nota) + "☆".repeat(5 - a.nota)),
          el("span", { class: "sr-only" }, `Nota ${a.nota} de 5`),
          ` · ${a.autor} · ${formatarData(a.dataAvaliacao)}`),
        el("p", { style: "margin:.25rem 0 0" }, a.comentario || el("em", { class: "local" }, "Sem comentário.")),
      )));
    } catch (e) {
      resumo.replaceChildren(el("span", { class: "aviso erro", text: e.erro }));
    }
  }

  function mesDe(iso) { return iso && /^\d{4}-\d{2}/.test(iso) ? iso.slice(0, 7) : null; }
  function somarMeses(aaaamm, n) {
    const [a, m] = aaaamm.split("-").map(Number);
    const d = new Date(a, m - 1 + n, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  }

  async function carregarCalendario() {
    const alvo = document.getElementById("calendario");
    const msg = document.getElementById("calendario-msg");
    const atual = mesDe(Comum.isoHojeMais(0));
    if (inicioCalendario < atual) inicioCalendario = atual;
    document.getElementById("mes-anterior").disabled = inicioCalendario <= atual;
    msg.replaceChildren();
    try {
      const r = await api(`/api/acomodacoes/${id}/calendario?mes=${inicioCalendario}&meses=${MESES_VISIVEIS}`);
      const ci = params.get("checkin"), co = params.get("checkout");
      alvo.replaceChildren(...r.meses.map((m) => tabelaMes(m, ci, co)));
      document.getElementById("mes-seguinte").disabled = false;
    } catch (e) {
      msg.replaceChildren(el("p", { class: "aviso erro", text: e.erro + (e.campos ? " " + Object.values(e.campos).join(" ") : "") }));
      if (e.status === 400) document.getElementById("mes-seguinte").disabled = true;
    }
  }

  function tabelaMes(mes, ci, co) {
    const [a, m] = mes.mes.split("-").map(Number);
    const nomeBruto = new Date(a, m - 1, 1).toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
    const nome = nomeBruto.charAt(0).toUpperCase() + nomeBruto.slice(1);
    const semana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
    const nomesSemana = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];
    const tabela = el("table", { class: "mes" }, el("caption", { text: nome }),
      el("thead", {}, el("tr", {}, semana.map((s, i) => el("th", { scope: "col", abbr: nomesSemana[i], text: s })))));
    const corpo = el("tbody");
    let linha = el("tr");
    const primeiroDia = new Date(a, m - 1, 1).getDay();
    for (let i = 0; i < primeiroDia; i++) linha.append(el("td"));
    for (const d of mes.dias) {
      if (linha.children.length === 7) { corpo.append(linha); linha = el("tr"); }
      const noPeriodo = ci && co && d.data >= ci && d.data < co;
      const rotulo = { livre: "livre", ocupado: "ocupado", passado: "data passada" }[d.situacao];
      linha.append(el("td", { class: `${d.situacao}${noPeriodo ? " no-periodo" : ""}` },
        el("span", { "aria-label": `${Number(d.data.slice(8))}: ${rotulo}${noPeriodo ? ", no período escolhido" : ""}` }, String(Number(d.data.slice(8))))));
    }
    while (linha.children.length < 7) linha.append(el("td"));
    corpo.append(linha);
    tabela.append(corpo);
    return tabela;
  }
});
