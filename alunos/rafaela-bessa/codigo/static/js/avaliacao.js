/*
 * avaliacao.js - Formulário de avaliação de estadia (UC18 / UC19)
 * JavaScript puro. As regras (RF-29 a RF-31, RN-06) são verificadas no servidor;
 * aqui só há validação de conveniência e o envio por fetch em JSON (seção 3.4).
 */
(function () {
  "use strict";

  const form = document.getElementById("formAvaliacao");
  if (!form) return; // a tela não mostra o formulário (já avaliou, prazo encerrado etc.)

  const reservaId = form.dataset.reservaId;
  const comentarioMax = parseInt(form.dataset.comentarioMax, 10);
  const radios = Array.from(form.querySelectorAll('input[name="nota"]'));
  const labels = Array.from(form.querySelectorAll(".estrela-label"));
  const rotuloNota = document.getElementById("rotuloNota");
  const comentario = document.getElementById("comentario");
  const contador = document.getElementById("contadorComentario");
  const alerta = document.getElementById("alertaAvaliacao");
  const botao = document.getElementById("btnEnviarAvaliacao");
  const ROTULOS = ["Péssimo", "Ruim", "Regular", "Bom", "Excelente"];

  function notaSelecionada() {
    const marcado = radios.find((r) => r.checked);
    return marcado ? parseInt(marcado.value, 10) : null;
  }

  // Pinta as estrelas até o valor informado (seleção atual ou hover).
  function pintar(valor) {
    labels.forEach((label) => {
      label.classList.toggle("ativa", parseInt(label.dataset.valor, 10) <= (valor || 0));
    });
  }

  function atualizarRotulo() {
    const nota = notaSelecionada();
    rotuloNota.textContent = nota ? `${nota} de 5 estrelas: ${ROTULOS[nota - 1]}` : "Escolha de 1 a 5 estrelas.";
    pintar(nota);
  }

  radios.forEach((radio) => radio.addEventListener("change", atualizarRotulo));
  labels.forEach((label) => {
    label.addEventListener("mouseenter", () => pintar(parseInt(label.dataset.valor, 10)));
    label.addEventListener("mouseleave", () => pintar(notaSelecionada()));
  });

  comentario.addEventListener("input", () => {
    contador.textContent = `${comentario.value.length} de ${comentarioMax} caracteres`;
  });

  function mostrarErro(mensagem) {
    alerta.textContent = mensagem;
    alerta.style.display = "flex";
    alerta.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    alerta.style.display = "none";

    const nota = notaSelecionada();
    if (!nota) {
      mostrarErro("Escolha uma nota de 1 a 5 estrelas antes de enviar (RF-29).");
      radios[0].focus();
      return;
    }
    if (comentario.value.trim().length > comentarioMax) {
      mostrarErro(`O comentário pode ter no máximo ${comentarioMax} caracteres.`);
      comentario.focus();
      return;
    }

    botao.disabled = true;
    botao.textContent = "Enviando...";
    try {
      const resposta = await fetch(`/api/reservas/${reservaId}/avaliacoes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nota: nota, comentario: comentario.value }),
      });
      const dados = await resposta.json().catch(() => ({}));
      if (resposta.status === 201) {
        // Recarrega a tela para mostrar a avaliação gravada e o estado da publicação.
        window.location.href = `/reservas/${reservaId}/avaliar?enviada=1`;
        return;
      }
      mostrarErro(dados.mensagem || "Não foi possível enviar a avaliação. Tente novamente.");
    } catch (erro) {
      mostrarErro("Não foi possível falar com o servidor. Verifique sua conexão e tente novamente.");
    }
    botao.disabled = false;
    botao.textContent = "Enviar avaliação";
  });
})();
