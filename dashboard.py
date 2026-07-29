"""
dashboard.py - API para o dashboard do FinBot
Autenticação JWT e endpoints protegidos
"""

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, and_, func
from datetime import datetime, timedelta
from typing import Optional, List
import bcrypt
import jwt
import os

from database import AsyncSessionLocal, Usuario, Transacao, Categoria
from repositories import TransacaoRepository, CategoriaRepository

# Configuração JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "finbot_secret_key_change_this_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

app = FastAPI(title="FinBot Dashboard API", prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# FUNÇÕES DE AUTENTICAÇÃO
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
# ENDPOINTS
# ============================================================

@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
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
async def get_transacoes(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    categoria: Optional[str] = None,
    forma_pagamento: Optional[str] = None,
    tipo: Optional[str] = None,
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
            if t.data.month != mes or t.data.year != ano:
                continue
            
            if categoria:
                nome_cat = t.categoria.nome if t.categoria else "Sem categoria"
                if categoria.lower() not in nome_cat.lower():
                    continue
            
            if forma_pagamento:
                if t.forma_pagamento != forma_pagamento:
                    continue
            
            if tipo:
                if t.tipo != tipo:
                    continue
            
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
async def get_resumo(
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
        formas_pagamento = {}
        
        for t in transacoes:
            if t.data.month == mes and t.data.year == ano:
                if t.tipo == 'R':
                    total_receitas += t.valor
                else:
                    total_despesas += t.valor
                    nome_cat = t.categoria.nome if t.categoria else "Sem categoria"
                    categorias[nome_cat] = categorias.get(nome_cat, 0) + t.valor
                
                forma = t.forma_pagamento or "Não informado"
                formas_pagamento[forma] = formas_pagamento.get(forma, 0) + t.valor
        
        return {
            "receitas": total_receitas,
            "despesas": total_despesas,
            "saldo": total_receitas - total_despesas,
            "categorias": [{"nome": k, "valor": v} for k, v in categorias.items()],
            "formas_pagamento": [{"nome": k, "valor": v} for k, v in formas_pagamento.items()]
        }


@app.get("/api/evolucao")
async def get_evolucao(usuario: Usuario = Depends(get_current_user)):
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


@app.get("/api/categorias")
async def get_categorias(usuario: Usuario = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        stmt = select(Categoria).where(Categoria.usuario_id == usuario.id).order_by(Categoria.nome)
        result = await session.execute(stmt)
        categorias = result.scalars().all()
        return [{"id": c.id, "nome": c.nome, "tipo": c.tipo} for c in categorias]


@app.put("/api/transacoes/{transacao_id}")
async def update_transacao(
    transacao_id: int,
    dados: dict,
    usuario: Usuario = Depends(get_current_user)
):
    async with AsyncSessionLocal() as session:
        stmt = select(Transacao).where(
            Transacao.id == transacao_id,
            Transacao.usuario_id == usuario.id
        )
        result = await session.execute(stmt)
        transacao = result.scalar_one_or_none()
        
        if not transacao:
            raise HTTPException(status_code=404, detail="Transação não encontrada")
        
        if 'valor' in dados:
            transacao.valor = dados['valor']
        if 'descricao' in dados:
            transacao.descricao = dados['descricao']
        if 'categoria' in dados:
            categoria_repo = CategoriaRepository(session)
            categoria = await categoria_repo.get_or_create_by_nome(
                dados['categoria'],
                transacao.tipo,
                usuario.id
            )
            transacao.categoria_id = categoria.id
        if 'data' in dados:
            try:
                transacao.data = datetime.strptime(dados['data'], "%d/%m/%Y")
            except:
                pass
        if 'forma_pagamento' in dados:
            transacao.forma_pagamento = dados['forma_pagamento']
        
        await session.commit()
        await session.refresh(transacao)
        
        return {
            "id": transacao.id,
            "valor": transacao.valor,
            "descricao": transacao.descricao,
            "categoria": transacao.categoria.nome if transacao.categoria else "Sem categoria",
            "data": transacao.data.strftime("%d/%m/%Y"),
            "forma_pagamento": transacao.forma_pagamento
        }


@app.delete("/api/transacoes/{transacao_id}")
async def delete_transacao(
    transacao_id: int,
    usuario: Usuario = Depends(get_current_user)
):
    async with AsyncSessionLocal() as session:
        stmt = select(Transacao).where(
            Transacao.id == transacao_id,
            Transacao.usuario_id == usuario.id
        )
        result = await session.execute(stmt)
        transacao = result.scalar_one_or_none()
        
        if not transacao:
            raise HTTPException(status_code=404, detail="Transação não encontrada")
        
        await session.delete(transacao)
        await session.commit()
        
        return {"message": "Transação apagada com sucesso"}


@app.get("/api/me")
async def get_me(usuario: Usuario = Depends(get_current_user)):
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "grupo_id": usuario.grupo_id
    }

@app.post("/api/register")
async def register(
    nome: str,
    email: str,
    senha: str,
    codigo_convite: str
):
    """Cadastra um novo usuário usando um código de convite"""
    async with AsyncSessionLocal() as session:
        # Verifica se o email já existe
        stmt = select(Usuario).where(Usuario.email == email)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email já cadastrado")
        
        # Verifica se o código de convite existe
        stmt = select(Usuario).where(Usuario.codigo_convite == codigo_convite)
        result = await session.execute(stmt)
        usuario_convidante = result.scalar_one_or_none()
        
        if not usuario_convidante:
            raise HTTPException(status_code=400, detail="Código de convite inválido")
        
        # Cria o novo usuário com o mesmo grupo_id
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        novo_usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=senha_hash,
            grupo_id=usuario_convidante.grupo_id
        )
        session.add(novo_usuario)
        await session.commit()
        await session.refresh(novo_usuario)
        
        return {"message": "Usuário cadastrado com sucesso!"}
