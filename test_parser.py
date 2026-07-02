"""
test_parser.py - Testa as funções do message_parser
"""

from message_parser import extrair_valor, extrair_categoria, extrair_data, classificar_tipo, extrair_info_mensagem

print("=" * 50)
print("🧪 TESTANDO PARSER")
print("=" * 50)

mensagens = [
    "padaria 25,50",
    "uber 15.00",
    "salário 2500",
    "recebi 1000 reais",
    "gastei 50 na farmácia",
    "comprei pão na padaria 15,00",
    "25,50",
    "alimentação 30,00 hoje",
    "ganhei 200 ontem",
    "hoje paguei 45 no mercado",
    "10/05/2025 aluguel 1200",
]

print("\n📩 Testando extração de informações:\n")

for msg in mensagens:
    info = extrair_info_mensagem(msg)
    print(f"Mensagem: {msg}")
    print(f"  Valor:   R$ {info['valor']:.2f}" if info['valor'] else "  Valor:   ❌ Não encontrado")
    print(f"  Categoria: {info['categoria']}" if info['categoria'] else "  Categoria: ❌ Não encontrada")
    print(f"  Data:    {info['data'].strftime('%d/%m/%Y')}" if info['data'] else "  Data:    ❌ Não encontrada")
    print(f"  Tipo:    {'Receita' if info['tipo'] == 'R' else 'Despesa'}")
    print("-" * 40)
