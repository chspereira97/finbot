"""
message_parser.py - Extrai informações de mensagens em linguagem natural
"""

import re
from datetime import datetime, timedelta

PALAVRAS_DATA = {'hoje', 'ontem', 'amanhã', 'agora'}


def extrair_valor(texto):
    """Extrai o valor de um texto. Suporta: 25,50 / 25.50 / R$ 25,50 / 25 reais"""
    texto = texto.strip()

    # Padrões de valor (do mais específico ao mais genérico)
    padroes = [
        r'R?\$?\s*(\d+[\.,]\d{2})',     # R$ 25,50 ou 25.50
        r'R?\$?\s*(\d+)\s*reais?',       # 25 reais
        r'(\d+[\.,]\d{2})\s*reais?',     # 25,50 reais
        r'\b(\d+[\.,]\d{2})\b',          # 25,50 isolado
        r'\b(\d+)\s*(?:reais?)?$',       # 25 no final
        r'\b(\d+)\s*(?:reais?)?\b',      # 25 no meio
    ]

    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            valor_str = match.group(1).replace(',', '.')
            try:
                return float(valor_str)
            except:
                continue
    return None


def extrair_categoria(texto):
    """Extrai a categoria de um texto."""
    # Remove valores
    texto_limpo = re.sub(r'R?\$?\s*\d+[\.,]\d{2}', '', texto, flags=re.IGNORECASE)
    texto_limpo = re.sub(r'\d+\s*reais?', '', texto_limpo, flags=re.IGNORECASE)
    texto_limpo = re.sub(r'\b\d+\b', '', texto_limpo)

    # Remove palavras comuns que não são categorias
    palavras_ignorar = [
        r'\bganhei\b', r'\bgastei\b', r'\brecebi\b',
        r'\bpaguei\b', r'\bcomprei\b', r'\bhoje\b',
        r'\bontem\b', r'\bamanhã\b', r'\bna\b', r'\bno\b',
        r'\bda\b', r'\bdo\b', r'\bde\b', r'\bpara\b'
    ]
    for palavra in palavras_ignorar:
        texto_limpo = re.sub(palavra, '', texto_limpo, flags=re.IGNORECASE)

    # Remove datas
    texto_limpo = re.sub(r'\d{2}[/.]\d{2}[/.]\d{2,4}', '', texto_limpo)

    texto_limpo = texto_limpo.strip()
    if not texto_limpo:
        return None

    # Pega a primeira palavra que não é data
    palavras = texto_limpo.split()
    for palavra in palavras:
        palavra_limpa = palavra.strip().capitalize()
        palavra_limpa = re.sub(r'[^\w\s]', '', palavra_limpa)
        if palavra_limpa and palavra_limpa.lower() not in PALAVRAS_DATA:
            return palavra_limpa

    return None


def extrair_data(texto):
    """Extrai uma data de um texto."""
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    texto_lower = texto.lower()
    if 'hoje' in texto_lower:
        return hoje
    if 'ontem' in texto_lower:
        return hoje - timedelta(days=1)
    if 'amanhã' in texto_lower:
        return hoje + timedelta(days=1)

    padrao_data = r'(\d{2})[/.](\d{2})[/.](\d{2,4})'
    match = re.search(padrao_data, texto)
    if match:
        dia, mes, ano = match.groups()
        dia, mes = int(dia), int(mes)
        ano = int(ano)
        if ano < 100:
            ano += 2000
        try:
            return datetime(ano, mes, dia)
        except:
            pass
    return None


def classificar_tipo(texto):
    """Classifica uma mensagem como receita (R) ou despesa (D)."""
    texto = texto.lower()

    receita_palavras = ['recebi', 'ganhei', 'salário', 'salario', 'entrada', 'depósito', 'deposito']
    for palavra in receita_palavras:
        if palavra in texto:
            return 'R'

    # Se tem valor, assume despesa (padrão)
    if extrair_valor(texto) is not None:
        return 'D'

    return 'D'


def extrair_info_mensagem(texto):
    """Extrai todas as informações de uma mensagem."""
    return {
        'valor': extrair_valor(texto),
        'categoria': extrair_categoria(texto),
        'data': extrair_data(texto),
        'tipo': classificar_tipo(texto)
    }
