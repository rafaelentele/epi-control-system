"""
CRUD da tabela entrada (chegada de fardamento no estoque).

Desde esta versão, toda entrada precisa estar ligada a um
pedido_de_compra já existente - o produto e o fornecedor da entrada
vêm automaticamente do pedido (não são escolhidos de novo aqui).
Isso evita registrar entrada de algo que nunca foi pedido.

O que ainda é específico da entrada: tamanho e quantidade recebida
(um mesmo pedido de compra pode virar várias entradas, uma pra cada
tamanho que chegou).
"""

from datetime import date
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from app.config.database import get_session
from app.models.models import Entrada, Tamanho, Usuario, PedidoDeCompra
from app.repositories.crud_auditoria import registrar_auditoria
from app.auth import obter_usuario_atual


def criar_entrada(
    id_pedido_compra: int,
    id_tamanho: int,
    quantidade: int,
    id_usuario: int,
    data_entrada: date = None,
    observacao: str | None = None,
) -> Entrada:
    session = get_session()
    try:
        usuario_atual = obter_usuario_atual()
        if usuario_atual:
            id_usuario = usuario_atual["id_usuario"]

        if int(quantidade) <= 0:
            raise ValueError("A quantidade da entrada deve ser maior que zero.")
        # Bloqueia o pedido durante a conferência para evitar que dois
        # computadores registrem simultaneamente uma quantidade acima do
        # total comprado. Requer tabela transacional (ex.: InnoDB no MySQL).
        pedido = (
            session.query(PedidoDeCompra)
            .filter(PedidoDeCompra.id_pedido_compra == id_pedido_compra)
            .with_for_update()
            .first()
        )
        if pedido is None:
            raise ValueError(f"Pedido de compra com id {id_pedido_compra} não existe.")

        total_recebido = session.query(func.coalesce(func.sum(Entrada.quantidade), 0)).filter(
            Entrada.id_pedido_compra == id_pedido_compra
        ).scalar() or 0
        restante = int(pedido.quantidade) - int(total_recebido)
        if int(quantidade) > restante:
            raise ValueError(
                f"Quantidade acima do pedido. Pedido #{pedido.id_pedido_compra}: "
                f"comprado {pedido.quantidade}, já recebido {total_recebido}, "
                f"restante {max(restante, 0)}."
            )
        if session.get(Tamanho, id_tamanho) is None:
            raise ValueError(f"Tamanho com id {id_tamanho} não existe.")
        if session.get(Usuario, id_usuario) is None:
            raise ValueError(f"Usuário com id {id_usuario} não existe.")

        nova = Entrada(
            id_produto=pedido.id_produto,
            id_fornecedor=pedido.id_fornecedor,
            id_pedido_compra=id_pedido_compra,
            id_tamanho=id_tamanho,
            quantidade=quantidade,
            id_usuario=id_usuario,
            data_entrada=data_entrada or date.today(),
            observacao=observacao,
        )
        session.add(nova)
        session.flush()
        registrar_auditoria(session, "ENTRADA", "entrada", f"Entrada de {quantidade} unidade(s) no pedido #{id_pedido_compra}.", id_registro=nova.id_entrada, id_usuario=id_usuario)
        session.commit()
        session.refresh(nova)
        return nova
    finally:
        session.close()


def _query_com_relacionamentos(session):
    return session.query(Entrada).options(
        joinedload(Entrada.produto),
        joinedload(Entrada.tamanho),
        joinedload(Entrada.fornecedor),
        joinedload(Entrada.usuario),
        joinedload(Entrada.pedido_compra),
    )


def listar_entradas() -> list[Entrada]:
    session = get_session()
    try:
        return _query_com_relacionamentos(session).order_by(Entrada.data_entrada.desc()).all()
    finally:
        session.close()


def buscar_entrada(id_entrada: int) -> Entrada | None:
    session = get_session()
    try:
        return _query_com_relacionamentos(session).filter(Entrada.id_entrada == id_entrada).first()
    finally:
        session.close()


def atualizar_entrada(
    id_entrada: int,
    quantidade: int = None,
    id_tamanho: int = None,
    data_entrada: date = None,
    observacao: str = None,
) -> Entrada | None:
    session = get_session()
    try:
        entrada = session.get(Entrada, id_entrada)
        if entrada is None:
            return None

        pedido = None
        if entrada.id_pedido_compra is not None:
            pedido = (
                session.query(PedidoDeCompra)
                .filter(PedidoDeCompra.id_pedido_compra == entrada.id_pedido_compra)
                .with_for_update()
                .first()
            )

        if id_tamanho is not None:
            if session.get(Tamanho, id_tamanho) is None:
                raise ValueError(f"Tamanho com id {id_tamanho} não existe.")
            entrada.id_tamanho = id_tamanho

        if quantidade is not None:
            if int(quantidade) <= 0:
                raise ValueError("A quantidade da entrada deve ser maior que zero.")
            if pedido is not None:
                total_outras_entradas = session.query(
                    func.coalesce(func.sum(Entrada.quantidade), 0)
                ).filter(
                    Entrada.id_pedido_compra == entrada.id_pedido_compra,
                    Entrada.id_entrada != id_entrada,
                ).scalar() or 0
                restante = int(pedido.quantidade) - int(total_outras_entradas)
                if int(quantidade) > restante:
                    raise ValueError(
                        f"Quantidade acima do pedido. Pedido #{pedido.id_pedido_compra}: "
                        f"comprado {pedido.quantidade}, outras entradas {total_outras_entradas}, "
                        f"máximo permitido nesta entrada {max(restante, 0)}."
                    )
            entrada.quantidade = quantidade
        if data_entrada is not None:
            entrada.data_entrada = data_entrada
        if observacao is not None:
            entrada.observacao = observacao

        registrar_auditoria(session, "ALTERAÇÃO", "entrada", f"Entrada #{entrada.id_entrada} alterada: quantidade={entrada.quantidade}, tamanho={entrada.id_tamanho}.", id_registro=entrada.id_entrada)
        session.commit()
        session.refresh(entrada)
        return entrada
    finally:
        session.close()


def excluir_entrada(id_entrada: int) -> bool:
    session = get_session()
    try:
        entrada = session.get(Entrada, id_entrada)
        if entrada is None:
            return False
        id_registro=entrada.id_entrada
        session.delete(entrada)
        registrar_auditoria(session, "EXCLUSÃO", "entrada", f"Entrada #{id_registro} excluída.", id_registro=id_registro)
        session.commit()
        return True
    finally:
        session.close()
