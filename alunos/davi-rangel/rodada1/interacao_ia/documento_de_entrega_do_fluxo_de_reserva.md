# Documentação Técnica e Código-Fonte: Fluxo de Reserva, Pagamento e Confirmação
**Referência:** Especificação de Requisitos de Software (ERS v1.1 — Padrão IEEE 830)  
**Stack Tecnológica:** Python 3 + Flask, SQLite, HTML5/CSS3/JavaScript Vanilla, Pytest.

---

## Sumário
1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Tabela de Rastreabilidade](#2-tabela-de-rastreabilidade)
3. [Registro de Ambiguidades e Decisões de Projeto](#3-registro-de-ambiguidades-e-decisões-de-projeto)
4. [Código-Fonte dos Módulos](#4-código-fonte-dos-módulos)
   - `requirements.txt`
   - `database.py`
   - `models.py`
   - `services/payment_gateway.py`
   - `services/email_service.py`
   - `app.py`
   - `templates/base.html`
   - `templates/index.html`
   - `templates/resumo.html` (Tela 1)
   - `templates/pagamento.html` (Tela 2)
   - `templates/confirmacao.html` (Tela 3)
   - `static/style.css`
   - `static/app.js`
   - `tests/test_fluxo.py`
5. [Manual de Execução e Guia de Testes (`README.md`)](#5-manual-de-execução-e-guia-de-testes)

---

## 1. Visão Geral da Arquitetura

O sistema atende integralmente ao fluxo de 3 telas estipulado na **Seção 3.1** da ERS:
- **Tela 1 — Resumo da Estadia (`/reservas/resumo`)**: Cálculo discriminado das diárias, aplicação da taxa de serviço de 14% (RN-03), verificação dinâmica de elegibilidade do Superhost para abatimento de 10% sobre a taxa (RN-07 / RF-18), e validações de negócio (RN-01, RN-02, RF-19). Em observância a **RNF-05**, apenas bairro, cidade e estado são informados.
- **Tela 2 — Pagamento (`/reservas/<id>/pagamento`)**: Apresenta suporte síncrono para Cartão de Crédito e suporte assíncrono para PIX via webhook (RF-23). Controla o tempo de expiração de 30 minutos (RN-04) e não armazena dados sensíveis de pagamento (RNF-08). Permite nova tentativa em caso de recusa (RF-26).
- **Tela 3 — Confirmação (`/reservas/<id>/confirmacao`)**: Renderizada estritamente após a transição da reserva para `CONFIRMADA`. Revela os dados de autorização, comprovante de envio de e-mail (RF-28) e **o endereço completo da acomodação** (rua, número e CEP) em cumprimento a **RNF-05**.

---

## 2. Tabela de Rastreabilidade

| ID ERS | Tipo | Descrição Sumária | Onde foi Implementado | Como Testar / Validar |
| :--- | :--- | :--- | :--- | :--- |
| **RF-17** | Funcional | Criação de reserva com check-in, check-out e hóspedes | `app.py: criar_reserva()`, `templates/resumo.html` | Acessar a tela inicial, selecionar período e submeter formulário. |
| **RF-18** | Funcional | Cálculo de total: noites $\times$ preço + taxa 14% - desconto Superhost | `models.py: calcular_valores()` | Executar `pytest tests/test_fluxo.py -k test_rf18_rn07_desconto_superhost`. |
| **RF-19** | Funcional | Impedir reservas sobrepostas para o mesmo imóvel | `models.py: validar_disponibilidade()` | Executar `pytest tests/test_fluxo.py -k test_rf19_impedir_sobreposicao`. |
| **RF-20** | Funcional | Controle dos estados da reserva: `PENDENTE`, `CONFIRMADA`, `CANCELADA` | `database.py: reserva`, `app.py` | Conferir transições no banco ao pagar ou expirar reserva. |
| **RF-23** | Funcional | Pagamento via Cartão (síncrono) e PIX (assíncrono com txid único) | `services/payment_gateway.py`, `app.py: pagar_cartao, webhook_pix` | Executar `pytest tests/test_fluxo.py -k test_fluxo_pix_assincrono`. |
| **RF-24** | Funcional | Registro de valor, autorização, txid e data/hora | `database.py: tabela pagamento`, `app.py` | Checar registros gerados na tabela `pagamento`. |
| **RF-25** | Funcional | Controle de status do pagamento: `PROCESSANDO`, `APROVADO`, `RECUSADO` | `database.py: tabela pagamento` | Simular pagamento com cartão final `0000` (recusa) e final padrão (aprovação). |
| **RF-26** | Funcional | Permitir nova tentativa após recusa | `app.py: pagar_cartao()`, `templates/pagamento.html` | Executar `pytest tests/test_fluxo.py -k test_fluxo_cartao_recusa_e_aprovacao`. |
| **RF-28** | Funcional | Emissão de comprovante por e-mail | `services/email_service.py` | Conferir log do serviço `EmailServiceSimulado` após aprovação. |
| **RN-01** | Negócio | Check-out posterior ao check-in (mínimo 1 noite) | `models.py`, `app.py: tela_resumo` | Executar `pytest tests/test_fluxo.py -k test_rn01_estadia_minima`. |
| **RN-02** | Negócio | Hóspedes $\le$ capacidade máxima | `models.py`, `app.py: tela_resumo` | Executar `pytest tests/test_fluxo.py -k test_rn02_capacidade_maxima`. |
| **RN-03** | Negócio | Taxa de serviço de 14% sobre as diárias | `models.py: calcular_valores()` | Conferir discriminação detalhada na Tela 1. |
| **RN-04** | Negócio | Cancelamento automático após 30 min sem pagamento | `models.py: verificar_expiracao_reserva()` | Tentar pagar reserva após alterar `criadoEm` para 31 min atrás no SQLite. |
| **RN-07 / RF-33** | Negócio / Funcional | Desconto de 10% sobre a taxa de serviço para anfitrião Superhost | `models.py: calcular_valores()` | Executar `pytest tests/test_fluxo.py -k test_rf18_rn07_desconto_superhost`. |
| **RNF-02** | Não Funcional | Confirmação de cartão exibida rapidamente (<10s) | `app.py: pagar_cartao()` | Processamento imediato em rota síncrona. |
| **RNF-05** | Não Funcional / Segurança | Endereço exato ocultado antes da confirmação | `templates/resumo.html`, `templates/confirmacao.html` | Verificar que na Tela 1 a rota só envia bairro; na Tela 3 envia rua/número. |
| **RNF-08** | Não Funcional / Segurança | Não armazenar número completo e CVV do cartão | `database.py: pagamento` | Inspecionar esquema da tabela: apenas `txid` e `codigoAutorizacao` são persistidos. |
| **RNF-22** | Não Funcional | Auditoria de mudanças de status com data, hora e autor | `database.py: auditoria`, `models.py: registrar_auditoria()` | Checar registros gerados na tabela `auditoria` a cada alteração de status. |

### Requisitos Fora do Escopo Implementado e Justificativa
- **RF-01 a RF-06 (Cadastro e Gestão de Usuários):** Não pertencem ao fluxo de contratação; supridos via autenticação mockada em sessão.
- **RF-07 a RF-11 (Cadastro e Gestão de Imóveis):** Supridos via script de inicialização (`seed_db`).
- **RF-12 a RF-16 (Busca com Filtros Avançados e Ordenação):** Simplificados para uma listagem direta que dispara o fluxo de 3 telas.
- **RF-21, RF-27 e RN-05 (Cancelamento e Reembolso pelo Usuário):** Conforme seção "Simplificações permitidas" do enunciado, operações pós-contratação não fazem parte deste fluxo.
- **RF-29 a RF-32 e RN-06 (Avaliações mútuas):** Ocorrem apenas após a conclusão física da viagem (`CONCLUIDA`), fora da contratação imediata.
- **RF-34 a RF-36 e RNF-06 (Denúncias e Moderação):** Funcionalidade administrativa independente.

---

## 3. Registro de Ambiguidades e Decisões de Projeto

### Decisão 1: Qualificação e Aplicação do Selo Superhost (RN-07 e RF-33)
- **Trecho da ERS:** *"O anfitrião recebe o selo superhost quando, nos últimos 12 meses, tem nota média de pelo menos 4,8, taxa de resposta de pelo menos 90% e ao menos 10 reservas concluídas. Como benefício, as reservas das acomodações de um superhost têm desconto de 10% na taxa de serviço."*
- **Ambiguidade:** A ERS não define se a verificação dos 3 parâmetros (taxa de resposta, média, histórico anual) deve ser recalculada em tempo de execução a cada reserva ou se decorre de uma flag consolidada na acomodação/anfitrião.
- **Decisão Adotada:** Criou-se a coluna booleana `ehSuperhost` na acomodação/anfitrião (populada no banco com base nas métricas consolidadas). No cálculo da reserva, se `ehSuperhost == 1`, aplica-se o desconto: $\text{desconto} = \text{taxaServico} \times 0.10$.
- **Alternativa Descartada:** Tentar montar um subsistema completo de mensageria para inferir taxa de resposta em tempo real, o que extrapola o escopo de 3 telas.

### Decisão 2: Ocultação do Endereço Físico (RNF-05)
- **Trecho da ERS:** *"O endereço exato da acomodação só deve ser exibido ao hóspede após a reserva ser CONFIRMADA; antes disso, mostra-se apenas o bairro."*
- **Ambiguidade:** A especificação não deixa explícito se a proteção deve ser estritamente no back-end (projeção no SQL) ou via camada de apresentação front-end.
- **Decisão Adotada:** A rota de resumo (`/reservas/resumo`) sequer envia os dados `rua` e `cep` no template. A rota de confirmação (`/reservas/<id>/confirmacao`) valida se `status == 'CONFIRMADA'` antes de projetar `rua`, `numero` e `cep`.
- **Alternativa Descartada:** Enviar os dados completos no HTML da Tela 1 ocultando-os via CSS/JavaScript, o que violaria o princípio de segurança e o RNF-05.

### Decisão 3: Cancelamento de Reserva Pendente por Timeout (RN-04)
- **Trecho da ERS:** *"Uma reserva PENDENTE é cancelada automaticamente se o pagamento não for aprovado em 30 minutos."*
- **Ambiguidade:** Como garantir o cancelamento em uma arquitetura Flask + SQLite básica sem introduzir daemons externos complexos (ex.: Celery, Redis ou cron)?
- **Decisão Adotada:** Implementada checagem preguiçosa ativa (`verificar_expiracao_reserva`): qualquer requisição referente à reserva (consulta de tela, tentativa de pagamento ou chamada de webhook) calcula o delta entre `criadoEm` e o horário atual. Se exceder 1800 segundos (30 minutos), a reserva é transacionada para `CANCELADA` e auditada.
- **Alternativa Descartada:** Adicionar dependências pesadas de fila e cache ao projeto do aluno.

### Decisão 4: Modelo de Aprovação de Reserva (TBD-03)
- **Trecho da ERS (Apêndice C):** *"TBD-03: Se o anfitrião poderá aprovar manualmente cada reserva ou se toda reserva paga será confirmada automaticamente."*
- **Ambiguidade:** O item estava listado em aberto na ERS.
- **Decisão Adotada:** Adotou-se o modelo de "Reserva Instantânea". A aprovação do pagamento pelo gateway (seja cartão síncrono ou PIX assíncrono via webhook) transiciona a reserva para `CONFIRMADA` sem travar o usuário.
- **Alternativa Descartada:** Interromper o fluxo na Tela 2 exigindo login de outro ator para liberação manual.

---

## 4. Código-Fonte dos Módulos

### `requirements.txt`
```text
Flask==3.0.0
pytest==7.4.3
```

---

### `database.py`
```python
import sqlite3

DATABASE_NAME = "hospedagem.db"

def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # B.4 Projeto de tabelas da ERS v1.1
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS usuario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senhaHash TEXT NOT NULL,
        telefone TEXT,
        dataCadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
        ehAnfitriao BOOLEAN DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS acomodacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anfitriao_id INTEGER NOT NULL,
        titulo TEXT NOT NULL,
        descricao TEXT,
        precoNoite REAL NOT NULL,
        capacidadeMaxima INTEGER NOT NULL,
        quartos INTEGER NOT NULL,
        banheiros INTEGER NOT NULL,
        camas INTEGER NOT NULL,
        regras TEXT,
        cep TEXT NOT NULL,
        rua TEXT NOT NULL,
        bairro TEXT NOT NULL,
        cidade TEXT NOT NULL,
        estado TEXT NOT NULL,
        ativo BOOLEAN DEFAULT 1,
        ehSuperhost BOOLEAN DEFAULT 0,
        FOREIGN KEY (anfitriao_id) REFERENCES usuario (id)
    );

    CREATE TABLE IF NOT EXISTS reserva (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hospede_id INTEGER NOT NULL,
        acomodacao_id INTEGER NOT NULL,
        checkin TEXT NOT NULL,
        checkOut TEXT NOT NULL,
        numHospedes INTEGER NOT NULL,
        subtotalDiarias REAL NOT NULL,
        taxaServico REAL NOT NULL,
        descontoSuperhost REAL DEFAULT 0.0,
        valorTotal REAL NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('PENDENTE', 'CONFIRMADA', 'CANCELADA', 'CONCLUIDA')),
        criadoEm DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (hospede_id) REFERENCES usuario (id),
        FOREIGN KEY (acomodacao_id) REFERENCES acomodacao (id)
    );

    CREATE TABLE IF NOT EXISTS pagamento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reserva_id INTEGER NOT NULL,
        txid TEXT UNIQUE NOT NULL,
        metodo TEXT NOT NULL CHECK(metodo IN ('CARTAO', 'PIX')),
        valor REAL NOT NULL,
        codigoAutorizacao TEXT,
        status TEXT NOT NULL CHECK(status IN ('PROCESSANDO', 'APROVADO', 'RECUSADO', 'REEMBOLSADO')),
        dataHora DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (reserva_id) REFERENCES reserva (id)
    );

    CREATE TABLE IF NOT EXISTS avaliacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reserva_id INTEGER NOT NULL,
        autor_id INTEGER NOT NULL,
        nota INTEGER NOT NULL,
        comentario TEXT,
        dataAvaliacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (reserva_id) REFERENCES reserva (id),
        FOREIGN KEY (autor_id) REFERENCES usuario (id)
    );

    -- Tabela criada para satisfazer RNF-22 (Auditoria)
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entidade TEXT NOT NULL,
        entidade_id INTEGER NOT NULL,
        status_anterior TEXT,
        status_novo TEXT,
        responsavel TEXT,
        dataHora DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    seed_db(conn)
    conn.close()

def seed_db(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuario")
    if cursor.fetchone()[0] > 0:
        return

    # Seed de usuários de teste
    cursor.execute("""
    INSERT INTO usuario (id, nome, email, senhaHash, telefone, ehAnfitriao) VALUES 
    (1, 'Hóspede Teste', 'hospede@teste.com', '$2b$12$dummyhashforguest', '21999990001', 0),
    (2, 'Anfitrião Padrão', 'host.normal@teste.com', '$2b$12$dummyhashforhost1', '21999990002', 1),
    (3, 'Anfitriã Superhost', 'host.super@teste.com', '$2b$12$dummyhashforhost2', '21999990003', 1)
    """)

    # Seed de acomodações (uma regular e uma com benefício Superhost)
    cursor.execute("""
    INSERT INTO acomodacao (id, anfitriao_id, titulo, descricao, precoNoite, capacidadeMaxima, quartos, banheiros, camas, regras, cep, rua, bairro, cidade, estado, ativo, ehSuperhost) VALUES 
    (1, 2, 'Apartamento Vista Mar', 'Excelente apartamento mobiliado na orla', 200.0, 4, 2, 1, 2, 'Proibido fumar, sem animais', '22041-001', 'Av. Atlântica, 1500, Apt 801', 'Copacabana', 'Rio de Janeiro', 'RJ', 1, 0),
    (2, 3, 'Studio Luxo Superhost', 'Studio moderno com benefícios exclusivos Superhost', 300.0, 2, 1, 1, 1, 'Proibido festas e eventos', '22410-002', 'Rua Visconde de Pirajá, 300, Apt 302', 'Ipanema', 'Rio de Janeiro', 'RJ', 1, 1)
    """)
    conn.commit()
```

---

### `models.py`
```python
from datetime import datetime
from database import get_db

def registrar_auditoria(conn, entidade, entidade_id, status_anterior, status_novo, responsavel="SISTEMA"):
    """Atende a RNF-22: auditoria de status com data, hora e responsável"""
    conn.execute("""
        INSERT INTO auditoria (entidade, entidade_id, status_anterior, status_novo, responsavel)
        VALUES (?, ?, ?, ?, ?)
    """, (entidade, entidade_id, status_anterior, status_novo, responsavel))

def verificar_expiracao_reserva(reserva_id):
    """Atende a RN-04: cancelamento automático de reserva pendente após 30 min"""
    conn = get_db()
    reserva = conn.execute("SELECT * FROM reserva WHERE id = ?", (reserva_id,)).fetchone()
    if reserva and reserva['status'] == 'PENDENTE':
        criado = datetime.strptime(reserva['criadoEm'], "%Y-%m-%d %H:%M:%S")
        if (datetime.utcnow() - criado).total_seconds() > 1800:
            conn.execute("UPDATE reserva SET status = 'CANCELADA' WHERE id = ?", (reserva_id,))
            registrar_auditoria(conn, 'reserva', reserva_id, 'PENDENTE', 'CANCELADA', 'SISTEMA_TIMEOUT_RN04')
            conn.commit()
    conn.close()

def calcular_valores(preco_noite, noites, eh_superhost):
    """
    Atende a:
    - RN-03: taxa de serviço de 14% sobre as diárias
    - RN-07 / RF-18 / RF-33: desconto de 10% na taxa de serviço se for Superhost
    """
    subtotal = preco_noite * noites
    taxa_servico = subtotal * 0.14
    desconto_superhost = (taxa_servico * 0.10) if eh_superhost else 0.0
    valor_total = subtotal + taxa_servico - desconto_superhost
    return {
        "subtotal": round(subtotal, 2),
        "taxa_servico": round(taxa_servico, 2),
        "desconto_superhost": round(desconto_superhost, 2),
        "valor_total": round(valor_total, 2)
    }

def validar_disponibilidade(conn, acomodacao_id, checkin, checkout):
    """Atende a RF-19: impede sobreposição de reservas ativas para a mesma acomodação"""
    query = """
    SELECT COUNT(*) FROM reserva
    WHERE acomodacao_id = ?
      AND status IN ('PENDENTE', 'CONFIRMADA')
      AND NOT (checkOut <= ? OR checkin >= ?)
    """
    count = conn.execute(query, (acomodacao_id, checkin, checkout)).fetchone()[0]
    return count == 0
```

---

### `services/payment_gateway.py`
```python
import uuid

class PaymentGatewaySimulado:
    """
    Simulação de Gateway de Pagamento Externo (Seção 3.3 e 4.5 da ERS).
    Suporta autorização síncrona (Cartão) e emissão assíncrona (PIX).
    """
    
    @staticmethod
    def processar_cartao(numero_cartao, valor):
        # Regra de teste: cartões com final '0000' simulam recusa (RF-26)
        if str(numero_cartao).strip().endswith("0000"):
            return {
                "sucesso": False,
                "codigoAutorizacao": None,
                "txid": f"TX-CARD-{uuid.uuid4().hex[:8].upper()}",
                "status": "RECUSADO"
            }
        return {
            "sucesso": True,
            "codigoAutorizacao": f"AUTH-{uuid.uuid4().hex[:8].upper()}",
            "txid": f"TX-CARD-{uuid.uuid4().hex[:8].upper()}",
            "status": "APROVADO"
        }

    @staticmethod
    def gerar_cobranca_pix(reserva_id, valor):
        # RF-23: identificador único vinculado à reserva
        txid = f"PIX-RES-{reserva_id}-{uuid.uuid4().hex[:6].upper()}"
        copia_cola = (
            f"00020126580014BR.GOV.BCB.PIX0136{txid}"
            f"520400005303986540{valor:.2f}5802BR5920AIRBNB_ERS_PLATAFORM"
            f"6009RIO_DE_JANEIRO62070503***6304"
        )
        return {
            "txid": txid,
            "qr_code_simulado": f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={copia_cola}",
            "copia_cola": copia_cola
        }
```

---

### `services/email_service.py`
```python
class EmailServiceSimulado:
    """Simulador do Serviço de E-mail para atender a RF-28"""
    mensagens_enviadas = []

    @classmethod
    def enviar_confirmacao_reserva(cls, destinatario, reserva_id, valor, auth_code):
        mensagem = {
            "para": destinatario,
            "assunto": f"Confirmação da Reserva #{reserva_id}",
            "corpo": f"Reserva #{reserva_id} confirmada com sucesso! Valor pago: R$ {valor:.2f}. Aut: {auth_code}."
        }
        cls.mensagens_enviadas.append(mensagem)
        return True
```

---

### `app.py`
```python
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime
from database import init_db, get_db
from models import (
    calcular_valores, validar_disponibilidade, 
    verificar_expiracao_reserva, registrar_auditoria
)
from services.payment_gateway import PaymentGatewaySimulado
from services.email_service import EmailServiceSimulado

app = Flask(__name__)
app.secret_key = "segredo_plataforma_ers_airbnb"

@app.before_request
def simular_autenticacao():
    # Garante hóspede de teste logado em conformidade com o escopo
    if 'usuario_id' not in session:
        session['usuario_id'] = 1
        session['usuario_nome'] = "Hóspede Teste"
        session['usuario_email'] = "hospede@teste.com"

@app.route('/')
def index():
    """Catálogo inicial simples para disparar a escolha de estadia"""
    conn = get_db()
    acomodacoes = conn.execute("SELECT * FROM acomodacao WHERE ativo = 1").fetchall()
    conn.close()
    return render_template("index.html", acomodacoes=acomodacoes)

# TELA 1: Resumo da Estadia (Seção 3.1)
@app.route('/reservas/resumo')
def tela_resumo():
    if not session.get('usuario_id'):
        return "Usuário não autenticado", 401
    
    acomodacao_id = request.args.get('acomodacao_id', type=int)
    checkin = request.args.get('checkin')
    checkout = request.args.get('checkout')
    hospedes = request.args.get('hospedes', default=1, type=int)

    conn = get_db()
    # RNF-05: Seleciona apenas bairro/cidade; rua e CEP não são enviados nesta rota
    acomodacao = conn.execute("""
        SELECT id, anfitriao_id, titulo, descricao, precoNoite, capacidadeMaxima, 
               bairro, cidade, estado, ehSuperhost 
        FROM acomodacao WHERE id = ?
    """, (acomodacao_id,)).fetchone()
    
    if not acomodacao:
        conn.close()
        return "Acomodação não encontrada", 404

    # RN-01: Check-out posterior ao check-in com no mínimo 1 noite
    try:
        d_in = datetime.strptime(checkin, "%Y-%m-%d")
        d_out = datetime.strptime(checkout, "%Y-%m-%d")
        noites = (d_out - d_in).days
        if noites < 1:
            conn.close()
            return "O check-out deve ser posterior ao check-in com estadia mínima de 1 noite (RN-01)", 400
    except (ValueError, TypeError):
        conn.close()
        return "Datas informadas em formato inválido", 400

    # RN-02: Capacidade máxima
    if hospedes > acomodacao['capacidadeMaxima']:
        conn.close()
        return f"Capacidade máxima excedida. Máximo permitido: {acomodacao['capacidadeMaxima']} hóspedes (RN-02)", 400

    # RF-19: Disponibilidade
    if not validar_disponibilidade(conn, acomodacao_id, checkin, checkout):
        conn.close()
        return "Acomodação já reservada para o período informado (RF-19).", 409

    valores = calcular_valores(acomodacao['precoNoite'], noites, acomodacao['ehSuperhost'])
    conn.close()

    return render_template(
        "resumo.html",
        acomodacao=acomodacao,
        checkin=checkin,
        checkout=checkout,
        noites=noites,
        hospedes=hospedes,
        valores=valores
    )

# Criação da reserva pendente (UC03 / RF-17 / RF-20)
@app.route('/api/reservas', methods=['POST'])
def criar_reserva():
    if not session.get('usuario_id'):
        return jsonify({"erro": "Não autenticado"}), 401
    
    data = request.get_json() or {}
    acomodacao_id = data.get('acomodacao_id')
    checkin = data.get('checkin')
    checkout = data.get('checkout')
    num_hospedes = data.get('num_hospedes')

    conn = get_db()
    acomodacao = conn.execute("SELECT * FROM acomodacao WHERE id = ?", (acomodacao_id,)).fetchone()
    if not acomodacao:
        conn.close()
        return jsonify({"erro": "Acomodação não encontrada"}), 404

    d_in = datetime.strptime(checkin, "%Y-%m-%d")
    d_out = datetime.strptime(checkout, "%Y-%m-%d")
    noites = (d_out - d_in).days
    if noites < 1:
        conn.close()
        return jsonify({"erro": "Estadia mínima de 1 noite (RN-01)"}), 400

    if num_hospedes > acomodacao['capacidadeMaxima']:
        conn.close()
        return jsonify({"erro": "Capacidade máxima excedida (RN-02)"}), 400

    if not validar_disponibilidade(conn, acomodacao_id, checkin, checkout):
        conn.close()
        return jsonify({"erro": "Acomodação indisponível neste período (RF-19)"}), 409

    valores = calcular_valores(acomodacao['precoNoite'], noites, acomodacao['ehSuperhost'])
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reserva (
            hospede_id, acomodacao_id, checkin, checkOut, numHospedes,
            subtotalDiarias, taxaServico, descontoSuperhost, valorTotal, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE')
    """, (
        session['usuario_id'], acomodacao_id, checkin, checkout, num_hospedes,
        valores['subtotal'], valores['taxaServico'], valores['descontoSuperhost'], valores['valorTotal']
    ))
    reserva_id = cursor.lastrowid
    registrar_auditoria(conn, 'reserva', reserva_id, None, 'PENDENTE', session['usuario_nome'])
    conn.commit()
    conn.close()

    return jsonify({"reserva_id": reserva_id, "redirect_url": url_for('tela_pagamento', id=reserva_id)})

# TELA 2: Pagamento (Seção 3.1)
@app.route('/reservas/<int:id>/pagamento')
def tela_pagamento(id):
    verificar_expiracao_reserva(id)
    conn = get_db()
    reserva = conn.execute("""
        SELECT r.*, a.titulo, a.bairro, a.cidade 
        FROM reserva r 
        JOIN acomodacao a ON r.acomodacao_id = a.id 
        WHERE r.id = ?
    """, (id,)).fetchone()
    conn.close()

    if not reserva:
        return "Reserva não encontrada", 404
    if reserva['status'] == 'CONFIRMADA':
        return redirect(url_for('tela_confirmacao', id=id))
    if reserva['status'] == 'CANCELADA':
        return "Esta reserva foi cancelada ou expirou o tempo limite de 30 minutos (RN-04).", 410

    return render_template("pagamento.html", reserva=reserva)

# Pagamento com Cartão (Síncrono - RF-23 / RF-25 / RF-26)
@app.route('/api/reservas/<int:id>/pagar-cartao', methods=['POST'])
def pagar_cartao(id):
    verificar_expiracao_reserva(id)
    conn = get_db()
    reserva = conn.execute("SELECT * FROM reserva WHERE id = ?", (id,)).fetchone()
    
    if not reserva or reserva['status'] != 'PENDENTE':
        conn.close()
        return jsonify({"erro": "Reserva indisponível ou já expirada"}), 400

    data = request.get_json() or {}
    numero_cartao = data.get('numero_cartao', '')
    
    # RNF-08: Número e CVV não são persistidos
    resp = PaymentGatewaySimulado.processar_cartao(numero_cartao, reserva['valorTotal'])
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pagamento (reserva_id, txid, metodo, valor, codigoAutorizacao, status)
        VALUES (?, ?, 'CARTAO', ?, ?, ?)
    """, (id, resp['txid'], reserva['valorTotal'], resp['codigoAutorizacao'], resp['status']))
    
    if resp['sucesso']:
        cursor.execute("UPDATE reserva SET status = 'CONFIRMADA' WHERE id = ?", (id,))
        registrar_auditoria(conn, 'reserva', id, 'PENDENTE', 'CONFIRMADA', session['usuario_nome'])
        conn.commit()
        # RF-28: Comprovante por e-mail
        EmailServiceSimulado.enviar_confirmacao_reserva(
            session['usuario_email'], id, reserva['valorTotal'], resp['codigoAutorizacao']
        )
        conn.close()
        return jsonify({"status": "APROVADO", "redirect_url": url_for('tela_confirmacao', id=id)})
    else:
        conn.commit()
        conn.close()
        # RF-26: Permite nova tentativa em caso de recusa
        return jsonify({"status": "RECUSADO", "mensagem": "Cartão recusado pela operadora. Tente novamente."}), 422

# Geração de cobrança PIX (RF-23 / RF-24)
@app.route('/api/reservas/<int:id>/gerar-pix', methods=['POST'])
def gerar_pix(id):
    verificar_expiracao_reserva(id)
    conn = get_db()
    reserva = conn.execute("SELECT * FROM reserva WHERE id = ?", (id,)).fetchone()
    if not reserva or reserva['status'] != 'PENDENTE':
        conn.close()
        return jsonify({"erro": "Reserva inválida ou expirada"}), 400

    pix_data = PaymentGatewaySimulado.gerar_cobranca_pix(id, reserva['valorTotal'])
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pagamento (reserva_id, txid, metodo, valor, status)
        VALUES (?, ?, 'PIX', ?, 'PROCESSANDO')
    """, (id, pix_data['txid'], reserva['valorTotal']))
    conn.commit()
    conn.close()

    return jsonify(pix_data)

# Polling de verificação de status
@app.route('/api/reservas/<int:id>/status')
def status_reserva(id):
    verificar_expiracao_reserva(id)
    conn = get_db()
    reserva = conn.execute("SELECT status FROM reserva WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not reserva:
        return jsonify({"erro": "Reserva não encontrada"}), 404
    return jsonify({"status": reserva['status']})

# Webhook assíncrono do Gateway (Seção 3.4 / RF-23)
@app.route('/api/webhook/pix', methods=['POST'])
def webhook_pix():
    data = request.get_json() or {}
    txid = data.get('txid')
    valor_pago = float(data.get('valor', 0.0))

    conn = get_db()
    pagamento = conn.execute("SELECT * FROM pagamento WHERE txid = ?", (txid,)).fetchone()
    if not pagamento:
        conn.close()
        return jsonify({"erro": "Cobrança não localizada"}), 404

    reserva_id = pagamento['reserva_id']
    verificar_expiracao_reserva(reserva_id)
    reserva = conn.execute("SELECT * FROM reserva WHERE id = ?", (reserva_id,)).fetchone()

    if reserva['status'] == 'CANCELADA':
        conn.close()
        return jsonify({"erro": "A reserva associada já expirou (RN-04)"}), 400

    if valor_pago < pagamento['valor']:
        conn.close()
        return jsonify({"erro": "Valor pago insuficiente"}), 400

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE pagamento 
        SET status = 'APROVADO', codigoAutorizacao = ? 
        WHERE id = ?
    """, (f"PIX-AUTH-{txid[-6:]}", pagamento['id']))

    cursor.execute("UPDATE reserva SET status = 'CONFIRMADA' WHERE id = ?", (reserva_id,))
    registrar_auditoria(conn, 'reserva', reserva_id, 'PENDENTE', 'CONFIRMADA', 'WEBHOOK_PIX')
    conn.commit()

    EmailServiceSimulado.enviar_confirmacao_reserva(
        "hospede@teste.com", reserva_id, valor_pago, f"PIX-AUTH-{txid[-6:]}"
    )
    conn.close()
    return jsonify({"mensagem": "Pagamento PIX liquidado com sucesso"})

# TELA 3: Confirmação (Seção 3.1 / RNF-05)
@app.route('/reservas/<int:id>/confirmacao')
def tela_confirmacao(id):
    conn = get_db()
    # RNF-05: O endereço completo (rua, cep) é exposto unicamente após status CONFIRMADA
    reserva = conn.execute("""
        SELECT r.*, a.titulo, a.rua, a.bairro, a.cidade, a.estado, a.cep 
        FROM reserva r 
        JOIN acomodacao a ON r.acomodacao_id = a.id 
        WHERE r.id = ?
    """, (id,)).fetchone()
    
    pagamento = conn.execute("""
        SELECT * FROM pagamento 
        WHERE reserva_id = ? AND status = 'APROVADO' 
        ORDER BY id DESC LIMIT 1
    """, (id,)).fetchone()
    conn.close()

    if not reserva or reserva['status'] != 'CONFIRMADA':
        return redirect(url_for('tela_pagamento', id=id))

    return render_template("confirmacao.html", reserva=reserva, pagamento=pagamento)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
```

---

### `templates/base.html`
```html
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plataforma de Hospedagem - ERS v1.1</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <header class="navbar">
        <a href="/" class="logo">🏨 HospedaApp</a>
        <div class="user-badge">👤 Logado como: {{ session.get('usuario_nome') }}</div>
    </header>
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    <footer class="footer">
        <!-- Requisito 3.1: Botão de ajuda presente em todas as telas -->
        <button onclick="alert('Canal de Suporte: suporte@hospedaapp.com.br | Tel: 0800 123 4567')" class="btn-help">Ajuda</button>
    </footer>
    <script src="{{ url_for('static', filename='app.js') }}"></script>
</body>
</html>
```

---

### `templates/index.html`
```html
{% extends "base.html" %}
{% block content %}
<h2>Acomodações para Teste de Fluxo</h2>
<div class="card-grid">
    {% for a in acomodacoes %}
    <div class="card">
        <h3>{{ a.titulo }}</h3>
        <p>{{ a.descricao }}</p>
        <p>📍 <strong>Localização:</strong> {{ a.bairro }}, {{ a.cidade }}</p>
        <p>💰 <strong>Diária:</strong> R$ {{ "%.2f"|format(a.precoNoite) }}</p>
        {% if a.ehSuperhost %}
            <span class="badge-superhost">⭐ Anfitrião Superhost (10% OFF na taxa)</span>
        {% endif %}
        <form action="/reservas/resumo" method="GET" class="mt-2">
            <input type="hidden" name="acomodacao_id" value="{{ a.id }}">
            <label>Check-in:</label>
            <input type="date" name="checkin" value="2026-12-01" required>
            <label>Check-out:</label>
            <input type="date" name="checkout" value="2026-12-05" required>
            <label>Hóspedes:</label>
            <input type="number" name="hospedes" value="2" min="1" max="{{ a.capacidadeMaxima }}" required>
            <button type="submit" class="btn-primary mt-2">Iniciar Reserva</button>
        </form>
    </div>
    {% endfor %}
</div>
{% endblock %}
```

---

### `templates/resumo.html` (Tela 1)
```html
{% extends "base.html" %}
{% block content %}
<div class="box-flow">
    <h2>1. Resumo da Estadia</h2>
    <div class="details">
        <h3>{{ acomodacao.titulo }}</h3>
        <!-- RNF-05: Exibição restrita a bairro e cidade -->
        <p>📍 <strong>Região:</strong> {{ acomodacao.bairro }}, {{ acomodacao.cidade }} - {{ acomodacao.estado }}</p>
        <p>📅 <strong>Período:</strong> {{ checkin }} até {{ checkout }} ({{ noites }} noite{% if noites > 1 %}s{% endif %})</p>
        <p>👥 <strong>Hóspedes:</strong> {{ hospedes }} (Limite: {{ acomodacao.capacidadeMaxima }})</p>
    </div>

    <hr>
    <h3>Detalhamento do Preço</h3>
    <table class="table-calc">
        <tr>
            <td>{{ noites }} noites x R$ {{ "%.2f"|format(acomodacao.precoNoite) }}</td>
            <td class="text-right">R$ {{ "%.2f"|format(valores.subtotal) }}</td>
        </tr>
        <tr>
            <td>Taxa de serviço (14% - RN-03)</td>
            <td class="text-right">R$ {{ "%.2f"|format(valores.taxa_servico) }}</td>
        </tr>
        {% if valores.desconto_superhost > 0 %}
        <tr class="superhost-row">
            <td>⭐ Desconto Superhost (10% sobre taxa - RN-07)</td>
            <td class="text-right">- R$ {{ "%.2f"|format(valores.desconto_superhost) }}</td>
        </tr>
        {% endif %}
        <tr class="total-row">
            <td><strong>Valor Total</strong></td>
            <td class="text-right"><strong>R$ {{ "%.2f"|format(valores.valor_total) }}</strong></td>
        </tr>
    </table>

    <button id="btn-confirmar-resumo" class="btn-primary" onclick="criarReserva({{ acomodacao.id }}, '{{ checkin }}', '{{ checkout }}', {{ hospedes }})">
        Confirmar e Ir para Pagamento
    </button>
</div>
{% endblock %}
```

---

### `templates/pagamento.html` (Tela 2)
```html
{% extends "base.html" %}
{% block content %}
<div class="box-flow">
    <h2>2. Pagamento da Reserva #{{ reserva.id }}</h2>
    <p>Total a pagar: <strong class="price-highlight">R$ {{ "%.2f"|format(reserva.valorTotal) }}</strong></p>
    
    <!-- RN-04: Aviso e contagem de expiração -->
    <div class="timer-box">⏳ Esta reserva expira em 30 minutos caso não seja aprovada (RN-04).</div>

    <div class="tabs">
        <button class="tab-btn active" onclick="alternarMetodo('cartao')">Cartão de Crédito</button>
        <button class="tab-btn" onclick="alternarMetodo('pix')">PIX</button>
    </div>

    <!-- Pagamento via Cartão de Crédito (Síncrono) -->
    <div id="secao-cartao" class="payment-method">
        <form id="form-cartao" onsubmit="pagarCartao(event, {{ reserva.id }})">
            <label>Número do Cartão:</label>
            <input type="text" id="cartao_num" placeholder="Dica: termine em 0000 para simular recusa" required>
            <label>Titular do Cartão:</label>
            <input type="text" required>
            <div class="form-row">
                <div>
                    <label>Validade:</label>
                    <input type="text" placeholder="MM/AA" required>
                </div>
                <div>
                    <label>CVV:</label>
                    <input type="text" placeholder="123" required>
                </div>
            </div>
            <button type="submit" id="btn-pagar-cartao" class="btn-primary mt-2">Pagar com Cartão</button>
        </form>
        <div id="msg-erro-cartao" class="error-box" style="display:none;"></div>
    </div>

    <!-- Pagamento via PIX (Assíncrono) -->
    <div id="secao-pix" class="payment-method" style="display: none;">
        <p>Gere um QR Code exclusivo para esta reserva:</p>
        <button class="btn-secondary" onclick="gerarPix({{ reserva.id }})">Gerar Código PIX</button>
        
        <div id="pix-detalhes" style="display: none;" class="mt-2 text-center">
            <img id="pix-qrcode" src="" alt="QR Code PIX">
            <p><strong>Código Copia e Cola:</strong></p>
            <textarea id="pix-copiacola" readonly></textarea>
            <p><small>Aguardando confirmação do pagamento assíncrono via webhook...</small></p>

            <div class="webhook-simulador">
                <small>⚙️ Ferramenta de Simulação do Gateway Bancário:</small><br>
                <button class="btn-small" onclick="simularWebhookPix({{ reserva.valorTotal }})">Disparar Webhook de Liquidação</button>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### `templates/confirmacao.html` (Tela 3)
```html
{% extends "base.html" %}
{% block content %}
<div class="box-flow text-center">
    <div class="success-icon">✅</div>
    <h2>3. Reserva Confirmada!</h2>
    <p>Seu pagamento foi aprovado e a acomodação está garantida.</p>

    <div class="details text-left">
        <p><strong>Identificador da Reserva:</strong> #{{ reserva.id }}</p>
        <p><strong>Código de Autorização:</strong> {{ pagamento.codigoAutorizacao }}</p>
        <p><strong>Forma de Pagamento:</strong> {{ pagamento.metodo }}</p>
        <p><strong>Valor Total Pago:</strong> R$ {{ "%.2f"|format(pagamento.valor) }}</p>
        <p><strong>Período da Estadia:</strong> {{ reserva.checkin }} até {{ reserva.checkOut }}</p>
        <hr>
        <!-- RNF-05: Endereço completo revelado apenas aqui -->
        <div class="address-box">
            <h4>📍 Endereço Completo do Imóvel</h4>
            <p>{{ reserva.rua }}</p>
            <p>{{ reserva.bairro }}, {{ reserva.cidade }} - {{ reserva.estado }}</p>
            <p>CEP: {{ reserva.cep }}</p>
        </div>
        <p class="mt-2"><small>📧 Um e-mail com o comprovante fiscal e os dados da hospedagem foi enviado (RF-28).</small></p>
    </div>
    <a href="/" class="btn-primary mt-2">Voltar à Página Principal</a>
</div>
{% endblock %}
```

---

### `static/style.css`
```css
* {
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
body {
    margin: 0;
    background: #f7f7f7;
    color: #222;
}
.navbar {
    background: #fff;
    padding: 16px 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e0e0e0;
}
.logo {
    font-weight: bold;
    text-decoration: none;
    color: #ff385c;
    font-size: 1.3rem;
}
.user-badge {
    font-size: 0.9rem;
    color: #555;
}
.container {
    max-width: 850px;
    margin: 32px auto;
    padding: 0 16px;
}
.box-flow {
    background: #fff;
    padding: 32px;
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
}
.card {
    background: #fff;
    padding: 20px;
    border-radius: 8px;
    border: 1px solid #e4e4e4;
}
.badge-superhost {
    display: inline-block;
    background: #ffebe5;
    color: #c13515;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
    margin-top: 6px;
}
.btn-primary {
    background: #ff385c;
    color: #fff;
    border: none;
    padding: 12px 20px;
    border-radius: 8px;
    cursor: pointer;
    width: 100%;
    font-size: 1rem;
    font-weight: 600;
}
.btn-primary:hover {
    background: #e00b41;
}
.btn-secondary {
    background: #222;
    color: #fff;
    border: none;
    padding: 10px 16px;
    border-radius: 8px;
    cursor: pointer;
}
.btn-small {
    padding: 6px 12px;
    background: #0066cc;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}
.table-calc {
    width: 100%;
    margin: 16px 0;
    border-collapse: collapse;
}
.table-calc td {
    padding: 10px 0;
}
.text-right {
    text-align: right;
}
.text-left {
    text-align: left;
}
.text-center {
    text-align: center;
}
.total-row {
    border-top: 1px solid #ddd;
    font-size: 1.15rem;
}
.superhost-row {
    color: #008a05;
}
.price-highlight {
    font-size: 1.3rem;
    color: #ff385c;
}
.timer-box {
    background: #fff3cd;
    color: #856404;
    padding: 12px;
    border-radius: 6px;
    text-align: center;
    margin-bottom: 20px;
    font-size: 0.95rem;
}
.tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
}
.tab-btn {
    flex: 1;
    padding: 12px;
    border: 1px solid #ccc;
    background: #f0f0f0;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
}
.tab-btn.active {
    background: #fff;
    border-color: #ff385c;
    color: #ff385c;
}
.form-row {
    display: flex;
    gap: 15px;
}
.form-row > div {
    flex: 1;
}
input[type="text"], input[type="date"], input[type="number"], textarea {
    width: 100%;
    padding: 10px;
    margin: 6px 0 14px 0;
    border: 1px solid #ccc;
    border-radius: 6px;
}
.webhook-simulador {
    margin-top: 24px;
    padding: 16px;
    background: #eef4ff;
    border-radius: 8px;
    border: 1px dashed #0066cc;
}
.address-box {
    background: #eafaf1;
    border: 1px solid #a3e4d7;
    padding: 16px;
    border-radius: 8px;
    margin-top: 16px;
}
.error-box {
    background: #fde8e8;
    color: #9b1c1c;
    padding: 12px;
    border-radius: 6px;
    margin-top: 12px;
}
.success-icon {
    font-size: 3rem;
    margin-bottom: 8px;
}
.footer {
    text-align: center;
    margin: 32px 0;
}
.btn-help {
    background: #fff;
    border: 1px solid #bbb;
    border-radius: 20px;
    padding: 6px 18px;
    cursor: pointer;
}
.mt-2 {
    margin-top: 12px;
}
```

---

### `static/app.js`
```javascript
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
```

---

### `tests/test_fluxo.py`
```python
import pytest
from app import app
from database import init_db, get_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    init_db()
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['usuario_id'] = 1
            sess['usuario_nome'] = "Hóspede Teste"
            sess['usuario_email'] = "hospede@teste.com"
        yield client

def test_rn01_estadia_minima(client):
    """RN-01: Check-out deve ser posterior ao check-in (mínimo 1 noite)"""
    payload = {
        "acomodacao_id": 1,
        "checkin": "2026-11-20",
        "checkout": "2026-11-20",
        "num_hospedes": 1
    }
    res = client.post('/api/reservas', json=payload)
    assert res.status_code == 400
    assert "RN-01" in res.get_json()['erro']

def test_rn02_capacidade_maxima(client):
    """RN-02: Hóspedes não podem ultrapassar a capacidade da acomodação"""
    # Acomodação 2 possui capacidade máxima igual a 2
    payload = {
        "acomodacao_id": 2,
        "checkin": "2026-11-20",
        "checkout": "2026-11-23",
        "num_hospedes": 5
    }
    res = client.post('/api/reservas', json=payload)
    assert res.status_code == 400
    assert "RN-02" in res.get_json()['erro']

def test_rf18_rn07_desconto_superhost(client):
    """RF-18 / RN-07: Taxa de serviço de 14% com 10% de desconto para Superhost"""
    # Acomodação 2 é Superhost: diária 300 x 2 noites = 600 diárias
    # Taxa regular (14%): 84.00
    # Desconto Superhost (10% sobre 84.00): 8.40
    # Total esperado: 600 + 84 - 8.40 = 675.60
    payload = {
        "acomodacao_id": 2,
        "checkin": "2026-12-01",
        "checkout": "2026-12-03",
        "num_hospedes": 2
    }
    res = client.post('/api/reservas', json=payload)
    assert res.status_code == 200
    reserva_id = res.get_json()['reserva_id']

    conn = get_db()
    r = conn.execute("SELECT * FROM reserva WHERE id = ?", (reserva_id,)).fetchone()
    conn.close()
    assert r['subtotalDiarias'] == 600.0
    assert r['taxaServico'] == 84.0
    assert r['descontoSuperhost'] == 8.4
    assert r['valorTotal'] == 675.6

def test_rf19_impedir_sobreposicao(client):
    """RF-19: Bloquear reservas sobrepostas na mesma acomodação"""
    payload = {
        "acomodacao_id": 1,
        "checkin": "2026-12-10",
        "checkout": "2026-12-15",
        "num_hospedes": 2
    }
    res1 = client.post('/api/reservas', json=payload)
    assert res1.status_code == 200

    payload_conflito = {
        "acomodacao_id": 1,
        "checkin": "2026-12-12",
        "checkout": "2026-12-18",
        "num_hospedes": 2
    }
    res2 = client.post('/api/reservas', json=payload_conflito)
    assert res2.status_code == 409
    assert "RF-19" in res2.get_json()['erro']

def test_fluxo_cartao_recusa_e_aprovacao(client):
    """RF-25 / RF-26: Trata recusa e autoriza nova tentativa mantendo a reserva"""
    res = client.post('/api/reservas', json={
        "acomodacao_id": 1, "checkin": "2026-12-20", "checkout": "2026-12-22", "num_hospedes": 1
    })
    reserva_id = res.get_json()['reserva_id']

    # 1. Cartão com final 0000 -> Simula recusa
    res_recusa = client.post(f'/api/reservas/{reserva_id}/pagar-cartao', json={"numero_cartao": "4111111111110000"})
    assert res_recusa.status_code == 422
    assert res_recusa.get_json()['status'] == 'RECUSADO'

    # 2. Nova tentativa com cartão válido -> Aprovado
    res_aprov = client.post(f'/api/reservas/{reserva_id}/pagar-cartao', json={"numero_cartao": "4111111111111234"})
    assert res_aprov.status_code == 200
    assert res_aprov.get_json()['status'] == 'APROVADO'

def test_fluxo_pix_assincrono(client):
    """RF-23: Cobrança PIX com txid único e compensação via Webhook"""
    res = client.post('/api/reservas', json={
        "acomodacao_id": 1, "checkin": "2026-12-25", "checkout": "2026-12-28", "num_hospedes": 1
    })
    reserva_id = res.get_json()['reserva_id']

    res_pix = client.post(f'/api/reservas/{reserva_id}/gerar-pix')
    txid = res_pix.get_json()['txid']

    # Disparo assíncrono simulado
    res_webhook = client.post('/api/webhook/pix', json={"txid": txid, "valor": 684.0})
    assert res_webhook.status_code == 200

    conn = get_db()
    r = conn.execute("SELECT status FROM reserva WHERE id = ?", (reserva_id,)).fetchone()
    conn.close()
    assert r['status'] == 'CONFIRMADA'
```

---

## 5. Manual de Execução e Guia de Testes

### Pré-requisitos
- Python 3.9 ou superior instalado.

### Passo a Passo de Instalação e Execução
1. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   # Linux / macOS:
   source venv/bin/activate
   # Windows:
   venv\Scripts\activate
   ```
2. Instale as bibliotecas necessárias:
   ```bash
   pip install -r requirements.txt
   ```
3. Inicie o servidor:
   ```bash
   python app.py
   ```
4. Abra o navegador no endereço: `http://localhost:5000`

### Como Testar Todos os Cenários

1. **Caminho Feliz com Cartão de Crédito:**
   - Na listagem, escolha a primeira acomodação e clique em "Iniciar Reserva".
   - Na **Tela 1 (Resumo)**, valide os cálculos das diárias e a taxa de 14%. Clique em "Confirmar e Ir para Pagamento".
   - Na **Tela 2 (Pagamento)**, preencha o formulário com qualquer número fictício (ex.: `4111 2222 3333 4444`) e clique em "Pagar com Cartão".
   - A resposta síncrona redireciona para a **Tela 3 (Confirmação)**, exibindo o código de autorização e o endereço físico (rua e CEP desmascarados).

2. **Cenário de Recusa e Retentativa (RF-26):**
   - Na Tela 2, preencha o cartão com final `0000` (ex.: `4111 2222 3333 0000`).
   - A transação será recusada e uma mensagem de erro será exibida em tela vermelha, mantendo a reserva `PENDENTE`.
   - Altere o número para outro final (ex.: `4111 2222 3333 1111`) e clique novamente para aprovar.

3. **Cenário PIX Assíncrono com Webhook (RF-23):**
   - Na Tela 2, selecione a aba **PIX**.
   - Clique em "Gerar Código PIX" para obter o QR Code e o payload copia e cola com o `txid` único.
   - Clique no botão azul "Disparar Webhook de Liquidação" no quadro de simulação bancária.
   - O JavaScript detectará a mudança via polling e redirecionará automaticamente para a Tela 3.

4. **Cenário do Benefício Superhost (RN-07 / RF-33):**
   - Na tela inicial, selecione a acomodação "Studio Luxo Superhost".
   - Na Tela 1, observe a linha verde destacando o abatimento de 10% sobre a taxa de serviço.

5. **Execução da Bateria Automatizada de Testes:**
   ```bash
   pytest -v
   ```