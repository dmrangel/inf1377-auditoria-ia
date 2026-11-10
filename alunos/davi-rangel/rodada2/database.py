"""
database.py - Inicialização do Banco de Dados SQLite e Schema da ERS v1.2
Projeto: Plataforma de Hospedagem (INF1377 - Engenharia de Requisitos)
Responsável: Fluxo de Reserva, Pagamento e Confirmação
"""

import os
import sqlite3
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hospedagem.db")


def get_db_connection():
    """Retorna uma conexão com o SQLite configurada para dicionários (sqlite3.Row)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(force_recreate=False):
    """
    Cria as tabelas conforme o Apêndice B.4 da ERS v1.2 e popula dados de teste
    se o banco estiver vazio ou force_recreate=True.
    """
    if force_recreate and os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela: usuario (Apêndice B.4)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senhaHash TEXT NOT NULL,
            telefone TEXT NOT NULL,
            dataCadastro TEXT NOT NULL,
            ehAnfitriao INTEGER NOT NULL DEFAULT 0,
            superhost INTEGER NOT NULL DEFAULT 0,
            taxaResposta REAL NOT NULL DEFAULT 1.0
        );
    """)

    # Tabela: acomodacao (Apêndice B.4)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acomodacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anfitriao_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            precoNoite REAL NOT NULL,
            capacidadeMaxima INTEGER NOT NULL,
            quartos INTEGER NOT NULL,
            banheiros INTEGER NOT NULL,
            camas INTEGER NOT NULL,
            regras TEXT NOT NULL,
            cep TEXT NOT NULL,
            rua TEXT NOT NULL,
            numero TEXT NOT NULL,
            bairro TEXT NOT NULL,
            cidade TEXT NOT NULL,
            estado TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (anfitriao_id) REFERENCES usuario (id)
        );
    """)

    # Tabela: reserva (Apêndice B.4 + dataCriacao para controle de expiração de 30 min)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reserva (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospede_id INTEGER NOT NULL,
            acomodacao_id INTEGER NOT NULL,
            checkIn TEXT NOT NULL,
            checkOut TEXT NOT NULL,
            numHospedes INTEGER NOT NULL,
            valorTotal REAL NOT NULL,
            status TEXT NOT NULL, -- PENDENTE, CONFIRMADA, CANCELADA, CONCLUIDA
            dataCriacao TEXT NOT NULL,
            FOREIGN KEY (hospede_id) REFERENCES usuario (id),
            FOREIGN KEY (acomodacao_id) REFERENCES acomodacao (id)
        );
    """)

    # Tabela: pagamento (Apêndice B.4 + tokenCartao para conformidade RNF-08)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reserva_id INTEGER NOT NULL,
            txid TEXT NOT NULL UNIQUE,
            metodo TEXT NOT NULL, -- CARTAO_CREDITO, PIX
            valor REAL NOT NULL,
            codigoAutorizacao TEXT,
            status TEXT NOT NULL, -- PROCESSANDO, APROVADO, RECUSADO, REEMBOLSADO
            dataHora TEXT NOT NULL,
            tokenCartao TEXT,
            FOREIGN KEY (reserva_id) REFERENCES reserva (id)
        );
    """)

    # Tabela: historico_status_reserva (Apêndice B.4 / RNF-22 Auditoria)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_status_reserva (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reserva_id INTEGER NOT NULL,
            statusAnterior TEXT,
            statusNovo TEXT NOT NULL,
            dataHora TEXT NOT NULL,
            responsavel_id INTEGER,
            FOREIGN KEY (reserva_id) REFERENCES reserva (id),
            FOREIGN KEY (responsavel_id) REFERENCES usuario (id)
        );
    """)

    # Tabela: historico_status_pagamento (Apêndice B.4 / RNF-22 Auditoria)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_status_pagamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pagamento_id INTEGER NOT NULL,
            statusAnterior TEXT,
            statusNovo TEXT NOT NULL,
            dataHora TEXT NOT NULL,
            responsavel_id INTEGER,
            FOREIGN KEY (pagamento_id) REFERENCES pagamento (id),
            FOREIGN KEY (responsavel_id) REFERENCES usuario (id)
        );
    """)

    # Tabelas opcionais do modelo para integridade da ERS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS avaliacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reserva_id INTEGER NOT NULL,
            autor_id INTEGER NOT NULL,
            nota INTEGER NOT NULL,
            comentario TEXT,
            dataAvaliacao TEXT NOT NULL,
            UNIQUE (reserva_id, autor_id),
            FOREIGN KEY (reserva_id) REFERENCES reserva (id),
            FOREIGN KEY (autor_id) REFERENCES usuario (id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS denuncia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            autor_id INTEGER NOT NULL,
            acomodacao_id INTEGER NOT NULL,
            motivo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            status TEXT NOT NULL,
            parecer TEXT,
            admin_id INTEGER,
            FOREIGN KEY (autor_id) REFERENCES usuario (id),
            FOREIGN KEY (acomodacao_id) REFERENCES acomodacao (id),
            FOREIGN KEY (admin_id) REFERENCES usuario (id)
        );
    """)

    conn.commit()

    # Verificar se já existem dados de teste populados
    cursor.execute("SELECT COUNT(*) as total FROM usuario;")
    if cursor.fetchone()["total"] == 0:
        seed_test_data(conn)

    conn.close()


def seed_test_data(conn):
    """Popula dados de exemplo completos para viabilizar todos os cenários de teste."""
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()

    # 1. Usuários
    # Hóspede de teste logado por padrão
    cursor.execute("""
        INSERT INTO usuario (nome, email, senhaHash, telefone, dataCadastro, ehAnfitriao, superhost, taxaResposta)
        VALUES (?, ?, ?, ?, ?, 0, 0, 1.0)
    """, ("Lucas Hóspede", "hospede_teste@exemplo.com", generate_password_hash("Senha@123"), "(21) 98888-1111", now_iso))
    hospede_id = cursor.lastrowid

    # Hóspede secundário para testar isolamento de acesso (RNF-11)
    cursor.execute("""
        INSERT INTO usuario (nome, email, senhaHash, telefone, dataCadastro, ehAnfitriao, superhost, taxaResposta)
        VALUES (?, ?, ?, ?, ?, 0, 0, 1.0)
    """, ("Ana Outra Hóspede", "ana_hospede@exemplo.com", generate_password_hash("Senha@123"), "(21) 98888-2222", now_iso))
    outro_hospede_id = cursor.lastrowid

    # Anfitrião Normal (não superhost)
    cursor.execute("""
        INSERT INTO usuario (nome, email, senhaHash, telefone, dataCadastro, ehAnfitriao, superhost, taxaResposta)
        VALUES (?, ?, ?, ?, ?, 1, 0, 0.88)
    """, ("Carlos Eduardo (Anfitrião Padrão)", "carlos_anfitriao@exemplo.com", generate_password_hash("Senha@123"), "(21) 97777-1111", now_iso))
    anfitriao_comum_id = cursor.lastrowid

    # Anfitrião Superhost (com selo e desconto de 10% na taxa de serviço - RN-07)
    cursor.execute("""
        INSERT INTO usuario (nome, email, senhaHash, telefone, dataCadastro, ehAnfitriao, superhost, taxaResposta)
        VALUES (?, ?, ?, ?, ?, 1, 1, 0.98)
    """, ("Mariana Silva (Superhost)", "mariana_superhost@exemplo.com", generate_password_hash("Senha@123"), "(21) 96666-2222", now_iso))
    anfitriao_superhost_id = cursor.lastrowid

    # 2. Acomodações
    # Acomodação 1: Padrão (Copacabana, anfitrião comum, diária R$ 250, capacidade 4)
    cursor.execute("""
        INSERT INTO acomodacao (
            anfitriao_id, titulo, descricao, precoNoite, capacidadeMaxima,
            quartos, banheiros, camas, regras,
            cep, rua, numero, bairro, cidade, estado, ativo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        anfitriao_comum_id,
        "Apartamento Aconchegante a 2 Minutos da Praia de Copacabana",
        "Lindo apartamento ensolarado, ventilado, reformado e totalmente equipado. Próximo ao metrô e principais restaurantes.",
        250.00,
        4,
        2,
        2,
        3,
        "1. Proibido fumar dentro do apartamento.\n2. Proibido eventos ou festas.\n3. Horário de silêncio: 22h às 08h.\n4. Animais de estimação não permitidos.",
        "22021-001",
        "Avenida Atlântica",
        "1500, apto 402",
        "Copacabana",
        "Rio de Janeiro",
        "RJ",
        1
    ))
    acomodacao_1_id = cursor.lastrowid

    # Acomodação 2: Superhost (Ipanema, desconto de 10% sobre a taxa de serviço, diária R$ 400, capacidade 2)
    cursor.execute("""
        INSERT INTO acomodacao (
            anfitriao_id, titulo, descricao, precoNoite, capacidadeMaxima,
            quartos, banheiros, camas, regras,
            cep, rua, numero, bairro, cidade, estado, ativo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        anfitriao_superhost_id,
        "Loft Moderno em Ipanema com Vista Panorâmica",
        "Hospede-se com um Superhost experiente em um dos melhores pontos da Zona Sul. Design sofisticado e vista exuberante.",
        400.00,
        2,
        1,
        1,
        1,
        "1. Proibido fumar.\n2. Não são permitidas festas.\n3. Aceita pets de pequeno porte com aviso prévio.\n4. Respeitar o limite de 2 hóspedes.",
        "22421-010",
        "Rua Garcia d'Ávila",
        "88, Cobertura 01",
        "Ipanema",
        "Rio de Janeiro",
        "RJ",
        1
    ))
    acomodacao_2_id = cursor.lastrowid

    # Acomodação 3: Para teste de conflito de datas / sobreposição (RF-19)
    # Tem capacidade 6, diária R$ 300
    cursor.execute("""
        INSERT INTO acomodacao (
            anfitriao_id, titulo, descricao, precoNoite, capacidadeMaxima,
            quartos, banheiros, camas, regras,
            cep, rua, numero, bairro, cidade, estado, ativo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        anfitriao_comum_id,
        "Chalé Rústico e Espaçoso no Alto da Serra",
        "Ideal para famílias e grupos de amigos que buscam tranquilidade e contato com a natureza.",
        300.00,
        6,
        3,
        2,
        4,
        "1. Apagar a lareira antes de dormir.\n2. Não jogar bitucas ou lixo na mata.\n3. Manter a porteira fechada.",
        "25960-000",
        "Estrada da Serra Encantada",
        "S/N, Km 12",
        "Alto",
        "Teresópolis",
        "RJ",
        1
    ))
    acomodacao_3_id = cursor.lastrowid

    # Acomodação 4: Inativa (ativo = 0, para testar recusa de reserva em anúncio desativado)
    cursor.execute("""
        INSERT INTO acomodacao (
            anfitriao_id, titulo, descricao, precoNoite, capacidadeMaxima,
            quartos, banheiros, camas, regras,
            cep, rua, numero, bairro, cidade, estado, ativo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        anfitriao_comum_id,
        "Estúdio Temporariamente Fechado para Obras",
        "Em reforma geral.",
        150.00,
        2,
        1,
        1,
        1,
        "Não disponível.",
        "20040-000",
        "Rua da Carioca",
        "10",
        "Centro",
        "Rio de Janeiro",
        "RJ",
        0
    ))

    # 3. Criar uma reserva CONFIRMADA existente na Acomodação 3 para demonstrar bloqueio de datas (RF-19)
    # Datas de teste fixadas para o próximo mês
    hoje = date.today()
    checkin_ocupado = (hoje + timedelta(days=20)).strftime("%Y-%m-%d")
    checkout_ocupado = (hoje + timedelta(days=25)).strftime("%Y-%m-%d")

    cursor.execute("""
        INSERT INTO reserva (hospede_id, acomodacao_id, checkIn, checkOut, numHospedes, valorTotal, status, dataCriacao)
        VALUES (?, ?, ?, ?, ?, ?, 'CONFIRMADA', ?)
    """, (outro_hospede_id, acomodacao_3_id, checkin_ocupado, checkout_ocupado, 2, 1710.00, now_iso))
    reserva_existente_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora, responsavel_id)
        VALUES (?, NULL, 'PENDENTE', ?, ?), (?, 'PENDENTE', 'CONFIRMADA', ?, ?)
    """, (reserva_existente_id, now_iso, outro_hospede_id, reserva_existente_id, now_iso, None))

    conn.commit()
    print("[database] Banco SQLite inicializado com sucesso e dados de exemplo inseridos.")


if __name__ == "__main__":
    init_db(force_recreate=True)
