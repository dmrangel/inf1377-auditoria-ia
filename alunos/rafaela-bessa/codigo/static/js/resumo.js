/* resumo.js - Lógica interativa da Tela 1 (Resumo da Estadia)
   Validações: RN-01 (datas), RN-02 (capacidade), RF-18 / RN-03 / RN-07 (cálculo de taxas)
*/

document.addEventListener("DOMContentLoaded", () => {
  const checkInInput = document.getElementById("checkIn");
  const checkOutInput = document.getElementById("checkOut");
  const numHospedesInput = document.getElementById("numHospedes");
  const formResumo = document.getElementById("formResumo");
  const alertBox = document.getElementById("validationAlert");
  const btnSubmit = document.getElementById("btnConfirmarReserva");

  const precoNoite = parseFloat(document.getElementById("precoNoiteVal").value || 0);
  const capacidadeMaxima = parseInt(document.getElementById("capacidadeMaximaVal").value || 1, 10);
  const ehSuperhost = document.getElementById("ehSuperhostVal").value === "1";

  // Formatação em Real Brasileiro (R$)
  const formatMoney = (val) => {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(val);
  };

  // Recalcular discriminativo financeiro e validar campos
  const atualizarValores = () => {
    const cIn = checkInInput.value;
    const cOut = checkOutInput.value;
    const hospedes = parseInt(numHospedesInput.value || 1, 10);

    // Limpar alerta anterior
    alertBox.style.display = "none";
    alertBox.textContent = "";
    btnSubmit.disabled = false;

    if (!cIn || !cOut) {
      return;
    }

    const dIn = new Date(cIn + "T00:00:00");
    const dOut = new Date(cOut + "T00:00:00");

    // RN-01: Check-out posterior ao check-in com no mínimo 1 noite
    const diffTime = dOut.getTime() - dIn.getTime();
    const diffDays = Math.round(diffTime / (1000 * 3600 * 24));

    if (diffDays < 1) {
      alertBox.textContent = "A data de check-out deve ser posterior ao check-in em pelo menos 1 noite (RN-01).";
      alertBox.style.display = "block";
      btnSubmit.disabled = true;
      return;
    }

    // RN-02: Número de hóspedes não pode ultrapassar capacidade máxima
    if (hospedes > capacidadeMaxima) {
      alertBox.textContent = `O número de hóspedes (${hospedes}) ultrapassa a capacidade máxima do imóvel (${capacidadeMaxima} pessoas) (RN-02).`;
      alertBox.style.display = "block";
      btnSubmit.disabled = true;
      return;
    }

    if (hospedes < 1) {
      alertBox.textContent = "O número de hóspedes deve ser de pelo menos 1.";
      alertBox.style.display = "block";
      btnSubmit.disabled = true;
      return;
    }

    // Cálculos financeiros (RF-18, RN-03, RN-07)
    const subtotal = diffDays * precoNoite;
    const taxaBase = Math.round(subtotal * 0.14 * 100) / 100;
    const descontoSuperhost = ehSuperhost ? Math.round(taxaBase * 0.10 * 100) / 100 : 0;
    const taxaFinal = Math.round((taxaBase - descontoSuperhost) * 100) / 100;
    const total = Math.round((subtotal + taxaFinal) * 100) / 100;

    // Atualizar UI
    document.getElementById("lblNumNoites").textContent = diffDays;
    document.getElementById("valSubtotal").textContent = formatMoney(subtotal);
    document.getElementById("valTaxaServico").textContent = formatMoney(taxaBase);

    const rowDesconto = document.getElementById("rowDescontoSuperhost");
    if (rowDesconto) {
      if (ehSuperhost) {
        document.getElementById("valDesconto").textContent = `- ${formatMoney(descontoSuperhost)}`;
        rowDesconto.style.display = "flex";
      } else {
        rowDesconto.style.display = "none";
      }
    }

    document.getElementById("valTotal").textContent = formatMoney(total);
  };

  checkInInput.addEventListener("change", atualizarValores);
  checkOutInput.addEventListener("change", atualizarValores);
  numHospedesInput.addEventListener("input", atualizarValores);

  // Execução inicial
  atualizarValores();
});
