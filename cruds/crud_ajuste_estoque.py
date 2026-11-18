"""Operações de ajuste de estoque físico, com histórico e auditoria."""
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.config.database import get_session
from app.models.models import AjusteEstoque, Entrada, Saida, Produto, Tamanho, Usuario
from app.repositories.crud_auditoria import registrar_auditoria


def saldo_produto_tamanho(id_produto: int, id_tamanho: int) -> int:
    session = get_session()
    try:
        return _saldo(session, id_produto, id_tamanho)
    finally:
        session.close()


def _saldo(session, id_produto, id_tamanho):
    entrada = session.query(func.coalesce(func.sum(Entrada.quantidade), 0)).filter(Entrada.id_produto == id_produto, Entrada.id_tamanho == id_tamanho).scalar() or 0
    saida = session.query(func.coalesce(func.sum(Saida.quantidade), 0)).filter(Saida.id_produto == id_produto, Saida.id_tamanho == id_tamanho).scalar() or 0
    ajuste = session.query(func.coalesce(func.sum(AjusteEstoque.quantidade_ajuste), 0)).filter(AjusteEstoque.id_produto == id_produto, AjusteEstoque.id_tamanho == id_tamanho).scalar() or 0
    return int(entrada) - int(saida) + int(ajuste)


def criar_ajuste(id_produto: int, id_tamanho: int, quantidade_fisica: int, motivo: str, observacao: str | None, id_usuario: int):
    if int(quantidade_fisica) < 0:
        raise ValueError("A quantidade física não pode ser negativa.")
    if not motivo or not motivo.strip():
        raise ValueError("Informe o motivo do ajuste.")
    session = get_session()
    try:
        produto = session.query(Produto).filter(Produto.id_produto == id_produto).with_for_update().first()
        tamanho = session.get(Tamanho, id_tamanho)
        if produto is None:
            raise ValueError("Produto não encontrado.")
        if tamanho is None:
            raise ValueError("Tamanho não encontrado.")
        if session.get(Usuario, id_usuario) is None:
            raise ValueError("Usuário não encontrado.")
        anterior = _saldo(session, id_produto, id_tamanho)
        posterior = int(quantidade_fisica)
        delta = posterior - anterior
        if delta == 0:
            raise ValueError("A quantidade física é igual ao estoque atual. Nenhum ajuste é necessário.")
        ajuste = AjusteEstoque(id_produto=id_produto, id_tamanho=id_tamanho, quantidade_ajuste=delta, estoque_anterior=anterior, estoque_posterior=posterior, motivo=motivo.strip(), observacao=(observacao or '').strip() or None, id_usuario=id_usuario)
        session.add(ajuste)
        session.flush()
        registrar_auditoria(session, "AJUSTE", "ajuste_estoque", f"Ajuste #{ajuste.id_ajuste}: {produto.nome}, tamanho {tamanho.nome}; estoque {anterior} -> {posterior}; diferença {delta:+d}; motivo: {motivo.strip()}." + (f" Observação: {observacao.strip()}" if observacao and observacao.strip() else ""), id_registro=ajuste.id_ajuste, id_usuario=id_usuario)
        session.commit(); session.refresh(ajuste)
        return ajuste
    except Exception:
        session.rollback(); raise
    finally:
        session.close()


def listar_ajustes(limite=200):
    session=get_session()
    try:
        return session.query(AjusteEstoque).options(joinedload(AjusteEstoque.produto), joinedload(AjusteEstoque.tamanho), joinedload(AjusteEstoque.usuario)).order_by(AjusteEstoque.data_ajuste.desc()).limit(limite).all()
    finally: session.close()
