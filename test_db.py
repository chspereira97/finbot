"""
test_db.py - Teste rápido do banco de dados
"""

import asyncio
from datetime import datetime
from database import init_db, AsyncSessionLocal, Usuario, Categoria, Transacao

async def main():
    await init_db()
    print("✅ Banco inicializado com sucesso!")

    async with AsyncSessionLocal() as session:
        # 1. Criar um usuário com chaves
        usuario = Usuario(
            nome="Carlos Teste",
            telefone="5511999999999",
            grupo_id="120363408845928882@g.us",
            chave_login="FIN-ABC123",
            chave_senha="FIN-XYZ789"
        )
        session.add(usuario)
        await session.commit()
        await session.refresh(usuario)
        print(f"✅ Usuário criado: {usuario.nome} (ID: {usuario.id})")
        print(f"   Login: {usuario.chave_login}")
        print(f"   Senha: {usuario.chave_senha}")

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
            grupo_id=usuario.grupo_id
        )
        session.add(transacao)
        await session.commit()
        await session.refresh(transacao)
        print(f"✅ Transação criada: R$ {transacao.valor:.2f} - {transacao.descricao} (ID: {transacao.id})")

        # 4. Listar transações
        from sqlalchemy import select
        stmt = select(Transacao)
        result = await session.execute(stmt)
        transacoes = result.scalars().all()
        print("\n📋 Transações no banco:")
        for t in transacoes:
            print(f"  - R$ {t.valor:.2f} | {t.descricao} | {t.categoria.nome} | {t.data.strftime('%d/%m/%Y')}")

if __name__ == "__main__":
    asyncio.run(main())
