"""
repositories.py - Camada de acesso a dados do FinBot
"""

from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List, Optional, Tuple
import secrets

from database import Usuario, Categoria, Transacao, Mes, AcessoGrupo


class UsuarioRepository:
    def __init__(self, session):
        self.session = session

    async def get_or_create_by_telefone(self, telefone: str, grupo_id: str) -> Usuario:
        """Busca usuário pelo telefone. Se não existir, cria com chaves automáticas."""
        stmt = select(Usuario).where(Usuario.telefone == telefone)
        result = await self.session.execute(stmt)
        usuario = result.scalar_one_or_none()

        if usuario:
            # Não sobrescreve mais o grupo_id do usuário a cada mensagem.
            # O grupo_id correto de cada operação já vem como parâmetro
            # explícito em cada comando/consulta.
            return usuario

        usuario = Usuario(
            telefone=telefone,
            nome=None,
            grupo_id=grupo_id,
            chave_login=None,
            chave_senha=None
        )
        self.session.add(usuario)
        await self.session.commit()
        await self.session.refresh(usuario)
        return usuario

    async def get_or_create_acesso(self, usuario_id: int, grupo_id: str) -> AcessoGrupo:
        """Busca ou cria um acesso para o usuário em um grupo específico"""
        stmt = select(AcessoGrupo).where(
            AcessoGrupo.usuario_id == usuario_id,
            AcessoGrupo.grupo_id == grupo_id
        )
        result = await self.session.execute(stmt)
        acesso = result.scalar_one_or_none()

        if acesso:
            return acesso

        chave_login = secrets.token_hex(4).upper()
        chave_senha = secrets.token_hex(4).upper()
        
        acesso = AcessoGrupo(
            usuario_id=usuario_id,
            grupo_id=grupo_id,
            chave_login=chave_login,
            chave_senha=chave_senha
        )
        self.session.add(acesso)
        await self.session.commit()
        await self.session.refresh(acesso)
        return acesso


class CategoriaRepository:
    def __init__(self, session):
        self.session = session

    async def get_or_create_by_nome(self, nome: str, tipo: str, usuario_id: int) -> Categoria:
        stmt = select(Categoria).where(
            and_(
                func.lower(Categoria.nome) == nome.lower(),
                Categoria.usuario_id == usuario_id
            )
        )
        result = await self.session.execute(stmt)
        categoria = result.scalar_one_or_none()

        if categoria:
            return categoria

        categoria = Categoria(nome=nome.capitalize(), tipo=tipo, usuario_id=usuario_id)
        self.session.add(categoria)
        await self.session.commit()
        await self.session.refresh(categoria)
        return categoria

    async def listar_todas(self, usuario_id: int) -> List[Categoria]:
        stmt = select(Categoria).where(Categoria.usuario_id == usuario_id).order_by(Categoria.nome)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class TransacaoRepository:
    def __init__(self, session):
        self.session = session

    async def criar(
        self,
        usuario_id: int,
        categoria_id: int,
        valor: float,
        descricao: str,
        tipo: str,
        grupo_id: str,
        mes_id: int,
        forma_pagamento: Optional[str] = None,
        parcelas: Optional[int] = None,
        parcela_atual: Optional[int] = None,
        data_vencimento: Optional[datetime] = None,
        transacao_original_id: Optional[int] = None,
        data: Optional[datetime] = None
    ) -> Transacao:
        if data is None:
            data = datetime.now()

        transacao = Transacao(
            usuario_id=usuario_id,
            categoria_id=categoria_id,
            mes_id=mes_id,
            grupo_id=grupo_id,
            forma_pagamento=forma_pagamento,
            parcelas=parcelas,
            parcela_atual=parcela_atual,
            data_vencimento=data_vencimento,
            transacao_original_id=transacao_original_id,
            valor=valor,
            descricao=descricao,
            tipo=tipo,
            data=data
        )
        self.session.add(transacao)
        await self.session.commit()
        await self.session.refresh(transacao)
        return transacao

    async def listar_por_grupo(
        self,
        grupo_id: str,
        periodo: Optional[Tuple[datetime, datetime]] = None,
        mes_id: Optional[int] = None
    ) -> List[Transacao]:
        stmt = select(Transacao).where(Transacao.grupo_id == grupo_id)
        
        if mes_id:
            stmt = stmt.where(Transacao.mes_id == mes_id)
        
        if periodo:
            data_inicio, data_fim = periodo
            stmt = stmt.where(and_(
                Transacao.data >= data_inicio,
                Transacao.data <= data_fim
            ))
        
        stmt = stmt.options(
            selectinload(Transacao.categoria),
            selectinload(Transacao.usuario)
        )
        stmt = stmt.order_by(Transacao.data.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def deletar(self, transacao_id: int) -> bool:
        stmt = select(Transacao).where(Transacao.id == transacao_id)
        result = await self.session.execute(stmt)
        transacao = result.scalar_one_or_none()

        if not transacao:
            return False

        await self.session.delete(transacao)
        await self.session.commit()
        return True

    async def total_por_grupo(self, grupo_id: str, mes_id: Optional[int] = None) -> dict:
        transacoes = await self.listar_por_grupo(grupo_id, mes_id=mes_id)

        total_receitas = sum(t.valor for t in transacoes if t.tipo == 'R')
        total_despesas = sum(t.valor for t in transacoes if t.tipo == 'D')
        saldo = total_receitas - total_despesas

        return {
            'receitas': total_receitas,
            'despesas': total_despesas,
            'saldo': saldo
        }


class MesRepository:
    def __init__(self, session):
        self.session = session

    async def get_or_create_mes_atual(self, grupo_id: str) -> Mes:
        agora = datetime.now()
        mes = agora.month
        ano = agora.year

        stmt = select(Mes).where(
            Mes.mes == mes,
            Mes.ano == ano,
            Mes.grupo_id == grupo_id
        )
        result = await self.session.execute(stmt)
        mes_obj = result.scalar_one_or_none()

        if mes_obj:
            return mes_obj

        mes_obj = Mes.criar_para_grupo(grupo_id)
        self.session.add(mes_obj)
        await self.session.commit()
        await self.session.refresh(mes_obj)
        return mes_obj
