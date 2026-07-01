"""
webhook_receiver.py - Webhook mínimo do FinBot

Este é o ponto de entrada para mensagens do WhatsApp.
A Evolution API envia um POST para este endpoint toda vez
que alguém manda mensagem para seu número.
"""

from fastapi import FastAPI, Request
import logging

# 1. CRIAR APLICAÇÃO FASTAPI
# FastAPI() cria uma instância da aplicação.
# É como criar um restaurante vazio que vai receber pedidos.
app = FastAPI(title="FinBot Webhook")

# 2. CONFIGURAR LOGGING
# logging.basicConfig diz: mostre tudo que acontecer no terminal.
# level=logging.INFO significa: mostre informações, não só erros.
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 3. CRIAR ENDPOINT DO WEBHOOK
# @app.post() é um "decorator" que diz ao FastAPI:
# "quando alguém fizer um POST nesta URL, execute esta função".
# A URL completa será: http://localhost:8000/webhook/whatsapp

@app.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request):
    """
    Recebe mensagens do WhatsApp via Evolution API.
    
    Quando uma mensagem chega, a Evolution API envia um JSON
    com informações como: remetente, mensagem, etc.
    
    Parâmetros:
        request: objeto que contém a requisição HTTP (cabeçalhos, corpo)
    
    Retorna:
        Mensagem de confirmação pra Evolution API saber que recebeu.
    """
    
    # 3.1 Receber o corpo da requisição em formato JSON
    # request.json() lê o corpo da requisição e converte pra dicionário Python
    data = await request.json()
    
    # 3.2 Log da mensagem recebida
    # f"..." é f-string: permite colocar variáveis dentro do texto.
    logger.info(f"📩 Mensagem recebida: {data}")
    
    # 3.3 Responder para Evolution API
    # O FastAPI converte dicionário Python em JSON automaticamente.
    return {
        "status": "success",
        "message": "Webhook recebeu a mensagem!"
    }

# 4. ROTA DE TESTE (SAUDACAO)
# Rota pra você testar no navegador se o servidor está rodando.
@app.get("/")
async def root():
    """Rota de teste para verificar se o servidor está no ar."""
    return {"message": "FinBot está rodando!"}

# 5. ENDPOINT DE STATUS (PRA VERIFICAR SAUDE)
@app.get("/health")
async def health():
    """Rota de saúde para monitoramento."""
    return {"status": "healthy", "service": "finbot-webhook"}

# 6. EXPLICACAO SOBRE O ARQUIVO
# Quando você executa: uvicorn webhook_receiver:app --reload
# 
# "webhook_receiver"  → nome do arquivo (sem .py)
# ":app"              → nome da variável que contém a aplicação FastAPI
# "--reload"          → reinicia o servidor automaticamente quando você muda o código
