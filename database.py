"""
database.py - Configuração do banco de dados e modelos SQLAlchemy
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func, text, UniqueConstraint
import os
from datetime import datetime, timedelta

os.makedirs("data", exist_ok=True)

DATABASE_URL = "sqlite+aiosqlite:///data/financeiro.db"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.run_sync(Base.metadata.create_all)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=True)
    telefone = Column(String, unique=True, index=True, nullable=False)
    grupo_id = Column(String, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())

    categorias = relationship("Categoria", back_populates="usuario")
    transacoes = relationship("Transacao", back_populates="usuario")


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    usuario = relationship("Usuario", back_populates="categorias")
    transacoes = relationship("Transacao", back_populates="categoria")


class Mes(Base):
    __tablename__ = "meses"
    __table_args__ = (UniqueConstraint('mes', 'ano', 'grupo_id', name='uq_mes_ano_grupo'),)

    id = Column(Integer, primary_key=True, index=True)
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    grupo_id = Column(String, nullable=False)
    data_inicio = Column(DateTime, nullable=False)
    data_fim = Column(DateTime, nullable=False)
    criado_em = Column(DateTime, server_default=func.now())

    transacoes = relationship("Transacao", back_populates="mes")

    @classmethod
    def criar_para_grupo(cls, grupo_id: str):
        agora = datetime.now()
        mes = agora.month
        ano = agora.year
        data_inicio = datetime(ano, mes, 1)
        if mes == 12:
            data_fim = datetime(ano + 1, 1, 1) - timedelta(days=1)
        else:
            data_fim = datetime(ano, mes + 1, 1) - timedelta(days=1)
        return cls(
            mes=mes,
            ano=ano,
            grupo_id=grupo_id,
            data_inicio=data_inicio,
            data_fim=data_fim
        )


class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    mes_id = Column(Integer, ForeignKey("meses.id"), nullable=True)
    grupo_id = Column(String, nullable=True)

    # 🔧 NOVAS COLUNAS: forma de pagamento e parcelamento
    forma_pagamento = Column(String, nullable=True)  # pix, credito, debito, dinheiro
    parcelas = Column(Integer, nullable=True)        # número total de parcelas
    parcela_atual = Column(Integer, nullable=True)   # parcela atual (1, 2, 3...)
    data_vencimento = Column(DateTime, nullable=True)  # data de vencimento da parcela
    transacao_original_id = Column(Integer, nullable=True)  # ID da transação original (para parcelas)

    valor = Column(Float, nullable=False)
    descricao = Column(String, nullable=True)
    tipo = Column(String, nullable=False)
    data = Column(DateTime, server_default=func.now())
    criado_em = Column(DateTime, server_default=func.now())

    usuario = relationship("Usuario", back_populates="transacoes")
    categoria = relationship("Categoria", back_populates="transacoes")
    mes = relationship("Mes", back_populates="transacoes")


async def get_session() -> AsyncSession:
    return AsyncSessionLocal()
