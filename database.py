"""
database.py - Configuração do banco de dados e modelos SQLAlchemy
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func, text
import os

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


class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    grupo_id = Column(String, nullable=True)  # 🔧 NOVO: isola gastos por grupo
    valor = Column(Float, nullable=False)
    descricao = Column(String, nullable=True)
    tipo = Column(String, nullable=False)
    data = Column(DateTime, server_default=func.now())
    criado_em = Column(DateTime, server_default=func.now())

    usuario = relationship("Usuario", back_populates="transacoes")
    categoria = relationship("Categoria", back_populates="transacoes")


async def get_session() -> AsyncSession:
    return AsyncSessionLocal()
