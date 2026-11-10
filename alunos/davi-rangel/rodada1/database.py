import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.path.join(BASE_DIR, "hospedagem.db")

def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # B.4 Projeto de tabelas da ERS v1.1 / v1.2
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
