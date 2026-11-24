// Tela "Anunciar espaço" (UC05) e "Editar acomodação" (UC06).
// As verificações aqui só ajudam o usuário; as regras valem no servidor.
"use strict";

const MIN_FOTOS = 5, MAX_FOTOS = 30, MAX_BYTES = 10 * 1024 * 1024;
const TIPOS = ["image/jpeg", "image/png"];
const CAMPOS = ["cep", "rua", "numero", "bairro", "cidade", "estado", "titulo", "descricao",
  "precoNoite", "capacidadeMaxima", "quartos", "banheiros", "camas", "regras"];
const CAMPOS_DO_CEP = ["rua", "bairro", "cidade", "estado"];

const modo = document.body.dataset.modo;
const idAcomodacao = document.body.dataset.id;
const form = document.getElementById("form-acomodacao");
const entradaFotos = document.getElementById("fotos");
const galeria = document.getElementById("galeria");
const contador = document.getElementById("contador-fotos");
const avisoCep = document.getElementById("aviso-cep");
const resumoErros = document.getElementById("resumo-erros");

let fotosNovas = [];     // modo "nova": File[] ainda não enviados
let fotosSalvas = [];    // modo "editar": fotos já no servidor
let acomodacao = null;

// ------------------------------------------------------------------ erros

function limparErros() {
  resumoErros.hidden = true;
  resumoErros.replaceChildren();
  form.querySelectorAll(".erro-campo").forEach(n => n.remove());
  form.querySelectorAll("[aria-invalid]").forEach(n => { n.removeAttribute("aria-invalid"); n.removeAttribute("aria-describedby"); });
}

/** Destaca os campos com erro e mantém os demais preenchidos (padrão do UC01, 4b). */
function mostrarErros(dados) {
  limparErros();
  const campos = dados.campos || {};
  const itens = [];
  for (const [nome, msg] of Object.entries(campos)) {
    const campo = document.getElementById(nome);
    if (campo) {
      const idErro = `erro-${nome}`;
      campo.setAttribute("aria-invalid", "true");
      campo.setAttribute("aria-describedby", idErro);
      campo.closest(".campo").append(el("p", { class: "erro-campo", id: idErro }, msg));
      itens.push(el("li", {}, el("a", { href: `#${nome}` }, msg)));
    }
  }
  resumoErros.replaceChildren(el("strong", {}, dados.erro || "Não foi possível salvar."), itens.length ? el("ul", {}, itens) : null);
  resumoErros.hidden = false;
  resumoErros.focus();
}

// ------------------------------------------------------------------ CEP (UC05 passo 3)

async function buscarCep() {
  const cep = document.getElementById("cep").value;
  avisoCep.textContent = "Consultando CEP…";
  const r = await api(`/api/cep/${encodeURIComponent(cep.replace(/\D/g, "") || "x")}`);
  liberarEnderecoDoCep();
  if (r.ok) {
    document.getElementById("cep").value = r.dados.cep;
    for (const c of CAMPOS_DO_CEP) {
      const campo = document.getElementById(c);
      if (r.dados[c]) { campo.value = r.dados[c]; campo.readOnly = true; }  // vem do serviço de CEP
      else campo.value = "";
    }
    const faltando = CAMPOS_DO_CEP.filter(c => !r.dados[c]);
    avisoCep.textContent = faltando.length
      ? "CEP geral da cidade: complete rua e bairro."
      : "";
    document.getElementById(faltando[0] || "numero").focus();
  } else {
    // UC05 fluxo 3a: CEP não encontrado (ou serviço fora do ar) → preenchimento manual.
    avisoCep.textContent = r.dados.erro;
    if (r.status !== 400) document.getElementById("rua").focus();
  }
}

// ------------------------------------------------------------------ fotos

function validarArquivo(arquivo) {
  if (!TIPOS.includes(arquivo.type)) return `"${arquivo.name}" não é JPEG nem PNG.`;
  if (arquivo.size > MAX_BYTES) return `"${arquivo.name}" tem mais de 10 MB.`;
  return null;
}

function atualizarContador() {
  const total = modo === "nova" ? fotosNovas.length : fotosSalvas.length;
  const falta = Math.max(0, MIN_FOTOS - total);
  contador.textContent = `${total} de ${MAX_FOTOS} fotos` + (falta ? ` · faltam ${falta} para o mínimo` : "");
}

function desenharGaleria() {
  const lista = modo === "nova"
    ? fotosNovas.map((f, i) => ({ url: URL.createObjectURL(f), nome: f.name, remover: () => { fotosNovas.splice(i, 1); desenharGaleria(); } }))
    : fotosSalvas.map((f, i) => ({ url: f.url, nome: `Foto ${i + 1}`, remover: () => removerFotoSalva(f) }));
  galeria.replaceChildren(...lista.map((f, i) => el("li", {},
    el("img", { src: f.url, alt: `${i === 0 ? "Capa: " : ""}${f.nome}` }),
    el("span", {}, i === 0 ? `${f.nome} (capa)` : f.nome),
    el("button", { type: "button", class: "botao perigo", onclick: f.remover, "aria-label": `Remover ${f.nome}` }, "Remover"))));
  atualizarContador();
}

async function aoEscolherFotos() {
  const arquivos = [...entradaFotos.files];
  entradaFotos.value = "";
  const erros = arquivos.map(validarArquivo).filter(Boolean);
  const validos = arquivos.filter(a => !validarArquivo(a));
  if (erros.length) mostrarMensagem(erros.join(" "), "erro"); else limparMensagem();

  if (modo === "nova") {
    const espaco = MAX_FOTOS - fotosNovas.length;
    if (validos.length > espaco) mostrarMensagem(`Máximo de ${MAX_FOTOS} fotos. Só ${espaco} foram adicionadas.`, "erro");
    fotosNovas.push(...validos.slice(0, espaco));
    desenharGaleria();
    return;
  }
  if (!validos.length) return;
  // Modo editar: envia na hora.
  const dados = new FormData();
  validos.forEach(a => dados.append("fotos", a, a.name));
  const r = await api(`/api/acomodacoes/${idAcomodacao}/fotos`, { method: "POST", body: dados });
  mostrarMensagem(r.ok ? r.dados.mensagem : r.dados.erro, r.ok ? "ok" : "erro");
  await carregarAcomodacao();
}

async function removerFotoSalva(foto) {
  const r = await api(`/api/acomodacoes/${idAcomodacao}/fotos/${foto.id}`, { method: "DELETE" });
  mostrarMensagem(r.ok ? r.dados.mensagem : r.dados.erro, r.ok ? "ok" : "erro");
  if (r.ok) await carregarAcomodacao();
}

// ------------------------------------------------------------------ envio

async function enviar(evento) {
  evento.preventDefault();
  limparMensagem();
  const botao = document.getElementById("enviar");
  botao.disabled = true;
  let r;
  if (modo === "nova") {
    if (fotosNovas.length < MIN_FOTOS) {
      // UC05 fluxo 5a (o servidor confere de novo).
      mostrarErros({ erro: `O anúncio precisa de no mínimo ${MIN_FOTOS} fotos. Você escolheu ${fotosNovas.length}.`, campos: { fotos: `Escolha pelo menos ${MIN_FOTOS} fotos.` } });
      botao.disabled = false;
      return;
    }
    const dados = new FormData();
    CAMPOS.forEach(c => dados.append(c, document.getElementById(c).value));
    fotosNovas.forEach(f => dados.append("fotos", f, f.name));
    r = await api("/api/acomodacoes", { method: "POST", body: dados });
  } else {
    const json = Object.fromEntries(CAMPOS.map(c => [c, document.getElementById(c).value]));
    r = await api(`/api/acomodacoes/${idAcomodacao}`, { method: "PUT", json });
  }
  botao.disabled = false;
  if (!r.ok) { mostrarErros(r.dados); return; }
  limparErros();
  if (modo === "nova") {
    window.location.href = "/anfitriao/acomodacoes";
  } else {
    mostrarMensagem(r.dados.mensagem, "ok");
    await carregarAcomodacao();
  }
}

// ------------------------------------------------------------------ edição

async function carregarAcomodacao() {
  const r = await api(`/api/acomodacoes/${idAcomodacao}`);
  if (!r.ok) {
    form.hidden = true;
    document.querySelector(".cabecalho-pagina .acoes")?.setAttribute("hidden", "");
    mostrarMensagem(r.dados.erro, "erro");
    return;
  }
  acomodacao = r.dados;
  document.getElementById("titulo-pagina").textContent = `Editar: ${acomodacao.titulo}`;
  for (const c of CAMPOS) {
    const valor = c === "precoNoite" ? acomodacao.precoNoite.replace(".", ",") : acomodacao[c];
    document.getElementById(c).value = valor;
  }
  fotosSalvas = acomodacao.fotos;
  desenharGaleria();
  const selo = document.getElementById("status-anuncio");
  selo.textContent = acomodacao.ativo ? "Publicado" : "Desativado";
  selo.className = `selo ${acomodacao.ativo ? "ativo" : "inativo"}`;
  const alternar = document.getElementById("alternar-ativo");
  alternar.textContent = acomodacao.ativo ? "Desativar" : "Reativar";
  alternar.className = `botao${acomodacao.ativo ? " perigo" : ""}`;
}

async function alternarAtivo(confirmar = false) {
  const acao = acomodacao.ativo ? "desativar" : "reativar";
  if (acao === "desativar" && !confirmar && !window.confirm("Desativar este anúncio? Ele deixará de aparecer nas buscas.")) return;
  const r = await api(`/api/acomodacoes/${idAcomodacao}/${acao}`, { method: "POST", json: { confirmar } });
  if (r.status === 409 && r.dados.codigo === "CONFIRMACAO_NECESSARIA") {
    const lista = r.dados.detalhes.map(x => `• ${x.hospede}: ${formatarData(x.checkIn)} a ${formatarData(x.checkOut)}`).join("\n");
    if (window.confirm(`${r.dados.erro}\n\n${lista}`)) return alternarAtivo(true);
    return;
  }
  mostrarMensagem(r.ok ? r.dados.mensagem : r.dados.erro, r.ok ? "ok" : "erro");
  await carregarAcomodacao();
}

// ------------------------------------------------------------------ início

document.getElementById("buscar-cep").addEventListener("click", buscarCep);
document.getElementById("cep").addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); buscarCep(); } });
// CEP mudou: o endereço preenchido pelo serviço deixa de valer (limpa e libera).
function liberarEnderecoDoCep() {
  for (const c of CAMPOS_DO_CEP) {
    const campo = document.getElementById(c);
    if (campo.readOnly) { campo.value = ""; campo.readOnly = false; }
  }
}
document.getElementById("cep").addEventListener("input", liberarEnderecoDoCep);
entradaFotos.addEventListener("change", aoEscolherFotos);
form.addEventListener("submit", enviar);

sessaoPronta.then(sessao => {
  if (modo === "editar") {
    document.getElementById("alternar-ativo").addEventListener("click", () => alternarAtivo());
    carregarAcomodacao();
  } else {
    if (sessao && !sessao.ehAnfitriao) {
      mostrarMensagem("Sua conta ainda não tem o papel de anfitrião. Ative-o no seu perfil para anunciar espaços.", "erro");
    }
    desenharGaleria();
  }
});
