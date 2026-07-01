## 📌 Situação Atual do Projeto

**Etapa 0 - Infraestrutura Base** ✅ Concluída

Nesta etapa, foram estabelecidas as bases do sistema, garantindo a comunicação entre o WhatsApp e o webhook do FinBot.

### O que foi feito:

- **Webhook FastAPI** criado para receber mensagens do WhatsApp.
- **Evolution API** configurada via Docker com PostgreSQL e Redis.
- **Túnel Cloudflared** ativo para expor o webhook publicamente.
- **Serviços rodando em background** com `nohup`.
- **Repositório Git** inicializado e conectado ao GitHub.
- **Documentação inicial** organizada no Notion.

### Status atual:

- ✅ Webhook rodando em `http://localhost:8000`
- ✅ Evolution API acessível em `http://IP_DO_SERVIDOR:8080/manager`
- ✅ WhatsApp conectado e recebendo mensagens
- ✅ Logs sendo gerados (`webhook.log`, `tunnel.log`)

### Próximos passos:

- ⬜ Etapa 1 - Banco de Dados (SQLite + SQLAlchemy)
- ⬜ Etapa 2 - Parser de Mensagens
- ⬜ Etapa 3 - Webhook Integrado
- ⬜ Etapa 4 - Comandos
- ⬜ Etapa 5 - Relatórios
- ⬜ Etapa 6 - Dashboard
- ⬜ Etapa 7 - Backup e Polimento


   tail -f ~/finbot/webhook.log
