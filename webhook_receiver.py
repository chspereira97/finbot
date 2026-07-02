"""
webhook_receiver.py - Webhook do FinBot (Multiusuário)
Recebe mensagens do WhatsApp e processa por grupo (família)
"""

from fastapi import FastAPI, Request
import logging
import httpx
import re
from datetime import datetime
from collections import defaultdict

from sqlalchemy import select

from database import AsyncSessionLocal, init_db, Usuario, Transacao
from repositories import UsuarioRepository, CategoriaRepository, TransacaoRepository
from message_parser import extrair_info_mensagem

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FinBot Webhook")

# 🔧 CONFIGURAÇÕES DA EVOLUTION API
INSTANCIA = "finbot"
API_KEY = "A606DD7229DA-4DCF-9856-91D2963A33F0"


@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("✅ Banco de dados inicializado")


async def enviar_mensagem(telefone: str, texto: str):
    """Envia mensagem via Evolution API"""
    url = f"http://localhost:8080/message/sendText/{INSTANCIA}"
    payload = {"number": telefone, "text": texto}
    headers = {
        "apikey": API_KEY,
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in [200, 201]:
                logger.info(f"✅ Mensagem enviada para {telefone}")
            else:
                logger.error(f"❌ Erro ao enviar mensagem: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {e}")


async def processar_comando(remetente: str, grupo_id: str, texto: str) -> str:
    texto = texto.strip()
    partes = texto.split()

    if texto == "/total":
        return await cmd_total(grupo_id)

    if texto == "/resumo":
        return await cmd_resumo(grupo_id)

    if texto.startswith("/ultimos"):
        if len(partes) == 2:
            try:
                n = int(partes[1])
                return await cmd_ultimos(grupo_id, n)
            except ValueError:
                return "⚠️ Use /ultimos NUMERO (ex: /ultimos 5)"
        return "⚠️ Use /ultimos NUMERO (ex: /ultimos 5)"

    if texto.startswith("/apagar"):
        if len(partes) == 2:
            try:
                transacao_id = int(partes[1])
                return await cmd_apagar(remetente, transacao_id)
            except ValueError:
                return "⚠️ Use /apagar ID (ex: /apagar 5)"
        return "⚠️ Use /apagar ID (ex: /apagar 5)"

    if texto.startswith("/editar"):
        if len(partes) == 3:
            try:
                transacao_id = int(partes[1])
                novo_valor = float(partes[2].replace(',', '.'))
                return await cmd_editar(remetente, transacao_id, novo_valor)
            except ValueError:
                return "⚠️ Use /editar ID VALOR (ex: /editar 5 30.00)"
        return "⚠️ Use /editar ID VALOR (ex: /editar 5 30.00)"

    if texto.startswith("/meu_nome"):
        if len(partes) >= 2:
            nome = " ".join(partes[1:])
            return await cmd_meu_nome(remetente, grupo_id, nome)
        return "⚠️ Use /meu_nome SEU_NOME (ex: /meu_nome Carlos)"

    return None


async def cmd_total(grupo_id: str) -> str:
    async with AsyncSessionLocal() as session:
        transacao_repo = TransacaoRepository(session)
        totais = await transacao_repo.total_por_grupo(grupo_id)
        return (
            f"💰 *Saldo total do grupo:* R$ {totais['saldo']:.2f}\n"
            f"📈 *Receitas:* R$ {totais['receitas']:.2f}\n"
            f"📉 *Despesas:* R$ {totais['despesas']:.2f}"
        )


async def cmd_resumo(grupo_id: str) -> str:
    async with AsyncSessionLocal() as session:
        transacao_repo = TransacaoRepository(session)
        transacoes = await transacao_repo.listar_por_grupo(grupo_id)

        if not transacoes:
            return "📭 Nenhuma transação encontrada."

        categorias_despesas = defaultdict(float)
        categorias_receitas = defaultdict(float)

        for t in transacoes:
            nome_categoria = t.categoria.nome if t.categoria else "Sem categoria"
            nome_usuario = t.usuario.nome if t.usuario.nome else t.usuario.telefone

            if t.tipo == 'D':
                chave = f"{nome_usuario} - {nome_categoria}"
                categorias_despesas[chave] += t.valor
            elif t.tipo == 'R':
                chave = f"{nome_usuario} - {nome_categoria}"
                categorias_receitas[chave] += t.valor

        resposta = "📊 *Resumo do grupo:*\n\n"

        if categorias_despesas:
            resposta += "📉 *Despesas:*\n"
            for chave, valor in sorted(categorias_despesas.items(), key=lambda x: x[1], reverse=True):
                resposta += f"  {chave}: R$ {valor:.2f}\n"

        if categorias_receitas:
            resposta += "\n📈 *Receitas:*\n"
            for chave, valor in sorted(categorias_receitas.items(), key=lambda x: x[1], reverse=True):
                resposta += f"  {chave}: R$ {valor:.2f}\n"

        totais = await transacao_repo.total_por_grupo(grupo_id)
        resposta += f"\n💰 *Saldo total do grupo:* R$ {totais['saldo']:.2f}"

        return resposta


async def cmd_ultimos(grupo_id: str, n: int) -> str:
    if n <= 0:
        return "⚠️ Use um número positivo (ex: /ultimos 5)"
    if n > 20:
        n = 20

    async with AsyncSessionLocal() as session:
        transacao_repo = TransacaoRepository(session)
        transacoes = await transacao_repo.listar_por_grupo(grupo_id)

        if not transacoes:
            return "📭 Nenhuma transação encontrada."

        ultimas = transacoes[:n]
        resposta = f"📋 *Últimas {len(ultimas)} transações do grupo:*\n\n"
        for i, t in enumerate(ultimas, 1):
            tipo_emoji = "📈" if t.tipo == 'R' else "📉"
            data_str = t.data.strftime("%d/%m/%Y")
            nome_usuario = t.usuario.nome if t.usuario.nome else t.usuario.telefone
            nome_categoria = t.categoria.nome if t.categoria else "Sem categoria"
            resposta += f"{i}. {tipo_emoji} R$ {t.valor:.2f} | {nome_usuario} - {nome_categoria} | {data_str}\n"
        return resposta


async def cmd_apagar(telefone: str, transacao_id: int) -> str:
    async with AsyncSessionLocal() as session:
        usuario_repo = UsuarioRepository(session)
        usuario = await usuario_repo.get_or_create_by_telefone(telefone, "")

        stmt = select(Transacao).where(
            Transacao.id == transacao_id,
            Transacao.usuario_id == usuario.id
        )
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

        stmt = select(Transacao).where(
            Transacao.id == transacao_id,
            Transacao.usuario_id == usuario.id
        )
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


@app.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request):
    try:
        data = await request.json()
        logger.info(f"📩 Mensagem recebida: {data}")

        evento = data.get("event")
        if evento != "messages.upsert":
            return {"status": "ignored", "message": f"Evento ignorado: {evento}"}

        dados = data.get("data")
        if not dados:
            return {"status": "ignored", "message": "Sem dados"}

        if isinstance(dados, dict):
            dados = [dados]

        for msg in dados:
            key = msg.get("key", {})
            remote_jid = key.get("remoteJid", "")
            participant = key.get("participant", "")
            participant_alt = key.get("participantAlt", "")

            # 🔧 Extrai o remetente (prioriza participantAlt quando disponível)
            if participant_alt:
                remetente = participant_alt.split("@")[0]
            elif participant:
                remetente = participant.split("@")[0]
            elif remote_jid:
                remetente = remote_jid.split("@")[0]
            else:
                logger.warning("🚫 Mensagem sem remetente (ignorada)")
                continue

            # Remove caracteres especiais
            remetente = re.sub(r'[^0-9]', '', remetente)
            if not remetente:
                continue

            # 🔧 Identificador do grupo
            if "@g.us" in remote_jid:
                grupo_id = remote_jid
            else:
                grupo_id = None

            mensagem_obj = msg.get("message", {})
            texto = mensagem_obj.get("conversation", "")
            if not texto:
                texto = mensagem_obj.get("extendedTextMessage", {}).get("text", "")

            if not texto:
                continue

            logger.info(f"📝 Mensagem de {remetente} no grupo {grupo_id}: {texto}")

            # 🔧 Se for mensagem privada, avisa
            if not grupo_id:
                await enviar_mensagem(remetente, "⚠️ Use o grupo para registrar gastos.")
                return {"status": "success", "message": "Aviso enviado"}

            # 🔧 Registra/atualiza o usuário com grupo_id
            async with AsyncSessionLocal() as session:
                usuario_repo = UsuarioRepository(session)
                await usuario_repo.get_or_create_by_telefone(remetente, grupo_id)

            # 🔧 Processa comando ou transação
            if texto.strip().startswith("/"):
                resposta = await processar_comando(remetente, grupo_id, texto)
                if resposta:
                    await enviar_mensagem(grupo_id, resposta)
                    return {"status": "success", "message": "Comando processado", "resposta": resposta}

            resposta = await processar_mensagem(remetente, grupo_id, texto)
            await enviar_mensagem(grupo_id, resposta)

            return {"status": "success", "message": "Mensagem processada", "resposta": resposta}

        return {"status": "success", "message": "Processado"}

    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook: {e}")
        return {"status": "error", "message": str(e)}


async def processar_mensagem(telefone: str, grupo_id: str, texto: str) -> str:
    info = extrair_info_mensagem(texto)
    logger.info(f"📊 Informações extraídas: {info}")

    if info['valor'] is None:
        return "⚠️ Não consegui identificar o valor. Exemplo: 'padaria 25,50'"

    if info['categoria'] is None:
        return "⚠️ Não consegui identificar a categoria. Exemplo: 'padaria 25,50'"

    async with AsyncSessionLocal() as session:
        usuario_repo = UsuarioRepository(session)
        usuario = await usuario_repo.get_or_create_by_telefone(telefone, grupo_id)

        categoria_repo = CategoriaRepository(session)
        categoria = await categoria_repo.get_or_create_by_nome(
            info['categoria'],
            info['tipo'],
            usuario.id
        )

        data = info['data'] if info['data'] else datetime.now()

        transacao_repo = TransacaoRepository(session)
        transacao = await transacao_repo.criar(
            usuario_id=usuario.id,
            categoria_id=categoria.id,
            valor=info['valor'],
            descricao=texto[:100],
            tipo=info['tipo'],
            grupo_id=grupo_id,  # 🔧 NOVO: salva o grupo na transação
            data=data
        )

        logger.info(f"✅ Transação salva: ID {transacao.id}")

    tipo_texto = "Receita" if info['tipo'] == 'R' else "Despesa"
    data_formatada = data.strftime("%d/%m/%Y")
    nome_usuario = usuario.nome if usuario.nome else usuario.telefone
    return (
        f"✅ {tipo_texto} registrada com sucesso!\n"
        f"👤 *Usuário:* {nome_usuario}\n"
        f"📌 *Categoria:* {categoria.nome}\n"
        f"💰 *Valor:* R$ {info['valor']:.2f}\n"
        f"📅 *Data:* {data_formatada}"
    )


@app.get("/")
async def root():
    return {"message": "FinBot está rodando!"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "finbot-webhook"}
