/* cancelamento.js - Tela de confirmação do cancelamento (UC12 passos 2 e 3)
   - Evita envio duplo do formulário (o servidor também se protege com BEGIN IMMEDIATE).
   - Se o prazo do reembolso integral (RN-05) vencer com a tela aberta, avisa o usuário e
     bloqueia a confirmação: o valor mostrado deixou de valer. O servidor confere de novo
     o valor de qualquer forma (valor_exibido), então isto é só uma ajuda de usabilidade.
*/

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("formCancelar");
  const botao = document.getElementById("btnConfirmarCancelamento");
  const aviso = document.getElementById("avisoPrazo");
  if (!form || !botao) return;

  form.addEventListener("submit", (evento) => {
    if (botao.disabled) {
      evento.preventDefault();
      return;
    }
    botao.disabled = true;
    botao.textContent = "Cancelando e solicitando o reembolso...";
  });

  if (form.dataset.regra !== "HOSPEDE_INTEGRAL" || !form.dataset.prazoIntegral) return;

  const prazo = new Date(form.dataset.prazoIntegral);
  if (isNaN(prazo.getTime())) return;

  const verificarPrazo = () => {
    if (new Date() >= prazo) {
      clearInterval(intervalo);
      botao.disabled = true;
      aviso.textContent = "O prazo do reembolso integral acabou enquanto esta tela estava aberta. " +
        "Recarregue a página para ver o novo valor antes de confirmar.";
      aviso.style.display = "flex";
    }
  };
  const intervalo = setInterval(verificarPrazo, 1000);
  verificarPrazo();
});
