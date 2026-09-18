"""Configurações do FinBot carregadas por variáveis de ambiente."""

import os
from dotenv import load_dotenv


load_dotenv()


def require_env(name: str) -> str:
    """Retorna uma variável obrigatória ou interrompe a inicialização."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"A variável de ambiente {name} não foi configurada.")
    return value


EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080").rstrip("/")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "finbot")
DASHBOARD_PUBLIC_URL = os.getenv("DASHBOARD_PUBLIC_URL", "http://localhost:8000/dashboard")
