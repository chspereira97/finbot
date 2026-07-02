"""
test_repositories.py - Testa os repositórios do FinBot
Usa um banco de testes separado (test_financeiro.db) que é recriado do zero.
"""

import asyncio
import os
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from database import Base, Usuario, Categoria, Transacao
from repositories import UsuarioRepository, CategoriaRepository, TransacaoRepository


# Banco de testes separado
TEST_DATABASE_URL = "sqlite+aiosqlite:///data/test_financeiro.db"


async def init_test_db():
    """Inicializa o banco de testes do zero"""
    # Remove o banco antigo se existir
    if os.path.exists("data/test_financeiro.db"):
        os.remove("data/test_financeiro.db")

    # Cria engine e tabelas
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.run_sync(Base.metadata.create_all)

    return engine


async def test_repositories():
    """Testa todos os repositórios com banco limpo"""
    print("=" * 50)
    print("🧪 TESTANDO REPOSITÓRIOS (banco de testes)")
    print("=" * 50)

    # Inicializa banco de testes limpo
    engine = await init_test_db()
    print("\n✅ Banco de testes inicializado (limpo)")

    # Sessão assíncrona
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. UsuarioRepository
        print("\n📌 TESTE: UsuarioRepository")
        usuario_repo = UsuarioRepository(session)

        usuario = await usuario_repo.get_or_create_by_telefone("5511999999999")
        print(f"✅ Usuário: {usuario.nome or 'Sem nome'} (ID: {usuario.id})")

        usuario2 = await usuario_repo.get_or_create_by_telefone("5511988888888")
        print(f"✅ Usuário 2: {usuario2.nome or 'Sem nome'} (ID: {usuario2.id})")

        # 2. CategoriaRepository
        print("\n📌 TESTE: CategoriaRepository")
        categoria_repo = CategoriaRepository(session)

        cat1 = await categoria_repo.get_or_create_by_nome("alimentação", "D", usuario.id)
        print(f"✅ Categoria: {cat1.nome} (ID: {cat1.id})")

        cat2 = await categoria_repo.get_or_create_by_nome("salário", "R", usuario.id)
        print(f"✅ Categoria: {cat2.nome} (ID: {cat2.id})")

        cat3 = await categoria_repo.get_or_create_by_nome("Alimentação", "D", usuario.id)
        print(f"✅ Categoria (case-insensitive): {cat3.nome} (ID: {cat3.id}) -> deve ser a mesma")

        # 3. TransacaoRepository
        print("\n📌 TESTE: TransacaoRepository")
        transacao_repo = TransacaoRepository(session)

        t1 = await transacao_repo.criar(
            usuario_id=usuario.id,
            categoria_id=cat1.id,
            valor=25.50,
            descricao="Padaria",
            tipo="D"
        )
        print(f"✅ Transação 1: R$ {t1.valor:.2f} - {t1.descricao} (ID: {t1.id})")

        t2 = await transacao_repo.criar(
            usuario_id=usuario.id,
            categoria_id=cat2.id,
            valor=1000.00,
            descricao="Salário mensal",
            tipo="R",
            data=datetime.now() - timedelta(days=5)
        )
        print(f"✅ Transação 2: R$ {t2.valor:.2f} - {t2.descricao} (ID: {t2.id})")

        # 4. Listar transações
        print("\n📌 TESTE: listar_por_usuario")
        transacoes = await transacao_repo.listar_por_usuario(usuario.id)
        print(f"✅ Total de transações: {len(transacoes)}")
        for t in transacoes:
            print(f"  - R$ {t.valor:.2f} | {t.descricao} | {t.categoria.nome} | {t.data.strftime('%d/%m/%Y')}")

        # 5. Listar por período
        print("\n📌 TESTE: listar_por_usuario com período")
        hoje = datetime.now()
        inicio = hoje - timedelta(days=10)
        fim = hoje + timedelta(days=1)
        transacoes_periodo = await transacao_repo.listar_por_usuario(
            usuario.id,
            periodo=(inicio, fim)
        )
        print(f"✅ Transações nos últimos 10 dias: {len(transacoes_periodo)}")

        # 6. Totais
        print("\n📌 TESTE: total_por_usuario")
        totais = await transacao_repo.total_por_usuario(usuario.id)
        print(f"✅ Receitas: R$ {totais['receitas']:.2f}")
        print(f"✅ Despesas: R$ {totais['despesas']:.2f}")
        print(f"✅ Saldo: R$ {totais['saldo']:.2f}")

        # 7. Deletar transação
        print("\n📌 TESTE: deletar")
        deletado = await transacao_repo.deletar(t1.id)
        print(f"✅ Transação {t1.id} deletada: {deletado}")

        transacoes_restantes = await transacao_repo.listar_por_usuario(usuario.id)
        print(f"✅ Transações restantes: {len(transacoes_restantes)}")

        # 8. Listar categorias
        print("\n📌 TESTE: listar_todas")
        categorias = await categoria_repo.listar_todas(usuario.id)
        print(f"✅ Categorias do usuário: {len(categorias)}")
        for cat in categorias:
            print(f"  - {cat.nome} ({cat.tipo})")

    print("\n" + "=" * 50)
    print("✅ TODOS OS TESTES CONCLUÍDOS!")
    print(f"📁 Banco de testes: data/test_financeiro.db")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_repositories())
