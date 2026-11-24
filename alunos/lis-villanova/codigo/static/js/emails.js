// emails.js - Caixa de saída do serviço de e-mail simulado.
"use strict";

async function carregarEmails() {
  const r = await chamarApi("GET", "/api/simulacao/emails");
  if (!r.ok) {
    mostrarMensagem(r.dados.erro || "Não foi possível carregar os e-mails.", "erro");
    return;
  }
  document.getElementById("simular-falha").checked = r.dados.simularFalha;
  const lista = document.getElementById("lista-emails");
  const modelo = document.getElementById("modelo-email");
  lista.replaceChildren();
  if (r.dados.mensagens.length === 0) {
    mostrarMensagem("Nenhum e-mail enviado ainda.", "alerta");
    return;
  }
  mostrarMensagem("");
  for (const m of r.dados.mensagens) {
    const item = modelo.content.cloneNode(true);
    // textContent (e não innerHTML): o conteúdo vem de dados digitados por usuários.
    item.querySelector("[data-campo=enviadoEm]").textContent = new Date(m.enviadoEm).toLocaleString("pt-BR");
    item.querySelector("[data-campo=para]").textContent = m.para;
    item.querySelector("[data-campo=assunto]").textContent = m.assunto;
    item.querySelector("[data-campo=corpo]").textContent = m.corpo;
    if (m.link) {
      item.querySelector("[data-campo=link-area]").hidden = false;
      item.querySelector("[data-campo=link]").href = m.link;
    }
    lista.appendChild(item);
  }
}

document.getElementById("botao-atualizar").addEventListener("click", carregarEmails);
document.getElementById("simular-falha").addEventListener("change", async (evento) => {
  const r = await chamarApi("POST", "/api/simulacao/email-falha", { falhar: evento.target.checked });
  if (r.ok) {
    mostrarMensagem(r.dados.simularFalha ? "Serviço de e-mail agora falha em todo envio."
                                         : "Serviço de e-mail voltou a funcionar.", "alerta");
  }
});
carregarEmails();
