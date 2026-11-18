"""
Modelos ORM (SQLAlchemy) — um por tabela do banco controle_fardamento_rh.
Os nomes de classes/atributos seguem exatamente os nomes de tabela/coluna
do SQL, então não tem tradução nem confusão de nomenclatura.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime,
    DECIMAL, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.config.database import Base


class Tamanho(Base):
    __tablename__ = "tamanho"

    id_tamanho = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(10), nullable=False, unique=True)


class Categoria(Base):
    __tablename__ = "categoria"

    id_categoria = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(45), nullable=False, unique=True)


class Fornecedor(Base):
    __tablename__ = "fornecedor"

    id_fornecedor = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(45), nullable=False)
    contato = Column(String(45))


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    login = Column(String(50), nullable=False, unique=True)
    nivel_acesso = Column(String(20), nullable=False, default="Operador")
    criado_em = Column(DateTime, server_default=func.now())
    password_hash = Column(String(255), nullable=True)

    permissoes = relationship("UsuarioPermissao", back_populates="usuario", cascade="all, delete-orphan")


class UsuarioPermissao(Base):
    __tablename__ = "usuario_permissao"

    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), primary_key=True)
    permissao = Column(String(80), primary_key=True)
    usuario = relationship("Usuario", back_populates="permissoes")


class Empresa(Base):
    __tablename__ = "empresa"

    id_empresa = Column(Integer, primary_key=True, autoincrement=True)
    razao_social = Column(String(150), nullable=False, unique=True)
    cnpj = Column(String(18), nullable=False, unique=True)

    funcionarios = relationship("Funcionario", back_populates="empresa")


class Funcionario(Base):
    __tablename__ = "funcionario"

    id_funcionario = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(45), nullable=False)
    # Nullable no banco para preservar registros antigos durante a migração;
    # a tela e o CRUD exigem CPF em novos cadastros e alterações.
    cpf = Column(String(14), nullable=True, unique=True)
    # Permite migrar os registros antigos sem atribuir empresa incorretamente.
    id_empresa = Column(Integer, ForeignKey("empresa.id_empresa"), nullable=True)
    empresa = relationship("Empresa", back_populates="funcionarios")


class SetorLoja(Base):
    __tablename__ = "setor_loja"

    id_setor_loja = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(45), nullable=False)


class Produto(Base):
    __tablename__ = "produtos"

    id_produto = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(45), nullable=False)
    id_categoria = Column(Integer, ForeignKey("categoria.id_categoria"))
    id_setor_padrao = Column(Integer, ForeignKey("setor_loja.id_setor_loja"))
    descricao = Column(Text)
    ca = Column(String(50), nullable=True)
    estoque_minimo = Column(Integer, nullable=False, default=0, server_default="0")
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"))

    categoria = relationship("Categoria")
    setor_padrao = relationship("SetorLoja")
    usuario = relationship("Usuario")


class PedidoDeCompra(Base):
    __tablename__ = "pedido_de_compra"

    id_pedido_compra = Column(Integer, primary_key=True, autoincrement=True)
    id_produto = Column(Integer, ForeignKey("produtos.id_produto"))
    quantidade = Column(Integer, nullable=False)
    preco = Column(DECIMAL(10, 2))
    data_compra = Column(Date)
    id_fornecedor = Column(Integer, ForeignKey("fornecedor.id_fornecedor"))
    observacao = Column(Text)

    produto = relationship("Produto")
    fornecedor = relationship("Fornecedor")


class Entrada(Base):
    __tablename__ = "entrada"

    id_entrada = Column(Integer, primary_key=True, autoincrement=True)
    id_produto = Column(Integer, ForeignKey("produtos.id_produto"))
    id_pedido_compra = Column(Integer, ForeignKey("pedido_de_compra.id_pedido_compra"))
    quantidade = Column(Integer, nullable=False)
    id_tamanho = Column(Integer, ForeignKey("tamanho.id_tamanho"))
    data_entrada = Column(Date)
    id_fornecedor = Column(Integer, ForeignKey("fornecedor.id_fornecedor"))
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"))
    observacao = Column(String(100))

    produto = relationship("Produto")
    pedido_compra = relationship("PedidoDeCompra")
    tamanho = relationship("Tamanho")
    fornecedor = relationship("Fornecedor")
    usuario = relationship("Usuario")


class PedidoSaida(Base):
    __tablename__ = "pedido_saida"

    id_pedido_saida = Column(Integer, primary_key=True, autoincrement=True)
    id_funcionario = Column(Integer, ForeignKey("funcionario.id_funcionario"))
    id_setor_loja = Column(Integer, ForeignKey("setor_loja.id_setor_loja"))
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"))
    data_saida = Column(Date)
    observacao = Column(Text)

    funcionario = relationship("Funcionario")
    setor_loja = relationship("SetorLoja")
    usuario = relationship("Usuario")
    itens = relationship("Saida", back_populates="pedido_saida", cascade="all, delete-orphan")


class Saida(Base):
    __tablename__ = "saida"

    id_saida = Column(Integer, primary_key=True, autoincrement=True)
    id_pedido_saida = Column(Integer, ForeignKey("pedido_saida.id_pedido_saida"), nullable=False)
    id_produto = Column(Integer, ForeignKey("produtos.id_produto"))
    id_tamanho = Column(Integer, ForeignKey("tamanho.id_tamanho"))
    quantidade = Column(Integer, nullable=False)

    pedido_saida = relationship("PedidoSaida", back_populates="itens")
    produto = relationship("Produto")
    tamanho = relationship("Tamanho")


class Auditoria(Base):
    __tablename__ = "auditoria"
    id_auditoria = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    data_hora = Column(DateTime, server_default=func.now(), nullable=False)
    operacao = Column(String(30), nullable=False)
    entidade = Column(String(60), nullable=False)
    id_registro = Column(Integer, nullable=True)
    descricao = Column(Text, nullable=False)
    usuario = relationship("Usuario")


class AjusteEstoque(Base):
    __tablename__ = "ajuste_estoque"

    id_ajuste = Column(Integer, primary_key=True, autoincrement=True)
    id_produto = Column(Integer, ForeignKey("produtos.id_produto"), nullable=False)
    id_tamanho = Column(Integer, ForeignKey("tamanho.id_tamanho"), nullable=False)
    quantidade_ajuste = Column(Integer, nullable=False)
    estoque_anterior = Column(Integer, nullable=False)
    estoque_posterior = Column(Integer, nullable=False)
    motivo = Column(String(60), nullable=False)
    observacao = Column(Text)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    data_ajuste = Column(DateTime, server_default=func.now(), nullable=False)

    produto = relationship("Produto")
    tamanho = relationship("Tamanho")
    usuario = relationship("Usuario")
