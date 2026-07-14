"""
webhook_receiver.py - Webhook do FinBot
Recebe mensagens do WhatsApp e processa com forma de pagamento e parcelamento
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import httpx
import re
import bcrypt
from jose import jwt
import os
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from sqlalchemy import select, and_, func

from database import AsyncSessionLocal, init_db, Usuario, Transacao, Mes
from repositories import (
    UsuarioRepository, 
    CategoriaRepository, 
    TransacaoRepository,
    MesRepository
)
from message_parser import extrair_info_mensagem
from conversation_manager import conversation_manager, ESTADO_AGUARDANDO_FORMA, ESTADO_AGUARDANDO_PARCELAS, ESTADO_AGUARDANDO_DATA, ESTADO_NORMAL

# ============================================================
# CONFIGURAÇÃO
# ============================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FinBot")

# 🔧 CONFIGURAÇÕES DA EVOLUTION API
INSTANCIA = "finbot"
API_KEY = "A606DD7229DA-4DCF-9856-91D2963A33F0"

# 🔧 JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "finbot_secret_key_change_this_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

# 🔧 TIMEOUT PARA RESPOSTA (em minutos)
TIMEOUT_MINUTOS = 5

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

# Cria a pasta static se não existir
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

# ============================================================
# FUNÇÕES DE AUTENTICAÇÃO JWT
# ============================================================

def criar_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def obter_usuario_por_email(email: str):
    async with AsyncSessionLocal() as session:
        stmt = select(Usuario).where(Usuario.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def obter_usuario_por_id(usuario_id: int):
    async with AsyncSessionLocal() as session:
        stmt = select(Usuario).where(Usuario.id == usuario_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: int = payload.get("sub")
        if usuario_id is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception

    usuario = await obter_usuario_por_id(usuario_id)
    if usuario is None:
        raise credentials_exception
    return usuario

# ============================================================
# API DO DASHBOARD
# ============================================================

@app.post("/api/login")
async def api_login(form_data: OAuth2PasswordRequestForm = Depends()):
    usuario = await obter_usuario_por_email(form_data.username)
    if not usuario:
        raise HTTPException(status_code=401, detail="Email inválido")

    if not bcrypt.checkpw(form_data.password.encode('utf-8'), usuario.senha_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Senha inválida")

    token = criar_token({"sub": str(usuario.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "grupo_id": usuario.grupo_id
        }
    }

@app.get("/api/transacoes")
async def api_transacoes(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    usuario: Usuario = Depends(get_current_user)
):
    async with AsyncSessionLocal() as session:
        transacao_repo = TransacaoRepository(session)
        
        if mes is None or ano is None:
            agora = datetime.now()
            mes = agora.month
            ano = agora.year
        
        transacoes = await transacao_repo.listar_por_grupo(usuario.grupo_id)
        
        resultado = []
        for t in transacoes:
            if t.data.month == mes and t.data.year == ano:
                resultado.append({
                    "id": t.id,
                    "valor": t.valor,
                    "descricao": t.descricao,
                    "tipo": t.tipo,
                    "categoria": t.categoria.nome if t.categoria else "Sem categoria",
                    "forma_pagamento": t.forma_pagamento,
                    "data": t.data.strftime("%d/%m/%Y"),
                    "parcelas": t.parcelas,
                    "parcela_atual": t.parcela_atual,
                })
        
        return resultado

@app.get("/api/resumo")
async def api_resumo(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    usuario: Usuario = Depends(get_current_user)
):
    async with AsyncSessionLocal() as session:
        if mes is None or ano is None:
            agora = datetime.now()
            mes = agora.month
            ano = agora.year
        
        transacao_repo = TransacaoRepository(session)
        transacoes = await transacao_repo.listar_por_grupo(usuario.grupo_id)
        
        total_receitas = 0
        total_despesas = 0
        categorias = {}
        
        for t in transacoes:
            if t.data.month == mes and t.data.year == ano:
                if t.tipo == 'R':
                    total_receitas += t.valor
                else:
                    total_despesas += t.valor
                    nome_cat = t.categoria.nome if t.categoria else "Sem categoria"
                    categorias[nome_cat] = categorias.get(nome_cat, 0) + t.valor
        
        return {
            "receitas": total_receitas,
            "despesas": total_despesas,
            "saldo": total_receitas - total_despesas,
            "categorias": [{"nome": k, "valor": v} for k, v in categorias.items()]
        }

@app.get("/api/evolucao")
async def api_evolucao(usuario: Usuario = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        transacao_repo = TransacaoRepository(session)
        transacoes = await transacao_repo.listar_por_grupo(usuario.grupo_id)
        
        meses = {}
        for t in transacoes:
            chave = f"{t.data.year}-{t.data.month:02d}"
            if chave not in meses:
                meses[chave] = {"receitas": 0, "despesas": 0}
            if t.tipo == 'R':
                meses[chave]["receitas"] += t.valor
            else:
                meses[chave]["despesas"] += t.valor
        
        chaves_ordenadas = sorted(meses.keys())
        return {
            "meses": chaves_ordenadas,
            "receitas": [meses[k]["receitas"] for k in chaves_ordenadas],
            "despesas": [meses[k]["despesas"] for k in chaves_ordenadas]
        }

@app.get("/api/me")
async def api_me(usuario: Usuario = Depends(get_current_user)):
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "grupo_id": usuario.grupo_id
    }

# ============================================================
# WEBHOOK DO WHATSAPP
# ============================================================

async def enviar_mensagem(telefone: str, texto: str):
    url = f"http://localhost:8080/message/sendText/{INSTANCIA}"
    payload = {"number": telefone, "text": texto}
    headers = {"apikey": API_KEY, "Content-Type": "application/json"}
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
        "❓ *Ajuda:*\n"
        "  `/ajuda` → Mostra esta mensagem\n\n"
        "💬 *\"A melhor maneira de prever o futuro é criá-lo.\"* — Peter Drucker"
    )

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

async def processar_resposta_conversa(remetente: str, grupo_id: str, texto: str) -> Optional[str]:
    estado = conversation_manager.get_estado(remetente)
    dados = conversation_manager.get_dados(remetente)

    if estado == ESTADO_AGUARDANDO_FORMA:
        if conversation_manager.is_forma_pagamento_valida(texto):
            forma = conversation_manager.normalizar_forma(texto)
            dados['forma_pagamento'] = forma
            if conversation_manager.eh_credito(forma):
                conversation_manager.set_estado(remetente, ESTADO_AGUARDANDO_PARCELAS, dados)
                return "Em quantas parcelas? (1 = à vista)"
            else:
                return await finalizar_transacao(remetente, grupo_id, dados)
        else:
            return "⚠️ Forma de pagamento inválida. Use: pix, credito, debito, dinheiro"

    elif estado == ESTADO_AGUARDANDO_PARCELAS:
        if conversation_manager.is_parcela_valida(texto):
            parcelas = int(texto)
            dados['parcelas'] = parcelas
            conversation_manager.set_estado(remetente, ESTADO_AGUARDANDO_DATA, dados)
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

async def finalizar_transacao(remetente: str, grupo_id: str, dados: dict) -> str:
    forma = dados.get('forma_pagamento')
    parcelas = dados.get('parcelas', 1)
    data_vencimento = dados.get('data_vencimento')
    texto = dados.get('texto_original', '')

    info = extrair_info_mensagem(texto)
    if info['valor'] is None:
        conversation_manager.resetar(remetente)
        return "⚠️ Erro: não consegui identificar o valor da transação."
    if info['categoria'] is None:
        conversation_manager.resetar(remetente)
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

    conversation_manager.resetar(remetente)
    return resposta

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

            if conversation_manager.get_estado(remetente) != ESTADO_NORMAL:
                resposta = await processar_resposta_conversa(remetente, grupo_id, texto)
                if resposta:
                    await enviar_mensagem(grupo_id, resposta)
                    return {"status": "success", "message": "Conversa processada", "resposta": resposta}
                else:
                    conversation_manager.resetar(remetente)
                    await enviar_mensagem(grupo_id, "⚠️ Erro na conversa. Tente novamente.")
                    return {"status": "error", "message": "Erro na conversa"}

            async with AsyncSessionLocal() as session:
                usuario_repo = UsuarioRepository(session)
                await usuario_repo.get_or_create_by_telefone(remetente, grupo_id)

            dados_conversa = {'texto_original': texto}
            conversation_manager.set_estado(remetente, ESTADO_AGUARDANDO_FORMA, dados_conversa)
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
