"""
conversation_manager.py - Gerencia estados de conversa do FinBot
"""

from datetime import datetime, timedelta
from typing import Optional, Dict

# Estados possíveis
ESTADO_AGUARDANDO_FORMA = "aguardando_forma"
ESTADO_AGUARDANDO_PARCELAS = "aguardando_parcelas"
ESTADO_AGUARDANDO_DATA = "aguardando_data"
ESTADO_NORMAL = "normal"

# Formas de pagamento válidas
FORMAS_PAGAMENTO = ["pix", "credito", "debito", "dinheiro"]

class ConversationManager:
    """Gerencia conversas com estado por (telefone, grupo_id).

    A chave é composta porque o mesmo telefone pode estar em vários
    grupos ao mesmo tempo. Sem isso, uma mensagem enviada no grupo B
    poderia ser interpretada como resposta de uma conversa pendente
    aberta no grupo A, misturando dados entre grupos.
    """

    def __init__(self):
        self.conversas: Dict[str, dict] = {}

    def _chave(self, telefone: str, grupo_id: str) -> str:
        return f"{telefone}:{grupo_id}"

    def get_estado(self, telefone: str, grupo_id: str) -> str:
        chave = self._chave(telefone, grupo_id)
        return self.conversas.get(chave, {}).get('estado', ESTADO_NORMAL)

    def get_dados(self, telefone: str, grupo_id: str) -> dict:
        chave = self._chave(telefone, grupo_id)
        return self.conversas.get(chave, {}).get('dados', {})

    def get_estado_completo(self, telefone: str, grupo_id: str) -> dict:
        """Retorna o estado completo da conversa para debug"""
        chave = self._chave(telefone, grupo_id)
        return self.conversas.get(chave, {})

    def set_estado(self, telefone: str, grupo_id: str, estado: str, dados: Optional[dict] = None):
        chave = self._chave(telefone, grupo_id)
        self.conversas[chave] = {
            'estado': estado,
            'dados': dados or {},
            'ultima_atualizacao': datetime.now()
        }

    def resetar(self, telefone: str, grupo_id: str):
        chave = self._chave(telefone, grupo_id)
        if chave in self.conversas:
            del self.conversas[chave]

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

    def timeout_expirado(self, telefone: str, grupo_id: str, timeout_minutos: int = 5) -> bool:
        chave = self._chave(telefone, grupo_id)
        dados = self.conversas.get(chave)
        if not dados:
            return False
        ultima = dados.get('ultima_atualizacao')
        if not ultima:
            return False
        return datetime.now() - ultima > timedelta(minutes=timeout_minutos)

conversation_manager = ConversationManager()
