/* pagamento.js - Lógica interativa da Tela 2 (Pagamento)
   Conforme: RF-23 a RF-26, RN-04 (timer 30 min), RNF-08 (tokenização/segurança)
*/

document.addEventListener("DOMContentLoaded", () => {
  const reservaId = window.RESERVA_ID;
  let segundosRestantes = window.RESERVA_SEGUNDOS_RESTANTES || 0;
  const statusReserva = window.RESERVA_STATUS;

  const timerDisplay = document.getElementById("timerDisplay");
  const tabCartao = document.getElementById("tabBtnCartao");
  const tabPix = document.getElementById("tabBtnPix");
  const paneCartao = document.getElementById("paneCartao");
  const panePix = document.getElementById("panePix");

  const formCartao = document.getElementById("formCartao");
  const btnPagarCartao = document.getElementById("btnPagarCartao");
  const cardErrorAlert = document.getElementById("cardErrorAlert");

  const pixLoading = document.getElementById("pixLoading");
  const pixContent = document.getElementById("pixContent");
  const pixQrContainer = document.getElementById("pixQrContainer");
  const pixCopiaCola = document.getElementById("pixCopiaCola");
  const btnCopiarPix = document.getElementById("btnCopiarPix");
  const btnSimularPix = document.getElementById("btnSimularPix");

  let pixTxid = null;
  let pixValor = null;
  let pollingInterval = null;

  // ---------------------------------------------------------
  // 1. Temporizador de 30 minutos (RN-04)
  // ---------------------------------------------------------
  const formatTimer = (totalSec) => {
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  const timerInterval = setInterval(() => {
    if (statusReserva !== "PENDENTE") {
      clearInterval(timerInterval);
      return;
    }

    if (segundosRestantes <= 0) {
      clearInterval(timerInterval);
      if (pollingInterval) clearInterval(pollingInterval);

      timerDisplay.textContent = "00:00 - EXPIRADA";
      timerDisplay.style.color = "var(--danger)";

      const container = document.querySelector(".timer-container");
      if (container) {
        container.style.backgroundColor = "var(--danger-bg)";
        container.style.borderColor = "#fecaca";
      }

      // Desativar formulários
      if (btnPagarCartao) btnPagarCartao.disabled = true;
      if (btnSimularPix) btnSimularPix.disabled = true;

      // Alerta de cancelamento automático
      const alertDiv = document.createElement("div");
      alertDiv.className = "alert alert-danger";
      alertDiv.innerHTML = "<strong>Tempo esgotado!</strong> Esta reserva foi cancelada automaticamente após 30 minutos sem aprovação de pagamento (RN-04). Por favor, inicie uma nova reserva.";
      document.querySelector(".main-content").prepend(alertDiv);
      return;
    }

    timerDisplay.textContent = formatTimer(segundosRestantes);
    segundosRestantes--;
  }, 1000);

  // ---------------------------------------------------------
  // 2. Troca de Abas (Cartão de Crédito vs PIX)
  // ---------------------------------------------------------
  tabCartao.addEventListener("click", () => {
    tabCartao.classList.add("active");
    tabPix.classList.remove("active");
    paneCartao.classList.add("active");
    panePix.classList.remove("active");
  });

  tabPix.addEventListener("click", () => {
    tabPix.classList.add("active");
    tabCartao.classList.remove("active");
    panePix.classList.add("active");
    paneCartao.classList.remove("active");

    // Gerar cobrança PIX se ainda não gerada
    if (!pixTxid) {
      carregarPix();
    }
  });

  // ---------------------------------------------------------
  // 3. Pagamento por Cartão de Crédito (Síncrono - RF-23, RF-26)
  // ---------------------------------------------------------
  formCartao.addEventListener("submit", async (e) => {
    e.preventDefault();
    cardErrorAlert.style.display = "none";
    btnPagarCartao.disabled = true;
    btnPagarCartao.textContent = "Processando pagamento no gateway...";

    const payload = {
      reserva_id: reservaId,
      titular: document.getElementById("cardHolder").value,
      numero_cartao: document.getElementById("cardNumber").value,
      validade: document.getElementById("cardExp").value,
      cvv: document.getElementById("cardCvv").value
    };

    try {
      const response = await fetch("/api/pagamento/cartao", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok && data.sucesso) {
        // Redireciona para Tela 3: Confirmação
        window.location.href = `/confirmacao/${reservaId}`;
      } else {
        // RF-26: Falha no pagamento permite nova tentativa
        cardErrorAlert.textContent = data.mensagem || "Não foi possível autorizar o pagamento. Verifique os dados ou tente outro cartão.";
        cardErrorAlert.style.display = "block";
        btnPagarCartao.disabled = false;
        btnPagarCartao.textContent = "Tentar novamente";
      }
    } catch (err) {
      cardErrorAlert.textContent = "Erro de conexão ao comunicar com o servidor de pagamento. Tente novamente.";
      cardErrorAlert.style.display = "block";
      btnPagarCartao.disabled = false;
      btnPagarCartao.textContent = "Tentar novamente";
    }
  });

  // ---------------------------------------------------------
  // 4. Pagamento por PIX (Assíncrono - RF-23, RF-24, UC16 passo 4b)
  // ---------------------------------------------------------
  const carregarPix = async () => {
    pixLoading.style.display = "block";
    pixContent.style.display = "none";

    try {
      const response = await fetch("/api/pagamento/pix/gerar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reserva_id: reservaId })
      });

      const data = await response.json();
      if (response.ok && data.sucesso) {
        pixTxid = data.cobranca.txid;
        pixValor = data.cobranca.valor;

        pixQrContainer.innerHTML = data.cobranca.qrCodeSvg;
        pixCopiaCola.value = data.cobranca.copiaECola;

        pixLoading.style.display = "none";
        pixContent.style.display = "block";

        // Iniciar polling a cada 3 segundos para detectar confirmação do webhook
        iniciarPollingPix();
      } else {
        pixLoading.innerHTML = `<span style="color:var(--danger)">Erro ao gerar cobrança PIX: ${data.mensagem}</span>`;
      }
    } catch (err) {
      pixLoading.innerHTML = '<span style="color:var(--danger)">Erro ao comunicar com o gateway de PIX.</span>';
    }
  };

  const iniciarPollingPix = () => {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/reservas/${reservaId}/status`);
        const info = await res.json();
        if (info.status === "CONFIRMADA") {
          clearInterval(pollingInterval);
          window.location.href = `/confirmacao/${reservaId}`;
        } else if (info.status === "CANCELADA") {
          clearInterval(pollingInterval);
          window.location.reload();
        }
      } catch (e) {
        // Silencia erros transitórios de rede no polling
      }
    }, 3000);
  };

  // Botão de Copiar Código PIX
  btnCopiarPix.addEventListener("click", () => {
    pixCopiaCola.select();
    navigator.clipboard.writeText(pixCopiaCola.value).then(() => {
      const origText = btnCopiarPix.textContent;
      btnCopiarPix.textContent = "✓ Código Copiado!";
      setTimeout(() => { btnCopiarPix.textContent = origText; }, 2500);
    });
  });

  // Botão de Simulação do Webhook para testes
  btnSimularPix.addEventListener("click", async () => {
    if (!pixTxid) return;
    btnSimularPix.disabled = true;
    btnSimularPix.textContent = "Enviando aviso bancário via webhook...";

    try {
      const res = await fetch("/api/webhook/pix", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          txid: pixTxid,
          valor: pixValor,
          status: "APROVADO"
        })
      });
      const data = await res.json();
      if (data.sucesso) {
        // O polling ou este retorno redireciona
        window.location.href = `/confirmacao/${reservaId}`;
      } else {
        alert("Erro na simulação do webhook: " + data.mensagem);
        btnSimularPix.disabled = false;
        btnSimularPix.textContent = "⚡ Simular Notificação do Banco (Webhook)";
      }
    } catch (e) {
      alert("Falha ao acionar webhook simulado.");
      btnSimularPix.disabled = false;
      btnSimularPix.textContent = "⚡ Simular Notificação do Banco (Webhook)";
    }
  });
});
