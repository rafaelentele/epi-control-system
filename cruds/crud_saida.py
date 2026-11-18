"""
CRUD de pedido_saida (cabeçalho: quem recebeu, setor, data, quem
registrou) e seus itens em saida (produto, tamanho, quantidade).

Um pedido de saída pode ter vários itens - por exemplo, um
funcionário recebendo camisa + calça + capacete de uma vez só.
"""

from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.config.database import get_session
from app.auth import obter_usuario_atual
from app.models.models import PedidoSaida, Saida, Funcionario, SetorLoja, Produto, Tamanho, Usuario, Entrada, AjusteEstoque
from app.repositories.crud_auditoria import registrar_auditoria


def _validar_item(session, id_produto: int, id_tamanho: int):
    produto = session.get(Produto, id_produto)
    if produto is None:
        raise ValueError(f"Produto com id {id_produto} não existe.")
    tamanho = session.get(Tamanho, id_tamanho)
    if tamanho is None:
        raise ValueError(f"Tamanho com id {id_tamanho} não existe.")
    return produto, tamanho


def _saldo_produto_tamanho(session, id_produto: int, id_tamanho: int) -> int:
    entrada = session.query(func.coalesce(func.sum(Entrada.quantidade), 0)).filter(
        Entrada.id_produto == id_produto, Entrada.id_tamanho == id_tamanho
    ).scalar() or 0
    saida = session.query(func.coalesce(func.sum(Saida.quantidade), 0)).filter(
        Saida.id_produto == id_produto, Saida.id_tamanho == id_tamanho
    ).scalar() or 0
    ajuste = session.query(func.coalesce(func.sum(AjusteEstoque.quantidade_ajuste), 0)).filter(
        AjusteEstoque.id_produto == id_produto, AjusteEstoque.id_tamanho == id_tamanho
    ).scalar() or 0
    return int(entrada) - int(saida) + int(ajuste)


def consultar_saldo(id_produto: int, id_tamanho: int) -> int:
    """Saldo atual (entradas - saídas + ajustes) de um produto em um tamanho."""
    session = get_session()
    try:
        return _saldo_produto_tamanho(session, id_produto, id_tamanho)
    finally:
        session.close()


def _validar_estoque_dos_itens(session, itens: list[dict]):
    """Valida o saldo por produto+tamanho e bloqueia o produto durante a operação.

    O bloqueio da linha de Produto evita que dois computadores que estejam
    usando este mesmo serviço confirmem simultaneamente saídas acima do saldo.
    Os produtos são bloqueados em ordem crescente para reduzir risco de deadlock.
    """
    agregados = {}
    for item in itens:
        quantidade = int(item.get("quantidade", 0))
        if quantidade <= 0:
            raise ValueError("A quantidade de cada item deve ser maior que zero.")
        chave = (item["id_produto"], item["id_tamanho"])
        agregados[chave] = agregados.get(chave, 0) + quantidade

    ids_produto = sorted({id_produto for id_produto, _ in agregados})
    for id_produto in ids_produto:
        produto = session.query(Produto).filter(Produto.id_produto == id_produto).with_for_update().first()
        if produto is None:
            raise ValueError(f"Produto com id {id_produto} não existe.")

    for (id_produto, id_tamanho), quantidade_solicitada in agregados.items():
        produto, tamanho = _validar_item(session, id_produto, id_tamanho)
        saldo = _saldo_produto_tamanho(session, id_produto, id_tamanho)
        if quantidade_solicitada > saldo:
            raise ValueError(
                f"Estoque insuficiente para '{produto.nome}' no tamanho {tamanho.nome}. "
                f"Saldo disponível: {saldo}. Quantidade solicitada: {quantidade_solicitada}."
            )


def criar_pedido_saida(
    id_funcionario: int,
    id_setor_loja: int,
    id_usuario: int,
    itens: list[dict],
    data_saida: date = None,
    observacao: str | None = None,
) -> PedidoSaida:
    """
    itens: lista de dicts, cada um com id_produto, id_tamanho, quantidade.
    Ex: [{"id_produto": 3, "id_tamanho": 4, "quantidade": 2}, ...]
    """
    if not itens:
        raise ValueError("O pedido precisa ter pelo menos um item.")

    session = get_session()
    try:
        # A baixa deve sempre ficar vinculada ao usuário autenticado.
        # Se houver uma sessão ativa, ela prevalece sobre qualquer id enviado pela interface.
        usuario_atual = obter_usuario_atual()
        if usuario_atual:
            id_usuario = usuario_atual["id_usuario"]

        if session.get(Funcionario, id_funcionario) is None:
            raise ValueError(f"Funcionário com id {id_funcionario} não existe.")
        if session.get(SetorLoja, id_setor_loja) is None:
            raise ValueError(f"Setor/loja com id {id_setor_loja} não existe.")
        if session.get(Usuario, id_usuario) is None:
            raise ValueError(f"Usuário com id {id_usuario} não existe.")
        _validar_estoque_dos_itens(session, itens)

        pedido = PedidoSaida(
            id_funcionario=id_funcionario,
            id_setor_loja=id_setor_loja,
            id_usuario=id_usuario,
            data_saida=data_saida or date.today(),
            observacao=observacao,
        )
        for item in itens:
            pedido.itens.append(Saida(
                id_produto=item["id_produto"],
                id_tamanho=item["id_tamanho"],
                quantidade=item["quantidade"],
            ))

        session.add(pedido)
        session.flush()
        resumo=", ".join(f"produto #{i['id_produto']} tam. #{i['id_tamanho']} x {i['quantidade']}" for i in itens)
        registrar_auditoria(session, "BAIXA", "pedido_saida", f"Baixa #{pedido.id_pedido_saida} para funcionário #{id_funcionario}: {resumo}.", id_registro=pedido.id_pedido_saida, id_usuario=id_usuario)
        session.commit()
        session.refresh(pedido)
        return pedido
    finally:
        session.close()


def _query_pedidos_com_relacionamentos(session):
    return session.query(PedidoSaida).options(
        joinedload(PedidoSaida.funcionario).joinedload(Funcionario.empresa),
        joinedload(PedidoSaida.setor_loja),
        joinedload(PedidoSaida.usuario),
        joinedload(PedidoSaida.itens).joinedload(Saida.produto).joinedload(Produto.categoria),
        joinedload(PedidoSaida.itens).joinedload(Saida.tamanho),
    )


def listar_pedidos_saida() -> list[PedidoSaida]:
    session = get_session()
    try:
        return _query_pedidos_com_relacionamentos(session).order_by(PedidoSaida.data_saida.desc()).all()
    finally:
        session.close()


def buscar_pedido_saida(id_pedido_saida: int) -> PedidoSaida | None:
    session = get_session()
    try:
        return (
            _query_pedidos_com_relacionamentos(session)
            .filter(PedidoSaida.id_pedido_saida == id_pedido_saida)
            .first()
        )
    finally:
        session.close()


def listar_pedidos_saida_por_funcionario(id_funcionario: int) -> list[PedidoSaida]:
    session = get_session()
    try:
        return (
            _query_pedidos_com_relacionamentos(session)
            .filter(PedidoSaida.id_funcionario == id_funcionario)
            .order_by(PedidoSaida.data_saida.desc())
            .all()
        )
    finally:
        session.close()


def atualizar_pedido_saida(
    id_pedido_saida: int,
    id_setor_loja: int = None,
    data_saida: date = None,
    observacao: str = None,
) -> PedidoSaida | None:
    """Pedidos de saída são fechados no momento do salvamento e não podem ser editados."""
    session = get_session()
    try:
        pedido = session.get(PedidoSaida, id_pedido_saida)
        if pedido is None:
            return None
        raise ValueError(f"O pedido de saída #{id_pedido_saida} já está fechado e não pode ser alterado.")
    finally:
        session.close()


def excluir_pedido_saida(id_pedido_saida: int) -> bool:
    """Exclui o pedido inteiro e todos os itens dele (cascade)."""
    session = get_session()
    try:
        pedido = session.get(PedidoSaida, id_pedido_saida)
        if pedido is None:
            return False
        id_registro=pedido.id_pedido_saida
        session.delete(pedido)
        registrar_auditoria(session, "EXCLUSÃO", "pedido_saida", f"Baixa #{id_registro} excluída.", id_registro=id_registro)
        session.commit()
        return True
    finally:
        session.close()
