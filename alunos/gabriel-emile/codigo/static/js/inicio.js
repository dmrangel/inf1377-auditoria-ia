/* Tela inicial: valida a busca no servidor e, se estiver tudo certo, abre os resultados. */
"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-busca");
  const msg = document.getElementById("mensagem-busca");
  FormBusca.ajustarDatas(form);
  FormBusca.preencher(form, new URLSearchParams(location.search));

  document.getElementById("preencher-exemplo").addEventListener("click", () => {
    form.cidade.value = "Rio de Janeiro";
    form.estado.value = "RJ";
    form.bairro.value = "Copacabana";
    form.rua.value = "";
    form.checkin.value = Comum.isoHojeMais(14);
    form.checkout.value = Comum.isoHojeMais(17);
    form.hospedes.value = "2";
    form.cidade.focus();
  });

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const params = FormBusca.paraParametros(form);
    const botao = form.querySelector("button[type=submit]");
    botao.disabled = true;
    msg.replaceChildren();
    try {
      // O servidor é quem valida (RN-01, campos obrigatórios); só seguimos
      // para a página de resultados se a busca for aceita.
      await Comum.api("/api/acomodacoes/busca?" + params.toString());
      Comum.mostrarErrosCampos(form, {});
      location.href = "/busca?" + params.toString();
    } catch (e) {
      Comum.mostrarErrosCampos(form, e.campos || {});
      msg.replaceChildren(Comum.el("p", { class: "aviso erro", text: e.erro }));
    } finally {
      botao.disabled = false;
    }
  });
});
