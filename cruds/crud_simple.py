"""
CRUD das tabelas "simples" do sistema (sem relacionamento com outras
tabelas): categoria, fornecedor, funcionario, setor_loja, tamanho.

Cada tabela tem 4 funções: criar, listar, atualizar, excluir.
Use como modelo pra criar o CRUD das tabelas mais complexas depois
(produtos, entrada, saida).
"""

from app.config.database import get_session
from sqlalchemy.orm import joinedload
from app.models.models import Categoria, Empresa, Fornecedor, Funcionario, SetorLoja, Tamanho


# ------------------------------------------------------------
# CATEGORIA
# ------------------------------------------------------------
def criar_categoria(nome: str) -> Categoria:
    session = get_session()
    try:
        nova = Categoria(nome=nome)
        session.add(nova)
        session.commit()
        session.refresh(nova)
        return nova
    finally:
        session.close()


def listar_categorias() -> list[Categoria]:
    session = get_session()
    try:
        return session.query(Categoria).order_by(Categoria.nome).all()
    finally:
        session.close()


def atualizar_categoria(id_categoria: int, novo_nome: str) -> Categoria | None:
    session = get_session()
    try:
        categoria = session.get(Categoria, id_categoria)
        if categoria is None:
            return None
        categoria.nome = novo_nome
        session.commit()
        session.refresh(categoria)
        return categoria
    finally:
        session.close()


def excluir_categoria(id_categoria: int) -> bool:
    session = get_session()
    try:
        categoria = session.get(Categoria, id_categoria)
        if categoria is None:
            return False
        session.delete(categoria)
        session.commit()
        return True
    finally:
        session.close()


# ------------------------------------------------------------
# FORNECEDOR
# ------------------------------------------------------------
def criar_fornecedor(nome: str, contato: str | None = None) -> Fornecedor:
    session = get_session()
    try:
        novo = Fornecedor(nome=nome, contato=contato)
        session.add(novo)
        session.commit()
        session.refresh(novo)
        return novo
    finally:
        session.close()


def listar_fornecedores() -> list[Fornecedor]:
    session = get_session()
    try:
        return session.query(Fornecedor).order_by(Fornecedor.nome).all()
    finally:
        session.close()


def atualizar_fornecedor(id_fornecedor: int, nome: str = None, contato: str = None) -> Fornecedor | None:
    session = get_session()
    try:
        fornecedor = session.get(Fornecedor, id_fornecedor)
        if fornecedor is None:
            return None
        if nome is not None:
            fornecedor.nome = nome
        if contato is not None:
            fornecedor.contato = contato
        session.commit()
        session.refresh(fornecedor)
        return fornecedor
    finally:
        session.close()


def excluir_fornecedor(id_fornecedor: int) -> bool:
    session = get_session()
    try:
        fornecedor = session.get(Fornecedor, id_fornecedor)
        if fornecedor is None:
            return False
        session.delete(fornecedor)
        session.commit()
        return True
    finally:
        session.close()


# ------------------------------------------------------------
# EMPRESA
# ------------------------------------------------------------
def _normalizar_cnpj(cnpj: str) -> str:
    # Aceita CNPJ numérico tradicional e o formato alfanumérico previsto para novas inscrições.
    import re
    valor = re.sub(r"[^A-Za-z0-9]", "", (cnpj or "")).upper()
    if len(valor) != 14:
        raise ValueError("Informe um CNPJ com 14 caracteres (números e, quando aplicável, letras).")
    if valor.isdigit():
        return f"{valor[:2]}.{valor[2:5]}.{valor[5:8]}/{valor[8:12]}-{valor[12:]}"
    return valor


def criar_empresa(razao_social: str, cnpj: str) -> Empresa:
    razao_social = (razao_social or "").strip()
    if not razao_social:
        raise ValueError("Informe a razão social da empresa.")
    session = get_session()
    try:
        nova = Empresa(razao_social=razao_social, cnpj=_normalizar_cnpj(cnpj))
        session.add(nova)
        session.commit()
        session.refresh(nova)
        return nova
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def listar_empresas() -> list[Empresa]:
    session = get_session()
    try:
        return session.query(Empresa).order_by(Empresa.razao_social).all()
    finally:
        session.close()


def atualizar_empresa(id_empresa: int, razao_social: str, cnpj: str) -> Empresa | None:
    razao_social = (razao_social or "").strip()
    if not razao_social:
        raise ValueError("Informe a razão social da empresa.")
    session = get_session()
    try:
        empresa = session.get(Empresa, id_empresa)
        if empresa is None:
            return None
        empresa.razao_social = razao_social
        empresa.cnpj = _normalizar_cnpj(cnpj)
        session.commit()
        session.refresh(empresa)
        return empresa
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def excluir_empresa(id_empresa: int) -> bool:
    session = get_session()
    try:
        empresa = session.get(Empresa, id_empresa)
        if empresa is None:
            return False
        if session.query(Funcionario).filter(Funcionario.id_empresa == id_empresa).first():
            raise ValueError("Não é possível excluir esta empresa: há funcionários vinculados a ela.")
        session.delete(empresa)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ------------------------------------------------------------
# FUNCIONARIO
# ------------------------------------------------------------
def _validar_cpf(cpf: str) -> str:
    """Valida CPF e retorna formato canônico XXX.XXX.XXX-XX."""
    import re
    digitos = re.sub(r"\D", "", cpf or "")
    if len(digitos) != 11 or len(set(digitos)) == 1:
        raise ValueError("Informe um CPF válido com 11 dígitos.")
    soma = sum(int(digitos[i]) * (10 - i) for i in range(9))
    d1 = (soma * 10) % 11
    if d1 == 10:
        d1 = 0
    soma = sum(int(digitos[i]) * (11 - i) for i in range(10))
    d2 = (soma * 10) % 11
    if d2 == 10:
        d2 = 0
    if digitos[-2:] != f"{d1}{d2}":
        raise ValueError("O CPF informado não é válido. Confira os números digitados.")
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def criar_funcionario(nome: str, cpf: str, id_empresa: int | None = None) -> Funcionario:
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome do funcionário.")
    cpf = _validar_cpf(cpf)
    if not id_empresa:
        raise ValueError("Selecione a empresa do funcionário.")
    session = get_session()
    try:
        empresa = session.get(Empresa, int(id_empresa))
        if empresa is None:
            raise ValueError("A empresa selecionada não existe.")
        if session.query(Funcionario).filter(Funcionario.cpf == cpf).first():
            raise ValueError("Já existe um funcionário cadastrado com este CPF.")
        novo = Funcionario(nome=nome, cpf=cpf, id_empresa=empresa.id_empresa)
        session.add(novo)
        session.commit()
        session.refresh(novo)
        return novo
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def listar_funcionarios() -> list[Funcionario]:
    session = get_session()
    try:
        return (session.query(Funcionario)
                .options(joinedload(Funcionario.empresa))
                .order_by(Funcionario.nome).all())
    finally:
        session.close()


def atualizar_funcionario(id_funcionario: int, novo_nome: str, cpf: str, id_empresa: int | None = None) -> Funcionario | None:
    novo_nome = (novo_nome or "").strip()
    if not novo_nome:
        raise ValueError("Informe o nome do funcionário.")
    cpf = _validar_cpf(cpf)
    if not id_empresa:
        raise ValueError("Selecione a empresa do funcionário.")
    session = get_session()
    try:
        funcionario = session.get(Funcionario, id_funcionario)
        if funcionario is None:
            return None
        empresa = session.get(Empresa, int(id_empresa))
        if empresa is None:
            raise ValueError("A empresa selecionada não existe.")
        duplicado = (session.query(Funcionario)
                     .filter(Funcionario.cpf == cpf, Funcionario.id_funcionario != id_funcionario)
                     .first())
        if duplicado:
            raise ValueError("Já existe outro funcionário cadastrado com este CPF.")
        funcionario.nome = novo_nome
        funcionario.cpf = cpf
        funcionario.id_empresa = empresa.id_empresa
        session.commit()
        session.refresh(funcionario)
        return funcionario
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def excluir_funcionario(id_funcionario: int) -> bool:
    session = get_session()
    try:
        funcionario = session.get(Funcionario, id_funcionario)
        if funcionario is None:
            return False
        session.delete(funcionario)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ------------------------------------------------------------
# SETOR_LOJA
# ------------------------------------------------------------
def criar_setor_loja(nome: str) -> SetorLoja:
    session = get_session()
    try:
        novo = SetorLoja(nome=nome)
        session.add(novo)
        session.commit()
        session.refresh(novo)
        return novo
    finally:
        session.close()


def listar_setores_loja() -> list[SetorLoja]:
    session = get_session()
    try:
        return session.query(SetorLoja).order_by(SetorLoja.nome).all()
    finally:
        session.close()


def atualizar_setor_loja(id_setor_loja: int, novo_nome: str) -> SetorLoja | None:
    session = get_session()
    try:
        setor = session.get(SetorLoja, id_setor_loja)
        if setor is None:
            return None
        setor.nome = novo_nome
        session.commit()
        session.refresh(setor)
        return setor
    finally:
        session.close()


def excluir_setor_loja(id_setor_loja: int) -> bool:
    session = get_session()
    try:
        setor = session.get(SetorLoja, id_setor_loja)
        if setor is None:
            return False
        session.delete(setor)
        session.commit()
        return True
    finally:
        session.close()


# ------------------------------------------------------------
# TAMANHO
# ------------------------------------------------------------
def criar_tamanho(nome: str) -> Tamanho:
    session = get_session()
    try:
        novo = Tamanho(nome=nome)
        session.add(novo)
        session.commit()
        session.refresh(novo)
        return novo
    finally:
        session.close()


def listar_tamanhos() -> list[Tamanho]:
    session = get_session()
    try:
        return session.query(Tamanho).order_by(Tamanho.nome).all()
    finally:
        session.close()


def atualizar_tamanho(id_tamanho: int, novo_nome: str) -> Tamanho | None:
    session = get_session()
    try:
        tamanho = session.get(Tamanho, id_tamanho)
        if tamanho is None:
            return None
        tamanho.nome = novo_nome
        session.commit()
        session.refresh(tamanho)
        return tamanho
    finally:
        session.close()


def excluir_tamanho(id_tamanho: int) -> bool:
    session = get_session()
    try:
        tamanho = session.get(Tamanho, id_tamanho)
        if tamanho is None:
            return False
        session.delete(tamanho)
        session.commit()
        return True
    finally:
        session.close()
