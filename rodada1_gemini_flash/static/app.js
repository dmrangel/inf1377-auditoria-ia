let currentTxid = null;
let pollingInterval = null;

function criarReserva(acomodacaoId, checkin, checkout, numHospedes) {
    const btn = document.getElementById('btn-confirmar-resumo');
    btn.disabled = true;
    btn.innerText = 'Processando...';

    fetch('/api/reservas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            acomodacao_id: acomodacaoId,
            checkin: checkin,
            checkout: checkout,
            num_hospedes: numHospedes
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.redirect_url) {
            window.location.href = data.redirect_url;
        } else {
            alert(data.erro || 'Falha ao iniciar reserva');
            btn.disabled = false;
            btn.innerText = 'Confirmar e Ir para Pagamento';
        }
    })
    .catch(() => {
        alert('Erro de comunicação com o servidor');
        btn.disabled = false;
    });
}

function alternarMetodo(metodo) {
    const secaoCartao = document.getElementById('secao-cartao');
    const secaoPix = document.getElementById('secao-pix');
    const btns = document.querySelectorAll('.tab-btn');
    
    if (metodo === 'cartao') {
        secaoCartao.style.display = 'block';
        secaoPix.style.display = 'none';
        btns[0].classList.add('active');
        btns[1].classList.remove('active');
        if (pollingInterval) clearInterval(pollingInterval);
    } else {
        secaoCartao.style.display = 'none';
        secaoPix.style.display = 'block';
        btns[1].classList.add('active');
        btns[0].classList.remove('active');
    }
}

function pagarCartao(e, reservaId) {
    e.preventDefault();
    const btn = document.getElementById('btn-pagar-cartao');
    const erroDiv = document.getElementById('msg-erro-cartao');
    const num = document.getElementById('cartao_num').value;

    btn.disabled = true;
    btn.innerText = 'Autorizando transação (RNF-02)...';
    erroDiv.style.display = 'none';

    fetch(`/api/reservas/${reservaId}/pagar-cartao`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ numero_cartao: num })
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerText = 'Pagar com Cartão';
        if (data.status === 'APROVADO') {
            window.location.href = data.redirect_url;
        } else {
            erroDiv.innerText = data.mensagem || 'Pagamento recusado.';
            erroDiv.style.display = 'block';
        }
    })
    .catch(() => {
        btn.disabled = false;
        btn.innerText = 'Pagar com Cartão';
        erroDiv.innerText = 'Falha no processamento da autorização.';
        erroDiv.style.display = 'block';
    });
}

function gerarPix(reservaId) {
    fetch(`/api/reservas/${reservaId}/gerar-pix`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
        currentTxid = data.txid;
        document.getElementById('pix-qrcode').src = data.qr_code_simulado;
        document.getElementById('pix-copiacola').value = data.copia_cola;
        document.getElementById('pix-detalhes').style.display = 'block';

        // RF-23: Inicia polling assíncrono para verificar compensação
        if (pollingInterval) clearInterval(pollingInterval);
        pollingInterval = setInterval(() => {
            fetch(`/api/reservas/${reservaId}/status`)
            .then(r => r.json())
            .then(res => {
                if (res.status === 'CONFIRMADA') {
                    clearInterval(pollingInterval);
                    window.location.href = `/reservas/${reservaId}/confirmacao`;
                }
            });
        }, 2000);
    });
}

function simularWebhookPix(valor) {
    if (!currentTxid) return alert('Gere o código PIX antes de disparar o webhook');
    fetch('/api/webhook/pix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ txid: currentTxid, valor: valor })
    })
    .then(r => r.json())
    .then(data => alert('Notificação Webhook: ' + (data.mensagem || data.erro)));
}
