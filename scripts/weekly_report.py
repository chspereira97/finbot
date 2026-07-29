"""
weekly_report.py - Relatório semanal do FinBot
Envia um resumo da semana para todos os grupos ativos.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
from datetime import datetime, timedelta
from sqlalchemy import select

from database import AsyncSessionLocal, Transacao, Usuario, Categoria
from repositories import TransacaoRepository

INSTANCIA = "finbot"
API_KEY = "D3C7E34BD4DF-44FE-85A7-ACD98CC1B0AD"
EVOLUTION_URL = "http://localhost:8080"


async def enviar_mensagem(telefone: str, texto: str):
    url = f"{EVOLUTION_URL}/message/sendText/{INSTANCIA}"
    payload = {"number": telefone, "text": texto}
    headers = {"apikey": API_KEY, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")
        return False


async def get_grupos_ativos():
    async with AsyncSessionLocal() as session:
        stmt = select(Transacao.grupo_id).distinct().where(Transacao.grupo_id.isnot(None))
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]


async def gerar_relatorio_semanal(grupo_id: str):
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_semana = hoje - timedelta(days=7)

    async with AsyncSessionLocal() as session:
        transacao_repo = TransacaoRepository(session)
        transacoes = await transacao_repo.listar_por_grupo(grupo_id, periodo=(inicio_semana, hoje))

        if not transacoes:
            return f"📊 *Nenhuma transação registrada esta semana.*"

        total_despesas = sum(t.valor for t in transacoes if t.tipo == 'D')
        total_receitas = sum(t.valor for t in transacoes if t.tipo == 'R')
        saldo = total_receitas - total_despesas

        por_pessoa = {}
        for t in transacoes:
            if t.tipo == 'D':
                nome = t.usuario.nome if t.usuario.nome else t.usuario.telefone
                por_pessoa[nome] = por_pessoa.get(nome, 0) + t.valor

        resposta = f"📊 *Resumo da semana ({inicio_semana.strftime('%d/%m')} a {hoje.strftime('%d/%m/%Y')})*\n\n"
        resposta += f"📉 *Despesas:* R$ {total_despesas:.2f}\n"
        resposta += f"📈 *Receitas:* R$ {total_receitas:.2f}\n"
        resposta += f"💰 *Saldo:* R$ {saldo:.2f}\n\n"

        if por_pessoa:
            resposta += "*Quem mais gastou:*\n"
            for nome, valor in sorted(por_pessoa.items(), key=lambda x: x[1], reverse=True):
                resposta += f"  {nome}: R$ {valor:.2f}\n"

        return resposta


async def main():
    print(f"📊 Gerando relatório semanal - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    grupos = await get_grupos_ativos()
    if not grupos:
        print("📭 Nenhum grupo ativo encontrado.")
        return
    for grupo_id in grupos:
        print(f"📤 Enviando relatório para {grupo_id}")
        relatorio = await gerar_relatorio_semanal(grupo_id)
        await enviar_mensagem(grupo_id, relatorio)
        await asyncio.sleep(1)
    print("✅ Relatórios enviados com sucesso!")


if __name__ == "__main__":
    asyncio.run(main())
