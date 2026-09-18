"""
webhook_receiver.py - Webhook do FinBot
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import httpx
import re
import os
from datetime import datetime, timedelta
from typing import Optional

from database import AsyncSessionLocal, init_db
from repositories import UsuarioRepository, CategoriaRepository, TransacaoRepository, MesRepository
from message_parser import extrair_info_mensagem
from conversation_manager import (
    conversation_manager,
    ESTADO_AGUARDANDO_FORMA,
    ESTADO_AGUARDANDO_PARCELAS,
    ESTADO_AGUARDANDO_DATA,
    ESTADO_NORMAL
)
from commands import (
    cmd_total,
    cmd_resumo,
    cmd_ultimos,
    cmd_apagar,
    cmd_editar,
    cmd_meu_nome,
    cmd_chaves,
    cmd_chaves_renovar,
    cmd_ajuda
)
from dashboard_api import router as dashboard_router
from config import EVOLUTION_API_URL, EVOLUTION_INSTANCE, require_env

EVOLUTION_API_KEY = require_env("EVOLUTION_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FinBot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# DASHBOARD - ARQUIVOS ESTÁTICOS
# ============================================================

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/login")
async def login_page():
    return FileResponse("static/login.html")

@app.get("/dashboard")
async def dashboard_page():
    return FileResponse("static/dashboard.html")

@app.get("/dashboard/")
async def dashboard_page_slash():
    return FileResponse("static/dashboard.html")

app.include_router(dashboard_router)

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

async def enviar_mensagem(telefone: str, texto: str):
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    payload = {"number": telefone, "text": texto}
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in [200, 201]:
                logger.info(f"✅ Mensagem enviada para {telefone}")
            else:
                logger.error(f"❌ Erro ao enviar mensagem: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {e}")

async def processar_comando(remetente: str, grupo_id: str, texto: str) -> Optional[str]:
    texto = texto.strip()
    partes = texto.split()

    if texto == "/total":
        return await cmd_total(grupo_id)
    if texto == "/resumo":
        return await cmd_resumo(grupo_id)
    if texto == "/ajuda":
        return await cmd_ajuda()
    if texto == "/chaves":
        return await cmd_chaves(remetente, grupo_id)
    if texto == "/chaves_renovar":
        return await cmd_chaves_renovar(remetente, grupo_id)
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


async def finalizar_transacao(remetente: str, grupo_id: str, dados: dict) -> str:
    """Finaliza o registro da transação com todas as informações coletadas"""
    forma = dados.get('forma_pagamento')
    parcelas = dados.get('parcelas', 1)
    data_vencimento = dados.get('data_vencimento')
    texto = dados.get('texto_original', '')

    info = extrair_info_mensagem(texto)
    if info['valor'] is None:
        conversation_manager.resetar(remetente, grupo_id)
        return "⚠️ Erro: não consegui identificar o valor da transação."
    if info['categoria'] is None:
        conversation_manager.resetar(remetente, grupo_id)
        return "⚠️ Erro: não consegui identificar a categoria."

    async with AsyncSessionLocal() as session:
        usuario_repo = UsuarioRepository(session)
        usuario = await usuario_repo.get_or_create_by_telefone(remetente, grupo_id)

        categoria_repo = CategoriaRepository(session)
        categoria = await categoria_repo.get_or_create_by_nome(info['categoria'], info['tipo'], usuario.id)

        mes_repo = MesRepository(session)
        mes_atual = await mes_repo.get_or_create_mes_atual(grupo_id)

        transacao_repo = TransacaoRepository(session)
        data = info['data'] if info['data'] else datetime.now()

        if forma == "credito" and parcelas > 1:
            valor_parcela = round(info['valor'] / parcelas, 2)
            transacao_original = None
            for i in range(parcelas):
                if data_vencimento:
                    data_parcela = data_vencimento + timedelta(days=30 * i)
                else:
                    data_parcela = data + timedelta(days=30 * (i + 1))
                transacao = await transacao_repo.criar(
                    usuario_id=usuario.id,
                    categoria_id=categoria.id,
                    valor=valor_parcela,
                    descricao=f"{info['categoria']} ({i+1}/{parcelas})",
                    tipo=info['tipo'],
                    grupo_id=grupo_id,
                    mes_id=mes_atual.id,
                    forma_pagamento=forma,
                    parcelas=parcelas,
                    parcela_atual=i+1,
                    data_vencimento=data_parcela,
                    transacao_original_id=transacao_original.id if transacao_original else None,
                    data=data_parcela if data_vencimento else data
                )
                if i == 0:
                    transacao_original = transacao
                logger.info(f"✅ Parcela {i+1}/{parcelas} salva: ID {transacao.id}")
            resposta = (
                f"✅ Despesa registrada com sucesso!\n"
                f"📌 Categoria: {categoria.nome}\n"
                f"💳 Forma: {forma.capitalize()} ({parcelas}x)\n"
                f"💰 Total: R$ {info['valor']:.2f} (R$ {valor_parcela:.2f}/parcela)\n"
                f"📅 Primeira parcela: {data_vencimento.strftime('%d/%m/%Y') if data_vencimento else data.strftime('%d/%m/%Y')}"
            )
        else:
            transacao = await transacao_repo.criar(
                usuario_id=usuario.id,
                categoria_id=categoria.id,
                valor=info['valor'],
                descricao=texto[:100],
                tipo=info['tipo'],
                grupo_id=grupo_id,
                mes_id=mes_atual.id,
                forma_pagamento=forma,
                parcelas=parcelas,
                parcela_atual=1,
                data_vencimento=data_vencimento if forma == "credito" else data,
                data=data
            )
            logger.info(f"✅ Transação salva: ID {transacao.id}")
            tipo_texto = "Receita" if info['tipo'] == 'R' else "Despesa"
            data_exibicao = data_vencimento if forma == "credito" else data
            data_formatada = data_exibicao.strftime("%d/%m/%Y") if data_exibicao else data.strftime("%d/%m/%Y")
            resposta = (
                f"✅ {tipo_texto} registrada com sucesso!\n"
                f"👤 *Usuário:* {usuario.nome or usuario.telefone}\n"
                f"📌 *Categoria:* {categoria.nome}\n"
                f"💳 *Forma:* {forma.capitalize()}\n"
                f"💰 *Valor:* R$ {info['valor']:.2f}\n"
                f"📅 *Data:* {data_formatada}"
            )

    conversation_manager.resetar(remetente, grupo_id)
    return resposta


async def processar_resposta_conversa(remetente: str, grupo_id: str, texto: str) -> Optional[str]:
    estado = conversation_manager.get_estado(remetente, grupo_id)
    dados = conversation_manager.get_dados(remetente, grupo_id)

    logger.info(f"🔄 Processando resposta de conversa: '{texto}', estado: {estado}")

    if estado == ESTADO_AGUARDANDO_FORMA:
        if conversation_manager.is_forma_pagamento_valida(texto):
            forma = conversation_manager.normalizar_forma(texto)
            dados['forma_pagamento'] = forma
            if conversation_manager.eh_credito(forma):
                conversation_manager.set_estado(remetente, grupo_id, ESTADO_AGUARDANDO_PARCELAS, dados)
                return "Em quantas parcelas? (1 = à vista)"
            else:
                return await finalizar_transacao(remetente, grupo_id, dados)
        else:
            return "⚠️ Forma de pagamento inválida. Use: pix, credito, debito, dinheiro"

    elif estado == ESTADO_AGUARDANDO_PARCELAS:
        if conversation_manager.is_parcela_valida(texto):
            parcelas = int(texto)
            dados['parcelas'] = parcelas
            conversation_manager.set_estado(remetente, grupo_id, ESTADO_AGUARDANDO_DATA, dados)
            return "Qual a data do pagamento? (dd/mm/aaaa)"
        else:
            return "⚠️ Número de parcelas inválido. Digite um número (ex: 1, 2, 3...)"

    elif estado == ESTADO_AGUARDANDO_DATA:
        data_vencimento = conversation_manager.is_data_valida(texto)
        if data_vencimento:
            dados['data_vencimento'] = data_vencimento
            return await finalizar_transacao(remetente, grupo_id, dados)
        else:
            return "⚠️ Data inválida. Use o formato dd/mm/aaaa (ex: 10/08/2026)"

    return None


@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("✅ Banco de dados inicializado")


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

            if participant_alt:
                remetente = participant_alt.split("@")[0]
            elif participant:
                remetente = participant.split("@")[0]
            elif remote_jid:
                remetente = remote_jid.split("@")[0]
            else:
                logger.warning("🚫 Mensagem sem remetente (ignorada)")
                continue

            remetente = re.sub(r'[^0-9]', '', remetente)
            if not remetente:
                continue

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

            if not grupo_id:
                await enviar_mensagem(remetente, "⚠️ Use o grupo para registrar gastos.")
                return {"status": "success", "message": "Aviso enviado"}

            if texto.strip().startswith("/"):
                resposta = await processar_comando(remetente, grupo_id, texto)
                if resposta:
                    await enviar_mensagem(grupo_id, resposta)
                    return {"status": "success", "message": "Comando processado", "resposta": resposta}

            logger.info(f"🔍 Estado da conversa de {remetente}: {conversation_manager.get_estado(remetente, grupo_id)}")
            if conversation_manager.get_estado(remetente, grupo_id) != ESTADO_NORMAL:
                resposta = await processar_resposta_conversa(remetente, grupo_id, texto)
                if resposta:
                    await enviar_mensagem(grupo_id, resposta)
                    return {"status": "success", "message": "Conversa processada", "resposta": resposta}
                else:
                    conversation_manager.resetar(remetente, grupo_id)
                    await enviar_mensagem(grupo_id, "⚠️ Erro na conversa. Tente novamente.")
                    return {"status": "error", "message": "Erro na conversa"}

            async with AsyncSessionLocal() as session:
                usuario_repo = UsuarioRepository(session)
                await usuario_repo.get_or_create_by_telefone(remetente, grupo_id)

            dados_conversa = {'texto_original': texto}
            conversation_manager.set_estado(remetente, grupo_id, ESTADO_AGUARDANDO_FORMA, dados_conversa)
            await enviar_mensagem(grupo_id, "Qual a forma de pagamento? (pix, credito, debito, dinheiro)")
            return {"status": "success", "message": "Aguardando forma de pagamento"}

        return {"status": "success", "message": "Processado"}

    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/")
async def root():
    return {"message": "FinBot está rodando!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "finbot-webhook"}
