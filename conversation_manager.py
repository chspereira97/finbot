"""
conversation_manager.py - Gerencia estados de conversa do FinBot
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import asyncio

# Estados possíveis
ESTADO_AGUARDANDO_FORMA = "aguardando_forma"
ESTADO_AGUARDANDO_PARCELAS = "aguardando_parcelas"
ESTADO_AGUARDANDO_DATA = "aguardando_data"
ESTADO_NORMAL = "normal"

# Formas de pagamento válidas
FORMAS_PAGAMENTO = ["pix", "credito", "debito", "dinheiro"]

class ConversationManager:
    """Gerencia conversas com estado por telefone"""

    def __init__(self):
        self.conversas: Dict[str, dict] = {}

    def get_estado(self, telefone: str) -> str:
        return self.conversas.get(telefone, {}).get('estado', ESTADO_NORMAL)

    def get_dados(self, telefone: str) -> dict:
        return self.conversas.get(telefone, {}).get('dados', {})

    def set_estado(self, telefone: str, estado: str, dados: Optional[dict] = None):
        self.conversas[telefone] = {
            'estado': estado,
            'dados': dados or {},
            'ultima_atualizacao': datetime.now()
        }

    def resetar(self, telefone: str):
        if telefone in self.conversas:
            del self.conversas[telefone]

    def is_forma_pagamento_valida(self, texto: str) -> bool:
        return texto.lower() in FORMAS_PAGAMENTO

    def normalizar_forma(self, texto: str) -> str:
        return texto.lower()

    def eh_credito(self, forma: str) -> bool:
        return forma.lower() == "credito"

    def is_parcela_valida(self, texto: str) -> bool:
        try:
            n = int(texto)
            return n >= 1
        except ValueError:
            return False

    def is_data_valida(self, texto: str) -> Optional[datetime]:
        try:
            return datetime.strptime(texto, "%d/%m/%Y")
        except ValueError:
            return None

    def timeout_expirado(self, telefone: str, timeout_minutos: int = 5) -> bool:
        dados = self.conversas.get(telefone)
        if not dados:
            return False
        ultima = dados.get('ultima_atualizacao')
        if not ultima:
            return False
        return datetime.now() - ultima > timedelta(minutes=timeout_minutos)

conversation_manager = ConversationManager()
