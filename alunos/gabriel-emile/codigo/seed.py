"""Dados de exemplo para demonstrar todos os cenários da busca e do anúncio.

As datas são relativas a "hoje" (momento em que o banco é criado). Para recriar
os dados com datas atualizadas, apague instancia/plataforma.db e rode o app de
novo.

CENÁRIO PRINCIPAL DE DEMONSTRAÇÃO (ver README):
    Cidade "Rio de Janeiro", bairro "Copacabana",
    check-in = hoje + 14 dias, check-out = hoje + 17 dias, 2 hóspedes.

Acomodações em Copacabana e por que aparecem ou não nesse cenário:
    #1  Apartamento com vista para o mar  -> APARECE (nota 4,67)
    #2  Studio perto da praia             -> NÃO: reserva CONFIRMADA no período
    #3  Cobertura duplex com piscina      -> APARECE (reserva termina no dia do check-in)
    #4  Quarto econômico                  -> NÃO: capacidade 1 < 2 hóspedes
    #5  Apartamento familiar              -> NÃO: datas bloqueadas pelo anfitrião
    #6  Flat moderno no Posto 6           -> NÃO: reserva PENDENTE criada há 10 min
    #7  Kitnet reformada                  -> APARECE (PENDENTE vencida há 2 h; sem nota)
    #8  Apartamento desativado            -> NÃO: ativo = 0
    #9  Apartamento sob denúncia          -> NÃO: denúncia de risco EM_ANALISE
    #10 Apartamento na Rua Barata Ribeiro -> APARECE (denúncia que não é de risco)
    #11 Anúncio com só 3 fotos            -> NÃO: menos de 5 fotos
"""
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

SENHA_TESTE = "senha123"  # só para os usuários de teste locais

CATEGORIAS_FOTOS = ["fachada", "sala de estar", "quarto principal", "cozinha", "banheiro", "vista"]


def popular(con, agora=None):
    agora = (agora or datetime.now()).replace(microsecond=0)
    hoje = agora.date()

    def dia(delta):
        return (hoje + timedelta(days=delta)).isoformat()

    def momento(delta_minutos=0, delta_dias=0):
        return (agora + timedelta(days=delta_dias, minutes=delta_minutos)).isoformat(timespec="seconds")

    senha = generate_password_hash(SENHA_TESTE)

    # ------------------------------------------------------------------ usuários
    usuarios = [
        # id, nome, email, ehAnfitriao, superhost, taxaResposta, cadastro (dias atrás)
        (1, "Ana Souza", "ana@teste.local", 0, 0, None, 400),
        (2, "Bruno Lima", "bruno@teste.local", 1, 1, 0.98, 1200),
        (3, "Carla Mendes", "carla@teste.local", 1, 0, 0.85, 700),
        (4, "Diego Rocha", "diego@teste.local", 0, 0, None, 300),
        (5, "Elisa Prado", "elisa@teste.local", 0, 0, None, 500),
        (6, "Fábio Admin", "admin@teste.local", 0, 0, None, 900),
    ]
    con.executemany(
        """INSERT INTO usuario (id, nome, email, senhaHash, telefone, dataCadastro,
                                ehAnfitriao, superhost, taxaResposta)
           VALUES (?, ?, ?, ?, '(21) 99999-0000', ?, ?, ?, ?)""",
        [(u[0], u[1], u[2], senha, dia(-u[6]), u[3], u[4], u[5]) for u in usuarios],
    )

    # -------------------------------------------------------------- acomodações
    regras_padrao = "Proibido fumar. Sem festas ou eventos. Silêncio após as 22h."
    acomodacoes = [
        # id, anfitriao, titulo, preco, cap, quartos, banh, camas, cep, rua, numero, bairro, cidade, uf, ativo
        (1, 2, "Apartamento com vista para o mar", 450, 4, 2, 1, 3, "22021-001", "Avenida Atlântica", "1702", "Copacabana", "Rio de Janeiro", "RJ", 1),
        (2, 2, "Studio aconchegante perto da praia", 180, 2, 1, 1, 1, "22041-001", "Rua Barata Ribeiro", "200", "Copacabana", "Rio de Janeiro", "RJ", 1),
        (3, 2, "Cobertura duplex com piscina", 1200, 8, 4, 3, 5, "22041-011", "Rua Santa Clara", "50", "Copacabana", "Rio de Janeiro", "RJ", 1),
        (4, 3, "Quarto econômico em Copacabana", 95, 1, 1, 1, 1, "22031-001", "Rua Siqueira Campos", "30", "Copacabana", "Rio de Janeiro", "RJ", 1),
        (5, 3, "Apartamento familiar em Copacabana", 600, 6, 3, 2, 4, "22050-001", "Rua Tonelero", "100", "Copacabana", "Rio de Janeiro", "RJ", 1),
        (6, 3, "Flat moderno no Posto 6", 320, 3, 1, 1, 2, "22081-020", "Rua Francisco Otaviano", "20", "Copacabana", "Rio de Janeiro", "RJ", 1),
        (7, 3, "Kitnet reformada", 150, 2, 1, 1, 1, "22070-011", "Rua Bolívar", "10", "Copacabana", "Rio de Janeiro", "RJ", 1),
        (8, 2, "Apartamento desativado", 200, 4, 2, 1, 2, "22020-001", "Rua Ronald de Carvalho", "15", "Copacabana", "Rio de Janeiro", "RJ", 0),
        (9, 3, "Apartamento sob denúncia", 210, 4, 2, 1, 2, "22011-001", "Rua Ministro Viveiros de Castro", "40", "Copacabana", "Rio de Janeiro", "RJ", 1),
        (10, 3, "Apartamento na Rua Barata Ribeiro", 280, 4, 2, 2, 2, "22040-002", "Rua Barata Ribeiro", "500", "Copacabana", "Rio de Janeiro", "RJ", 1),
        (11, 2, "Anúncio com só 3 fotos", 130, 2, 1, 1, 1, "22010-010", "Rua Duvivier", "12", "Copacabana", "Rio de Janeiro", "RJ", 1),
        (12, 2, "Casa charmosa em Ipanema", 700, 5, 3, 2, 3, "22410-002", "Rua Visconde de Pirajá", "300", "Ipanema", "Rio de Janeiro", "RJ", 1),
        (13, 3, "Apartamento no Leblon", 520, 4, 2, 2, 2, "22440-032", "Rua Dias Ferreira", "100", "Leblon", "Rio de Janeiro", "RJ", 1),
        (14, 2, "Casa colonial em Santa Teresa", 380, 6, 3, 2, 4, "20241-000", "Rua Almirante Alexandrino", "800", "Santa Teresa", "Rio de Janeiro", "RJ", 1),
        (15, 3, "Loft em Pinheiros", 330, 2, 1, 1, 1, "05422-001", "Rua dos Pinheiros", "500", "Pinheiros", "São Paulo", "SP", 1),
        (16, 3, "Studio na Vila Madalena", 210, 2, 1, 1, 1, "05433-000", "Rua Aspicuelta", "60", "Vila Madalena", "São Paulo", "SP", 1),
        (17, 2, "Chalé na Serra", 400, 4, 2, 1, 3, "25745-000", "Estrada das Videiras", "3000", "Vale das Videiras", "Petrópolis", "RJ", 1),
    ]
    con.executemany(
        """INSERT INTO acomodacao (id, anfitriao_id, titulo, descricao, precoNoite, capacidadeMaxima,
                                   quartos, banheiros, camas, regras, cep, rua, numero, bairro,
                                   cidade, estado, ativo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (a[0], a[1], a[2],
             f"{a[2]} em {a[11]}, {a[12]}. Espaço bem iluminado, roupa de cama e toalhas incluídas, "
             f"Wi-Fi rápido e cozinha equipada. Acomoda até {a[4]} pessoa(s).",
             a[3], a[4], a[5], a[6], a[7], regras_padrao, a[8], a[9], a[10], a[11], a[12], a[13], a[14])
            for a in acomodacoes
        ],
    )

    # ------------------------------------------------------------------- fotos
    fotos = []
    for a in acomodacoes:
        quantidade = 3 if a[0] == 11 else 6  # #11 viola RF-08 (menos de 5 fotos)
        for ordem in range(quantidade):
            categoria = CATEGORIAS_FOTOS[ordem]
            chave = f"fotos/{a[0]}/{categoria.replace(' ', '-')}.svg"
            if a[0] == 15 and ordem == 2:
                chave = "ausente/15/quarto-principal.jpg"  # arquivo que sumiu do armazenamento
            fotos.append((a[0], chave, f"{categoria.capitalize()} - {a[2]}", ordem))
    con.executemany(
        "INSERT INTO foto_acomodacao (acomodacao_id, chave, legenda, ordem) VALUES (?, ?, ?, ?)", fotos
    )

    # ----------------------------------------------------------------- reservas
    reservas_criadas = {}

    def reserva(rid, hospede, acom, ini, fim, n, status, criada_min=None):
        preco = next(a[3] for a in acomodacoes if a[0] == acom)
        noites = fim - ini
        valor = round(noites * preco * 1.14, 2)  # RN-03 (só para preencher valorTotal)
        con.execute(
            """INSERT INTO reserva (id, hospede_id, acomodacao_id, checkIn, checkOut, numHospedes, valorTotal, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (rid, hospede, acom, dia(ini), dia(fim), n, valor, status),
        )
        # Histórico (B.4): a criação como PENDENTE e, se for o caso, a mudança final.
        criada = momento(delta_minutos=criada_min) if criada_min is not None else momento(delta_dias=min(ini, 0) - 10)
        con.execute(
            "INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora, responsavel_id) VALUES (?, NULL, 'PENDENTE', ?, ?)",
            (rid, criada, hospede),
        )
        if status != "PENDENTE":
            caminho = ["CONFIRMADA"] if status in ("CONFIRMADA", "CONCLUIDA") else []
            if status == "CONCLUIDA":
                caminho.append("CONCLUIDA")
            if status == "CANCELADA":
                caminho.append("CANCELADA")
            anterior = "PENDENTE"
            for novo in caminho:
                con.execute(
                    "INSERT INTO historico_status_reserva (reserva_id, statusAnterior, statusNovo, dataHora, responsavel_id) VALUES (?, ?, ?, ?, ?)",
                    (rid, anterior, novo, criada, hospede if novo == "CANCELADA" else None),
                )
                anterior = novo
        reservas_criadas[rid] = (hospede, acom, ini, fim)

    # Passadas e concluídas (geram avaliações)
    reserva(101, 1, 1, -60, -55, 2, "CONCLUIDA")
    reserva(102, 5, 1, -40, -36, 2, "CONCLUIDA")
    reserva(103, 4, 1, -20, -18, 2, "CONCLUIDA")
    reserva(104, 5, 3, -90, -85, 6, "CONCLUIDA")
    reserva(105, 1, 3, -30, -25, 4, "CONCLUIDA")
    reserva(106, 4, 12, -50, -45, 3, "CONCLUIDA")
    reserva(107, 1, 13, -5, -3, 2, "CONCLUIDA")   # avaliação ainda não publicada
    reserva(108, 5, 14, -70, -65, 4, "CONCLUIDA")
    reserva(109, 1, 15, -100, -95, 2, "CONCLUIDA")
    reserva(110, 4, 2, -200, -195, 2, "CONCLUIDA")
    reserva(111, 4, 16, -9, -7, 2, "CONCLUIDA")   # só o anfitrião avaliou (não publica)

    # Futuras (afetam a disponibilidade e o endereço exato)
    reserva(201, 1, 1, 40, 45, 2, "CONFIRMADA")    # Ana vê o endereço exato do #1
    reserva(202, 1, 2, 10, 12, 2, "CANCELADA")     # cancelada: não libera endereço nem ocupa
    reserva(203, 5, 2, 14, 18, 2, "CONFIRMADA")    # ocupa o período de demonstração
    reserva(204, 4, 6, 13, 15, 2, "PENDENTE", criada_min=-10)   # PENDENTE válida
    reserva(205, 4, 7, 14, 17, 2, "PENDENTE", criada_min=-120)  # PENDENTE vencida (RN-04)
    reserva(206, 4, 3, 10, 14, 4, "CONFIRMADA")    # sai no dia do check-in da demonstração
    reserva(207, 4, 15, 14, 17, 2, "PENDENTE")     # Diego tem PENDENTE no #15: NÃO vê endereço

    # ---------------------------------------------------------------- bloqueios
    con.execute(
        "INSERT INTO bloqueio_data (acomodacao_id, dataInicio, dataFim) VALUES (5, ?, ?)", (dia(15), dia(16))
    )
    con.execute(
        "INSERT INTO bloqueio_data (acomodacao_id, dataInicio, dataFim) VALUES (1, ?, ?)", (dia(25), dia(28))
    )

    # --------------------------------------------------------------- avaliações
    def avaliacao(rid, autor, nota, comentario, dias_apos_checkout=1):
        fim = reservas_criadas[rid][3]
        data_av = min(fim + dias_apos_checkout, 0)
        con.execute(
            "INSERT INTO avaliacao (reserva_id, autor_id, nota, comentario, dataAvaliacao) VALUES (?, ?, ?, ?, ?)",
            (rid, autor, nota, comentario, dia(data_av)),
        )

    # #1: três avaliações publicadas -> média (5+4+5)/3 = 4,67
    avaliacao(101, 1, 5, "Vista incrível e anfitrião muito atencioso.")
    avaliacao(101, 2, 5, "Hóspede exemplar.")                # do anfitrião: não aparece no anúncio
    avaliacao(102, 5, 4, "Ótima localização, mas o chuveiro é fraco.")
    avaliacao(102, 2, 5, "Recomendo a hóspede.")
    avaliacao(103, 4, 5, None)                               # comentário é opcional (RF-29); publicada por prazo
    # #3: média 4,5
    avaliacao(104, 5, 5, "Piscina maravilhosa, perfeita para a família.")
    avaliacao(104, 2, 4, "Deixou a casa em ordem.")
    avaliacao(105, 1, 4, "Espaçosa, mas a escada é íngreme.")
    avaliacao(105, 2, 5, "Ótima hóspede.")
    # #12: média 3,0
    avaliacao(106, 4, 3, "Bonita, porém barulhenta à noite.")
    avaliacao(106, 2, 4, "Tudo certo.")
    # #13: só a hóspede avaliou e o prazo de 14 dias ainda não acabou -> NÃO publicada
    avaliacao(107, 1, 2, "Estava sujo na chegada.")
    # #14: média 5,0
    avaliacao(108, 5, 5, "Casa linda e cheia de história.")
    avaliacao(108, 2, 5, "Hóspede cuidadosa.")
    # #15: média 4,0
    avaliacao(109, 1, 4, "Bom custo-benefício.")
    avaliacao(109, 3, 4, "Tranquila.")
    # #2: média 3,0
    avaliacao(110, 4, 3, None)
    avaliacao(110, 2, 4, "Ok.")
    # #16: só a anfitriã avaliou o hóspede (avaliação sobre o hóspede, nunca aparece)
    avaliacao(111, 3, 2, "Hóspede deixou bagunça.")

    # ---------------------------------------------------------------- denúncias
    con.execute(
        """INSERT INTO denuncia (autor_id, acomodacao_id, motivo, descricao, status)
           VALUES (5, 9, 'RISCO_SEGURANCA', 'Fiação elétrica exposta no banheiro.', 'EM_ANALISE')"""
    )
    con.execute(
        """INSERT INTO denuncia (autor_id, acomodacao_id, motivo, descricao, status)
           VALUES (1, 10, 'INFORMACOES_FALSAS', 'As fotos parecem de outro imóvel.', 'EM_ANALISE')"""
    )
    con.execute(
        """INSERT INTO denuncia (autor_id, acomodacao_id, motivo, descricao, status, parecer, admin_id)
           VALUES (4, 12, 'RISCO_SEGURANCA', 'Grade da varanda solta.', 'IMPROCEDENTE',
                   'Vistoria não encontrou problema.', 6)"""
    )
    con.commit()
