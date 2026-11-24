// Tela "Calendário" (RF-10): bloquear e desbloquear noites.
"use strict";

const idAcomodacao = document.body.dataset.id;
const grade = document.getElementById("grade");
const tituloMes = document.getElementById("titulo-mes");
const campoInicio = document.getElementById("inicio");
const campoFim = document.getElementById("fim");
let mesAtual = null;      // "AAAA-MM"
let cliqueInicial = null; // primeira data clicada na grade

function somarMes(mes, delta) {
  const [a, m] = mes.split("-").map(Number);
  const d = new Date(a, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

async function carregar(mes) {
  const r = await api(`/api/acomodacoes/${idAcomodacao}/calendario${mes ? `?mes=${mes}` : ""}`);
  if (!r.ok) {
    document.getElementById("form-periodo").hidden = true;
    mostrarMensagem(r.dados.erro, "erro");
    return;
  }
  mesAtual = r.dados.mes;
  desenhar(r.dados);
}

function desenhar(dados) {
  const [a, m] = dados.mes.split("-").map(Number);
  tituloMes.textContent = new Date(a, m - 1, 1).toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
  const bloqueadas = new Set(dados.bloqueadas);
  const celulas = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"].map(d => el("div", { class: "cab-semana", role: "columnheader" }, d));
  const primeiroDia = new Date(a, m - 1, 1).getDay();
  for (let i = 0; i < primeiroDia; i++) celulas.push(el("div", { "aria-hidden": "true" }));
  const diasNoMes = new Date(a, m, 0).getDate();
  for (let d = 1; d <= diasNoMes; d++) {
    const iso = `${dados.mes}-${String(d).padStart(2, "0")}`;
    let estado = "livre", rotulo = "livre";
    if (iso < dados.hoje) { estado = "passada"; rotulo = "já passou"; }
    else if (dados.reservadas[iso]) { estado = "reservada"; rotulo = `reservada (${NOMES_STATUS[dados.reservadas[iso].status].toLowerCase()})`; }
    else if (bloqueadas.has(iso)) { estado = "bloqueada"; rotulo = "bloqueada"; }
    celulas.push(el("button", {
      type: "button", role: "gridcell", class: `dia ${estado}`, "data-data": iso,
      "aria-label": `${formatarData(iso)}: ${rotulo}`,
      disabled: estado === "passada" || estado === "reservada",
      onclick: () => selecionar(iso),
    }, String(d), estado !== "livre" && estado !== "passada" ? el("small", {}, rotulo.split(" ")[0]) : null));
  }
  grade.replaceChildren(...celulas);
  destacarSelecao();
}

/** Dois cliques na grade preenchem primeira e última noite. */
function selecionar(iso) {
  if (!cliqueInicial || campoFim.value) {
    cliqueInicial = iso; campoInicio.value = iso; campoFim.value = "";
  } else {
    const [i, f] = iso < cliqueInicial ? [iso, cliqueInicial] : [cliqueInicial, iso];
    campoInicio.value = i; campoFim.value = f; cliqueInicial = null;
  }
  destacarSelecao();
}

function destacarSelecao() {
  const i = campoInicio.value, f = campoFim.value || campoInicio.value;
  grade.querySelectorAll(".dia").forEach(b => b.classList.toggle("selecionada", !!i && b.dataset.data >= i && b.dataset.data <= f));
}

async function enviar(evento) {
  evento.preventDefault();
  const acao = evento.submitter?.dataset.acao || "bloquear";
  const inicio = campoInicio.value, fim = campoFim.value || campoInicio.value;
  if (!inicio) { mostrarMensagem("Escolha a primeira noite.", "erro"); campoInicio.focus(); return; }
  const r = await api(`/api/acomodacoes/${idAcomodacao}/bloqueios`,
    { method: acao === "bloquear" ? "POST" : "DELETE", json: { inicio, fim } });
  let texto = r.ok ? r.dados.mensagem : r.dados.erro;
  if (!r.ok && Array.isArray(r.dados.detalhes)) {
    texto += " Reservas no período: " + r.dados.detalhes.map(x => `${formatarData(x.checkIn)} a ${formatarData(x.checkOut)}`).join("; ") + ".";
  }
  mostrarMensagem(texto, r.ok ? "ok" : "erro");
  if (r.ok) { campoInicio.value = ""; campoFim.value = ""; }
  carregar(mesAtual);
}

async function carregarNome() {
  const r = await api(`/api/acomodacoes/${idAcomodacao}`);
  if (r.ok) document.getElementById("nome-acomodacao").textContent = r.dados.titulo;
}

document.getElementById("mes-anterior").addEventListener("click", () => carregar(somarMes(mesAtual, -1)));
document.getElementById("mes-seguinte").addEventListener("click", () => carregar(somarMes(mesAtual, 1)));
document.getElementById("form-periodo").addEventListener("submit", enviar);
[campoInicio, campoFim].forEach(c => c.addEventListener("change", destacarSelecao));

sessaoPronta.then(() => { carregarNome(); carregar(); });
