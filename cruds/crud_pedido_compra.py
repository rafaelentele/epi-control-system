"""
CRUD da tabela pedido_de_compra - o pedido de compra formal feito a
um fornecedor (produto, quantidade, valor unitário, data, observação).

A entrada de estoque passa a exigir um pedido de compra existente:
quando o material chega, você registra a entrada ligada a este
pedido, e o produto/fornecedor da entrada vêm automaticamente daqui
(evita registrar entrada de algo que nunca foi pedido).
"""

from datetime import date
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from app.config.database import get_session
from app.models.models import PedidoDeCompra, Produto, Fornecedor
from app.repositories.crud_auditoria import registrar_auditoria


def criar_pedido_compra(
    id_produto: int,
    quantidade: int,
    preco: float,
    id_fornecedor: int,
    data_compra: date = None,
    observacao: str | None = None,
) -> PedidoDeCompra:
    session = get_session()
    try:
        if int(quantidade) <= 0:
            raise ValueError("A quantidade do pedido deve ser maior que zero.")
        if session.get(Produto, id_produto) is None:
            raise ValueError(f"Produto com id {id_produto} não existe.")
        if session.get(Fornecedor, id_fornecedor) is None:
            raise ValueError(f"Fornecedor com id {id_fornecedor} não existe.")

        novo = PedidoDeCompra(
            id_produto=id_produto,
            quantidade=quantidade,
            preco=preco,
            id_fornecedor=id_fornecedor,
            data_compra=data_compra or date.today(),
            observacao=observacao,
        )
        session.add(novo)
        session.flush()
        registrar_auditoria(session, "CRIAÇÃO", "pedido_de_compra", f"Pedido de compra #{novo.id_pedido_compra} criado: {quantidade} unidade(s) do produto #{id_produto}.", id_registro=novo.id_pedido_compra)
        session.commit()
        session.refresh(novo)
        return novo
    finally:
        session.close()


def _query_com_relacionamentos(session):
    return session.query(PedidoDeCompra).options(
        joinedload(PedidoDeCompra.produto),
        joinedload(PedidoDeCompra.fornecedor),
    )


def listar_pedidos_compra() -> list[PedidoDeCompra]:
    session = get_session()
    try:
        return _query_com_relacionamentos(session).order_by(PedidoDeCompra.data_compra.desc()).all()
    finally:
        session.close()


def buscar_pedido_compra(id_pedido_compra: int) -> PedidoDeCompra | None:
    session = get_session()
    try:
        return (
            _query_com_relacionamentos(session)
            .filter(PedidoDeCompra.id_pedido_compra == id_pedido_compra)
            .first()
        )
    finally:
        session.close()


def atualizar_pedido_compra(
    id_pedido_compra: int,
    quantidade: int = None,
    preco: float = None,
    data_compra: date = None,
    observacao: str = None,
) -> PedidoDeCompra | None:
    session = get_session()
    try:
        pedido = session.get(PedidoDeCompra, id_pedido_compra)
        if pedido is None:
            return None
        if quantidade is not None:
            if int(quantidade) <= 0:
                raise ValueError("A quantidade do pedido deve ser maior que zero.")
            from app.models.models import Entrada
            total_recebido = session.query(func.coalesce(func.sum(Entrada.quantidade), 0)).filter(
                Entrada.id_pedido_compra == id_pedido_compra
            ).scalar() or 0
            if int(quantidade) < int(total_recebido):
                raise ValueError(
                    f"Não é possível reduzir o pedido para {quantidade} unidade(s), "
                    f"pois já foram recebidas {total_recebido}."
                )
            pedido.quantidade = quantidade
        if preco is not None:
            pedido.preco = preco
        if data_compra is not None:
            pedido.data_compra = data_compra
        if observacao is not None:
            pedido.observacao = observacao
        registrar_auditoria(session, "ALTERAÇÃO", "pedido_de_compra", f"Pedido de compra #{pedido.id_pedido_compra} alterado: quantidade={pedido.quantidade}, preço={pedido.preco}.", id_registro=pedido.id_pedido_compra)
        session.commit()
        session.refresh(pedido)
        return pedido
    finally:
        session.close()


def excluir_pedido_compra(id_pedido_compra: int) -> bool:
    session = get_session()
    try:
        pedido = session.get(PedidoDeCompra, id_pedido_compra)
        if pedido is None:
            return False
        id_registro=pedido.id_pedido_compra
        session.delete(pedido)
        registrar_auditoria(session, "EXCLUSÃO", "pedido_de_compra", f"Pedido de compra #{id_registro} excluído.", id_registro=id_registro)
        session.commit()
        return True
    finally:
        session.close()


def pesquisar_pedidos_compra(id_produto: int = None, id_fornecedor: int = None, id_pedido_compra: int = None) -> list[PedidoDeCompra]:
    """Pesquisa com filtros opcionais - qualquer combinação deles."""
    session = get_session()
    try:
        query = _query_com_relacionamentos(session)
        if id_pedido_compra is not None:
            query = query.filter(PedidoDeCompra.id_pedido_compra == id_pedido_compra)
        if id_produto is not None:
            query = query.filter(PedidoDeCompra.id_produto == id_produto)
        if id_fornecedor is not None:
            query = query.filter(PedidoDeCompra.id_fornecedor == id_fornecedor)
        return query.order_by(PedidoDeCompra.data_compra.desc()).all()
    finally:
        session.close()
