"""
CRUD da tabela produtos.

Diferença pras tabelas simples: produtos tem duas chaves estrangeiras
(id_categoria e id_usuario). Por isso:
- criar_produto valida que a categoria e o usuário existem antes de
  gravar, pra não deixar cair um erro feio do banco lá na frente.
- listar_produtos já traz o nome da categoria e do usuário junto,
  usando os relacionamentos definidos no model (produto.categoria,
  produto.usuario), sem precisar escrever nenhum JOIN na mão.
"""

from sqlalchemy.orm import joinedload
from app.config.database import get_session
from app.models.models import Produto, Categoria, Usuario, SetorLoja
from app.repositories.crud_auditoria import registrar_auditoria


def categoria_e_epi(categoria: Categoria | None) -> bool:
    """Considera EPI qualquer categoria cujo nome contenha a sigla EPI."""
    return bool(categoria and "epi" in (categoria.nome or "").casefold())


def criar_produto(
    nome: str,
    id_categoria: int,
    id_usuario: int,
    descricao: str | None = None,
    id_setor_padrao: int | None = None,
    estoque_minimo: int = 0,
    ca: str | None = None,
) -> Produto:
    session = get_session()
    try:
        if session.get(Categoria, id_categoria) is None:
            raise ValueError(f"Categoria com id {id_categoria} não existe.")
        if session.get(Usuario, id_usuario) is None:
            raise ValueError(f"Usuário com id {id_usuario} não existe.")
        if id_setor_padrao is not None and session.get(SetorLoja, id_setor_padrao) is None:
            raise ValueError(f"Setor/loja com id {id_setor_padrao} não existe.")
        if int(estoque_minimo) < 0:
            raise ValueError("O estoque mínimo não pode ser negativo.")
        ca = (ca or "").strip() or None
        categoria = session.get(Categoria, id_categoria)
        if categoria_e_epi(categoria) and not ca:
            raise ValueError("Produtos da categoria EPI exigem o preenchimento do CA (Certificado de Aprovação).")

        novo = Produto(
            nome=nome,
            id_categoria=id_categoria,
            id_usuario=id_usuario,
            descricao=descricao,
            ca=ca,
            estoque_minimo=int(estoque_minimo),
            id_setor_padrao=id_setor_padrao,
        )
        session.add(novo)
        session.flush()
        registrar_auditoria(session, "CRIAÇÃO", "produto", f"Produto #{novo.id_produto} criado: {novo.nome}; estoque mínimo={novo.estoque_minimo}.", id_registro=novo.id_produto)
        session.commit()
        session.refresh(novo)
        return novo
    finally:
        session.close()


def listar_produtos() -> list[Produto]:
    session = get_session()
    try:
        # joinedload carrega categoria, usuario e setor_padrao junto, na mesma
        # consulta, pra poder acessar produto.categoria.nome depois de fechar
        # a sessão sem dar erro (o dado já veio pronto, não precisa buscar de novo).
        return (
            session.query(Produto)
            .options(joinedload(Produto.categoria), joinedload(Produto.usuario), joinedload(Produto.setor_padrao))
            .order_by(Produto.nome)
            .all()
        )
    finally:
        session.close()


def buscar_produto(id_produto: int) -> Produto | None:
    session = get_session()
    try:
        return (
            session.query(Produto)
            .options(joinedload(Produto.categoria), joinedload(Produto.usuario), joinedload(Produto.setor_padrao))
            .filter(Produto.id_produto == id_produto)
            .first()
        )
    finally:
        session.close()


def atualizar_produto(
    id_produto: int,
    nome: str = None,
    id_categoria: int = None,
    id_usuario: int = None,
    descricao: str = None,
    id_setor_padrao: int = None,
    estoque_minimo: int = None,
    ca: str | None = None,
) -> Produto | None:
    session = get_session()
    try:
        produto = session.get(Produto, id_produto)
        if produto is None:
            return None

        if id_categoria is not None:
            if session.get(Categoria, id_categoria) is None:
                raise ValueError(f"Categoria com id {id_categoria} não existe.")
            produto.id_categoria = id_categoria

        categoria_atual = session.get(Categoria, produto.id_categoria) if produto.id_categoria else None
        ca_informado = (ca or "").strip() or None
        if categoria_e_epi(categoria_atual):
            if ca is not None:
                produto.ca = ca_informado
            if not (produto.ca or "").strip():
                raise ValueError("Produtos da categoria EPI exigem o preenchimento do CA (Certificado de Aprovação).")
        elif ca is not None:
            produto.ca = ca_informado

        if id_usuario is not None:
            if session.get(Usuario, id_usuario) is None:
                raise ValueError(f"Usuário com id {id_usuario} não existe.")
            produto.id_usuario = id_usuario

        if id_setor_padrao is not None:
            if session.get(SetorLoja, id_setor_padrao) is None:
                raise ValueError(f"Setor/loja com id {id_setor_padrao} não existe.")
            produto.id_setor_padrao = id_setor_padrao

        if estoque_minimo is not None:
            if int(estoque_minimo) < 0:
                raise ValueError("O estoque mínimo não pode ser negativo.")
            produto.estoque_minimo = int(estoque_minimo)

        if nome is not None:
            produto.nome = nome
        if descricao is not None:
            produto.descricao = descricao

        registrar_auditoria(session, "ALTERAÇÃO", "produto", f"Produto #{produto.id_produto} alterado: {produto.nome}; estoque mínimo={produto.estoque_minimo}.", id_registro=produto.id_produto)
        session.commit()
        session.refresh(produto)
        return produto
    finally:
        session.close()


def excluir_produto(id_produto: int) -> bool:
    session = get_session()
    try:
        produto = session.get(Produto, id_produto)
        if produto is None:
            return False
        id_registro=produto.id_produto
        nome=produto.nome
        session.delete(produto)
        registrar_auditoria(session, "EXCLUSÃO", "produto", f"Produto #{id_registro} excluído: {nome}.", id_registro=id_registro)
        session.commit()
        return True
    finally:
        session.close()
