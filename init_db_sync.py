import sqlite3
import os

os.makedirs("data", exist_ok=True)
conn = sqlite3.connect("data/financeiro.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    telefone TEXT,
    grupo_id TEXT NOT NULL,
    chave_login TEXT NOT NULL,
    chave_senha TEXT NOT NULL,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL,
    usuario_id INTEGER NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    categoria_id INTEGER NOT NULL,
    mes_id INTEGER,
    grupo_id TEXT NOT NULL,
    forma_pagamento TEXT,
    parcelas INTEGER,
    parcela_atual INTEGER,
    data_vencimento DATETIME,
    transacao_original_id INTEGER,
    valor REAL NOT NULL,
    descricao TEXT,
    tipo TEXT NOT NULL,
    data DATETIME DEFAULT CURRENT_TIMESTAMP,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    FOREIGN KEY (categoria_id) REFERENCES categorias (id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS meses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mes INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    grupo_id TEXT NOT NULL,
    data_inicio DATETIME NOT NULL,
    data_fim DATETIME NOT NULL,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(mes, ano, grupo_id)
)
""")

# Inserir usuário de teste
cursor.execute("""
INSERT OR IGNORE INTO usuarios (nome, telefone, grupo_id, chave_login, chave_senha)
VALUES ('Carlos Teste', '5511999999999', '120363408845928882@g.us', 'FIN-ABC123', 'FIN-XYZ789')
""")

conn.commit()
conn.close()

print("✅ Banco criado com sucesso!")
