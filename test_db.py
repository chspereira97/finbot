"""
test_db.py - Teste rápido do banco de dados (versão assíncrona)
"""

import asyncio
from datetime import datetime
from database import init_db, AsyncSessionLocal, Usuario, Categoria, Transacao


async def main():
    # Inicializa o banco
    await init_db()
    print("✅ Banco inicializado com sucesso!")

    async with AsyncSessionLocal() as session:
        # 1. Criar usuário
        usuario = Usuario(
            nome="Carlos Teste",
            telefone="5511999999999",
            grupo_id="120363420879818756@g.us"  # 🔧 COM O CAMPO NOVO
        )
        session.add(usuario)
        await session.commit()
        await session.refresh(usuario)
        print(f"✅ Usuário criado: {usuario.nome} (ID: {usuario.id})")

        # 2. Criar categoria
        categoria = Categoria(
            nome="Alimentação",
            tipo="D",
            usuario_id=usuario.id
        )
        session.add(categoria)
        await session.commit()
        await session.refresh(categoria)
        print(f"✅ Categoria criada: {categoria.nome} (ID: {categoria.id})")

        # 3. Criar transação
        transacao = Transacao(
            usuario_id=usuario.id,
            categoria_id=categoria.id,
            valor=25.50,
            descricao="Padaria",
            tipo="D",
            data=datetime.now()
        )
        session.add(transacao)
        await session.commit()
        await session.refresh(transacao)
        print(f"✅ Transação criada: R$ {transacao.valor:.2f} - {transacao.descricao} (ID: {transacao.id})")

        # 4. Listar transações
        print("\n📋 Transações no banco:")
        from sqlalchemy import select
        stmt = select(Transacao)
        result = await session.execute(stmt)
        transacoes = result.scalars().all()
        for t in transacoes:
            print(f"  - R$ {t.valor:.2f} | {t.descricao} | {t.categoria.nome} | {t.data.strftime('%d/%m/%Y')}")

    # 5. Verificar arquivo
    import os
    if os.path.exists("data/financeiro.db"):
        print("\n✅ Banco de dados criado: data/financeiro.db")
    else:
        print("\n❌ Banco de dados NÃO foi criado!")


if __name__ == "__main__":
    asyncio.run(main())
