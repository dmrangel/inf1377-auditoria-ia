/* Formulário de busca, usado na tela inicial e na página de resultados. */
"use strict";

const FormBusca = (() => {
  const CAMPOS_LOCAL = ["cidade", "estado", "bairro", "rua", "checkin", "checkout", "hospedes"];
  const CAMPOS_FILTRO = ["preco_min", "preco_max", "quartos", "banheiros", "camas", "ordenar"];

  /** Lê os campos preenchidos de um ou mais formulários em URLSearchParams. */
  function paraParametros(...forms) {
    const p = new URLSearchParams();
    for (const form of forms) {
      for (const [k, v] of new FormData(form).entries()) {
        const valor = String(v).trim();
        if (valor !== "") p.set(k, valor);
      }
    }
    return p;
  }

  /** Preenche os campos do formulário a partir da URL. */
  function preencher(form, params) {
    for (const nome of [...CAMPOS_LOCAL, ...CAMPOS_FILTRO]) {
      const input = form.elements[nome]; // inclui campos ligados por form="..."
      if (input && params.has(nome)) input.value = params.get(nome);
    }
  }

  /** Datas mínimas no seletor (o servidor valida de novo). */
  function ajustarDatas(form) {
    const hoje = Comum.isoHojeMais(0);
    const ci = form.querySelector("[name=checkin]");
    const co = form.querySelector("[name=checkout]");
    ci.min = hoje;
    co.min = Comum.isoHojeMais(1);
    ci.addEventListener("change", () => {
      if (!ci.value) return;
      const d = new Date(ci.value + "T12:00:00");
      d.setDate(d.getDate() + 1);
      co.min = d.toISOString().slice(0, 10);
      if (co.value && co.value <= ci.value) co.value = co.min;
    });
  }

  return { paraParametros, preencher, ajustarDatas, CAMPOS_LOCAL, CAMPOS_FILTRO };
})();
