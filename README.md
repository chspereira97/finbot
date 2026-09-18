# FinBot

Assistente financeiro integrado ao WhatsApp para registrar receitas e despesas por mensagens, acompanhar o saldo e consultar relatórios em um painel web.

## Sobre o projeto

O FinBot transforma mensagens simples, como `padaria 25,50`, em registros financeiros organizados. O sistema identifica valor, categoria, tipo de transação e data, mantém os dados separados por grupo e disponibiliza consultas pelo WhatsApp e pelo dashboard.

Este projeto foi desenvolvido como aplicação prática de automação, APIs, banco de dados e desenvolvimento web.

## Funcionalidades

- Registro de receitas e despesas pelo WhatsApp
- Classificação automática de transações
- Controle de compras parceladas
- Resumos mensais e consulta de saldo
- Histórico das últimas transações
- Edição e exclusão de lançamentos
- Relatórios diários e semanais
- Lembretes de inatividade
- Dashboard web com autenticação
- Separação dos dados por grupo

## Tecnologias

- Python e FastAPI
- SQLAlchemy e SQLite
- Evolution API
- PostgreSQL e Redis para a infraestrutura da Evolution API
- Docker Compose
- HTML, CSS, JavaScript, Bootstrap e Chart.js
- Autenticação com JWT

## Arquitetura resumida

1. O WhatsApp encaminha os eventos para a Evolution API.
2. A Evolution API envia os eventos ao webhook do FinBot.
3. O FinBot interpreta a mensagem e grava a transação no banco de dados.
4. O usuário recebe a resposta pelo WhatsApp e pode consultar os dados no dashboard.

## Como executar localmente

### 1. Clone o projeto

```bash
git clone https://github.com/chspereira97/finbot.git
cd finbot
```

### 2. Crie o ambiente virtual e instale as dependências

```bash
python -m venv .venv
```

No Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

No Linux ou macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

Copie `.env.example` para `.env` e substitua os valores de exemplo:

```bash
cp .env.example .env
```

Para gerar um segredo JWT seguro:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> O arquivo `.env` contém informações sensíveis e não deve ser enviado ao GitHub.

### 4. Inicie a infraestrutura da Evolution API

```bash
docker compose up -d
```

### 5. Inicie o FinBot

```bash
uvicorn webhook_receiver:app --host 0.0.0.0 --port 8000 --reload
```

Serviços locais:

- API e status: `http://localhost:8000`
- Dashboard: `http://localhost:8000/dashboard`
- Documentação interativa: `http://localhost:8000/docs`
- Evolution API: `http://localhost:8080`

## Comandos do WhatsApp

| Comando | Função |
|---|---|
| `/total` | Exibe receitas, despesas e saldo do mês |
| `/resumo` | Mostra o resumo mensal por categoria |
| `/ultimos 5` | Lista as últimas transações |
| `/editar ID VALOR` | Altera o valor de uma transação |
| `/apagar ID` | Exclui uma transação |
| `/meu_nome NOME` | Define o nome do usuário |
| `/chaves` | Exibe as chaves de acesso ao dashboard |
| `/chaves_renovar` | Gera novas chaves de acesso |
| `/ajuda` | Mostra os comandos disponíveis |

## Segurança

- Chaves, senhas e URLs privadas são carregadas por variáveis de ambiente.
- O arquivo `.env` está protegido pelo `.gitignore`.
- O repositório disponibiliza apenas o modelo seguro `.env.example`.
- Credenciais que já tenham sido publicadas devem ser revogadas e substituídas.

## Status

Projeto em desenvolvimento. Melhorias planejadas incluem testes automatizados, migrações de banco de dados, implantação em nuvem e ampliação dos relatórios.

## Autor

**Carlos Pereira**

- [LinkedIn](https://www.linkedin.com/in/carlos-pereira1997/)
- [GitHub](https://github.com/chspereira97)
