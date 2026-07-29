"""
inactivity_reminder.py - Lembrete de inatividade
Lembra se o usuário não registrou nada no dia.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
from datetime import datetime, timedelta
from sqlalchemy import select

from database import AsyncSessionLocal, Transacao, Usuario

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


async def get_grupos_com_usuarios():
    """Busca grupos que têm pelo menos um usuário registrado"""
    async with AsyncSessionLocal() as session:
        stmt = select(Usuario.grupo_id).distinct().where(Usuario.grupo_id.isnot(None))
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]


async def get_transacoes_hoje(grupo_id: str):
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    amanha = hoje + timedelta(days=1)
    async with AsyncSessionLocal() as session:
        stmt = select(Transacao).where(
            Transacao.grupo_id == grupo_id,
            Transacao.data >= hoje,
            Transacao.data < amanha
        )
        result = await session.execute(stmt)
        return result.scalars().all()


async def main():
    print(f"📋 Verificando inatividade - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    grupos = await get_grupos_com_usuarios()

    for grupo_id in grupos:
        transacoes = await get_transacoes_hoje(grupo_id)
        if not transacoes:
            print(f"🔔 Grupo {grupo_id} não registrou nada hoje")
            await enviar_mensagem(
                grupo_id,
                f"🔔 *Lembrete de inatividade*\n\n"
                f"Você ainda não registrou nenhum gasto hoje!\n"
                f"Use *padaria 25,50* para registrar uma despesa."
            )
            await asyncio.sleep(1)

    print("✅ Verificação concluída!")


if __name__ == "__main__":
    asyncio.run(main())
