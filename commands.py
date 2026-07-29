"""
commands.py - Comandos do FinBot
"""

from datetime import datetime
from collections import defaultdict
import secrets

from sqlalchemy import select

from database import AsyncSessionLocal, Usuario
from repositories import TransacaoRepository, MesRepository, UsuarioRepository


async def cmd_total(grupo_id: str) -> str:
    async with AsyncSessionLocal() as session:
        mes_repo = MesRepository(session)
        mes_atual = await mes_repo.get_or_create_mes_atual(grupo_id)
        transacao_repo = TransacaoRepository(session)
        totais = await transacao_repo.total_por_grupo(grupo_id, mes_id=mes_atual.id)
        return (
            f"💰 *Saldo do mês:* R$ {totais['saldo']:.2f}\n"
            f"📈 *Receitas:* R$ {totais['receitas']:.2f}\n"
            f"📉 *Despesas:* R$ {totais['despesas']:.2f}"
        )


async def cmd_resumo(grupo_id: str) -> str:
    async with AsyncSessionLocal() as session:
        mes_repo = MesRepository(session)
        mes_atual = await mes_repo.get_or_create_mes_atual(grupo_id)
        transacao_repo = TransacaoRepository(session)
        transacoes = await transacao_repo.listar_por_grupo(grupo_id, mes_id=mes_atual.id)
        if not transacoes:
            return f"📭 Nenhuma transação registrada em {mes_atual.mes:02d}/{mes_atual.ano}."
        categorias_despesas = defaultdict(float)
        categorias_receitas = defaultdict(float)
        for t in transacoes:
            nome_categoria = t.categoria.nome if t.categoria else "Sem categoria"
            nome_usuario = t.usuario.nome if t.usuario.nome else t.usuario.telefone
            forma = t.forma_pagamento if t.forma_pagamento else "Não informado"
            if t.tipo == 'D':
                chave = f"{nome_usuario} - {nome_categoria}"
                categorias_despesas[chave] += t.valor
            elif t.tipo == 'R':
                chave = f"{nome_usuario} - {nome_categoria}"
                categorias_receitas[chave] += t.valor
        resposta = f"📊 *Resumo do mês {mes_atual.mes:02d}/{mes_atual.ano}:*\n\n"
        if categorias_despesas:
            resposta += "📉 *Despesas:*\n"
            for chave, valor in sorted(categorias_despesas.items(), key=lambda x: x[1], reverse=True):
                resposta += f"  {chave}: R$ {valor:.2f}\n"
        if categorias_receitas:
            resposta += "\n📈 *Receitas:*\n"
            for chave, valor in sorted(categorias_receitas.items(), key=lambda x: x[1], reverse=True):
                resposta += f"  {chave}: R$ {valor:.2f}\n"
        totais = await transacao_repo.total_por_grupo(grupo_id, mes_id=mes_atual.id)
        resposta += f"\n💰 *Saldo do mês:* R$ {totais['saldo']:.2f}"
        return resposta


async def cmd_ultimos(grupo_id: str, n: int) -> str:
    if n <= 0:
        return "⚠️ Use um número positivo (ex: /ultimos 5)"
    if n > 20:
        n = 20
    async with AsyncSessionLocal() as session:
        mes_repo = MesRepository(session)
        mes_atual = await mes_repo.get_or_create_mes_atual(grupo_id)
        transacao_repo = TransacaoRepository(session)
        transacoes = await transacao_repo.listar_por_grupo(grupo_id, mes_id=mes_atual.id)
        if not transacoes:
            return f"📭 Nenhuma transação registrada em {mes_atual.mes:02d}/{mes_atual.ano}."
        ultimas = transacoes[:n]
        resposta = f"📋 *Últimas {len(ultimas)} transações:*\n\n"
        for i, t in enumerate(ultimas, 1):
            tipo_emoji = "📈" if t.tipo == 'R' else "📉"
            data_str = t.data.strftime("%d/%m/%Y")
            nome_usuario = t.usuario.nome if t.usuario.nome else t.usuario.telefone
            nome_categoria = t.categoria.nome if t.categoria else "Sem categoria"
            forma = t.forma_pagamento if t.forma_pagamento else "Não informado"
            resposta += f"{i}. {tipo_emoji} R$ {t.valor:.2f} | {nome_usuario} - {nome_categoria} | {forma} | {data_str}\n"
        return resposta


async def cmd_apagar(telefone: str, transacao_id: int) -> str:
    async with AsyncSessionLocal() as session:
        usuario_repo = UsuarioRepository(session)
        usuario = await usuario_repo.get_or_create_by_telefone(telefone, "")
        stmt = select(Transacao).where(Transacao.id == transacao_id, Transacao.usuario_id == usuario.id)
        result = await session.execute(stmt)
        transacao = result.scalar_one_or_none()
        if not transacao:
            return f"❌ Transação {transacao_id} não encontrada."
        transacao_repo = TransacaoRepository(session)
        deletado = await transacao_repo.deletar(transacao_id)
        if deletado:
            return f"✅ Transação {transacao_id} apagada com sucesso!"
        return f"❌ Erro ao apagar transação {transacao_id}."


async def cmd_editar(telefone: str, transacao_id: int, novo_valor: float) -> str:
    if novo_valor <= 0:
        return "⚠️ O valor deve ser positivo."
    async with AsyncSessionLocal() as session:
        usuario_repo = UsuarioRepository(session)
        usuario = await usuario_repo.get_or_create_by_telefone(telefone, "")
        stmt = select(Transacao).where(Transacao.id == transacao_id, Transacao.usuario_id == usuario.id)
        result = await session.execute(stmt)
        transacao = result.scalar_one_or_none()
        if not transacao:
            return f"❌ Transação {transacao_id} não encontrada."
        transacao.valor = novo_valor
        await session.commit()
        return f"✅ Transação {transacao_id} atualizada: R$ {novo_valor:.2f}"


async def cmd_meu_nome(telefone: str, grupo_id: str, nome: str) -> str:
    async with AsyncSessionLocal() as session:
        usuario_repo = UsuarioRepository(session)
        usuario = await usuario_repo.get_or_create_by_telefone(telefone, grupo_id)
        usuario.nome = nome
        await session.commit()
        return f"✅ Nome atualizado para *{nome}*!"


async def cmd_chaves(remetente: str, grupo_id: str) -> str:
    """Comando /chaves - Gera chaves de acesso específicas para o grupo"""
    async with AsyncSessionLocal() as session:
        # Busca o usuário pelo telefone e grupo
        stmt = select(Usuario).where(
            Usuario.telefone == remetente,
            Usuario.grupo_id == grupo_id
        )
        result = await session.execute(stmt)
        usuario = result.scalar_one_or_none()

        if not usuario:
            # Se não existir, cria com chaves específicas do grupo
            login = secrets.token_hex(4).upper()
            senha = secrets.token_hex(4).upper()
            usuario = Usuario(
                telefone=remetente,
                nome=None,
                grupo_id=grupo_id,
                chave_login=login,
                chave_senha=senha
            )
            session.add(usuario)
            await session.commit()
            await session.refresh(usuario)
        else:
            login = usuario.chave_login
            senha = usuario.chave_senha
        
        return (
            f"🔑 *Chaves de acesso deste grupo:*\n\n"
            f"📌 *Login:* `{login}`\n"
            f"🔒 *Senha:* `{senha}`\n\n"
            f"Acesse o dashboard em:\n"
            f"https://server.tailb5388f.ts.net/dashboard\n\n"
            f"⚠️ *Estas chaves são específicas para este grupo!*\n"
            f"Cada grupo tem suas próprias chaves."
        )


async def cmd_ajuda() -> str:
    return (
        "🤖 *FinBot - Assistente Financeiro*\n\n"
        "📌 *Comandos disponíveis:*\n\n"
        "📝 *Registrar gastos:*\n"
        "  `padaria 25,50` → Registra uma despesa\n"
        "  `salário 2500` → Registra uma receita\n\n"
        "📊 *Consultar:*\n"
        "  `/total` → Saldo do mês atual\n"
        "  `/resumo` → Resumo do mês atual\n"
        "  `/ultimos 5` → Últimas 5 transações\n\n"
        "✏️ *Gerenciar:*\n"
        "  `/editar ID VALOR` → Edita uma transação\n"
        "  `/apagar ID` → Apaga uma transação\n"
        "  `/meu_nome NOME` → Define seu nome\n\n"
        "🔑 *Convite:*\n"
        "  `/chaves` → Gera chaves de acesso para o dashboard\n\n"
        "❓ *Ajuda:*\n"
        "  `/ajuda` → Mostra esta mensagem\n\n"
        "💬 *\"A melhor maneira de prever o futuro é criá-lo.\"* — Peter Drucker"
    )
