"""
repositories.py - Camada de acesso a dados do FinBot
"""

from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List, Optional, Tuple

from database import Usuario, Categoria, Transacao


class UsuarioRepository:
    def __init__(self, session):
        self.session = session

    async def get_or_create_by_telefone(self, telefone: str, grupo_id: str) -> Usuario:
        stmt = select(Usuario).where(Usuario.telefone == telefone)
        result = await self.session.execute(stmt)
        usuario = result.scalar_one_or_none()

        if usuario:
            if usuario.grupo_id != grupo_id:
                usuario.grupo_id = grupo_id
                await self.session.commit()
                await self.session.refresh(usuario)
            return usuario

        usuario = Usuario(telefone=telefone, nome=None, grupo_id=grupo_id)
        self.session.add(usuario)
        await self.session.commit()
        await self.session.refresh(usuario)
        return usuario


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
        grupo_id: str,  # 🔧 NOVO: obrigatório
        data: Optional[datetime] = None
    ) -> Transacao:
        if data is None:
            data = datetime.now()

        transacao = Transacao(
            usuario_id=usuario_id,
            categoria_id=categoria_id,
            grupo_id=grupo_id,  # 🔧 NOVO
            valor=valor,
            descricao=descricao,
            tipo=tipo,
            data=data
        )
        self.session.add(transacao)
        await self.session.commit()
        await self.session.refresh(transacao)
        return transacao

    async def listar_por_usuario(
        self,
        usuario_id: int,
        periodo: Optional[Tuple[datetime, datetime]] = None
    ) -> List[Transacao]:
        stmt = select(Transacao).where(Transacao.usuario_id == usuario_id)
        stmt = stmt.options(
            selectinload(Transacao.categoria),
            selectinload(Transacao.usuario)
        )
        if periodo:
            data_inicio, data_fim = periodo
            stmt = stmt.where(and_(
                Transacao.data >= data_inicio,
                Transacao.data <= data_fim
            ))
        stmt = stmt.order_by(Transacao.data.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def listar_por_grupo(
        self,
        grupo_id: str,
        periodo: Optional[Tuple[datetime, datetime]] = None
    ) -> List[Transacao]:
        """Lista transações de um grupo específico (família ou motoristas)"""
        stmt = select(Transacao).where(Transacao.grupo_id == grupo_id)
        stmt = stmt.options(
            selectinload(Transacao.categoria),
            selectinload(Transacao.usuario)
        )
        if periodo:
            data_inicio, data_fim = periodo
            stmt = stmt.where(and_(
                Transacao.data >= data_inicio,
                Transacao.data <= data_fim
            ))
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

    async def total_por_grupo(self, grupo_id: str, periodo: Optional[Tuple[datetime, datetime]] = None) -> dict:
        transacoes = await self.listar_por_grupo(grupo_id, periodo)

        total_receitas = sum(t.valor for t in transacoes if t.tipo == 'R')
        total_despesas = sum(t.valor for t in transacoes if t.tipo == 'D')
        saldo = total_receitas - total_despesas

        return {
            'receitas': total_receitas,
            'despesas': total_despesas,
            'saldo': saldo
        }
