"""CRUD e persistencia de usuarios/permissoes."""
from sqlalchemy.exc import IntegrityError
from app.config.database import get_session
from app.models.models import Usuario, UsuarioPermissao
from app.repositories.crud_auditoria import registrar_auditoria
from app.auth import (
    _hash_senha, PERMISSOES, PERMISSOES_OPERADOR_PADRAO, validar_senha,
    obter_usuario_atual,
)

NIVEIS_VALIDOS = ("Administrador", "Operador")


def _exigir_administrador():
    atual = obter_usuario_atual()
    if not atual or atual.get("nivel_acesso") != "Administrador":
        raise PermissionError("Somente um usuário com perfil Administrador pode gerenciar usuários e permissões.")

def criar_usuario(nome, login, nivel_acesso="Operador", senha=None, permissoes=None):
    _exigir_administrador()
    if not (nome or "").strip() or not (login or "").strip():
        raise ValueError("Informe nome e login.")
    if nivel_acesso not in NIVEIS_VALIDOS:
        raise ValueError("Nível de acesso inválido.")
    validar_senha(senha)
    session=get_session()
    try:
        novo=Usuario(nome=nome, login=login, nivel_acesso=nivel_acesso, password_hash=_hash_senha(senha))
        session.add(novo); session.flush()
        if nivel_acesso == "Administrador":
            permissoes=set(PERMISSOES)
        elif permissoes is None:
            permissoes=set(PERMISSOES_OPERADOR_PADRAO)
        for p in permissoes or set():
            if p in PERMISSOES:
                session.add(UsuarioPermissao(id_usuario=novo.id_usuario, permissao=p))
        registrar_auditoria(session, "CRIAÇÃO", "usuario", f"Usuário #{novo.id_usuario} criado: {novo.nome} ({novo.login}), nível {novo.nivel_acesso}.", id_registro=novo.id_usuario)
        try: session.commit()
        except IntegrityError:
            session.rollback(); raise ValueError(f"Já existe um usuário com o login '{login}'.")
        session.refresh(novo); return novo
    finally: session.close()

def listar_usuarios():
    session=get_session()
    try: return session.query(Usuario).order_by(Usuario.nome).all()
    finally: session.close()

def obter_permissoes(id_usuario):
    session=get_session()
    try: return {p.permissao for p in session.query(UsuarioPermissao).filter(UsuarioPermissao.id_usuario==id_usuario).all()}
    finally: session.close()

def salvar_permissoes(id_usuario, permissoes):
    _exigir_administrador()
    session=get_session()
    try:
        u=session.get(Usuario,id_usuario)
        if not u: raise ValueError("Usuário não encontrado.")
        if u.nivel_acesso == "Administrador":
            permissoes=set(PERMISSOES)
        session.query(UsuarioPermissao).filter(UsuarioPermissao.id_usuario==id_usuario).delete(synchronize_session=False)
        for p in set(permissoes):
            if p in PERMISSOES: session.add(UsuarioPermissao(id_usuario=id_usuario, permissao=p))
        registrar_auditoria(session, "PERMISSÕES", "usuario", f"Permissões do usuário #{id_usuario} atualizadas: {', '.join(sorted(set(permissoes)))}.", id_registro=id_usuario)
        session.commit()
    finally: session.close()

def atualizar_usuario(id_usuario, nome=None, login=None, nivel_acesso=None, senha=None):
    _exigir_administrador()
    session=get_session()
    try:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        u=session.get(Usuario,id_usuario)
        if u is None: return None
        if nivel_acesso is not None and nivel_acesso not in NIVEIS_VALIDOS:
            raise ValueError("Nível de acesso inválido.")
        if nome is not None and not nome.strip():
            raise ValueError("O nome não pode ficar vazio.")
        if login is not None and not login.strip():
            raise ValueError("O login não pode ficar vazio.")
        if u.nivel_acesso == "Administrador" and nivel_acesso == "Operador":
            administradores = session.query(Usuario).filter(Usuario.nivel_acesso == "Administrador").count()
            if administradores <= 1:
                raise ValueError("Não é possível rebaixar o último administrador.")
        if nome is not None: u.nome=nome
        if login is not None: u.login=login.strip()
        if nivel_acesso is not None: u.nivel_acesso=nivel_acesso
        if senha:
            validar_senha(senha)
            u.password_hash=_hash_senha(senha)
        if u.nivel_acesso == "Administrador":
            session.query(UsuarioPermissao).filter(UsuarioPermissao.id_usuario==u.id_usuario).delete(synchronize_session=False)
            for p in PERMISSOES: session.add(UsuarioPermissao(id_usuario=u.id_usuario, permissao=p))
        registrar_auditoria(session, "ALTERAÇÃO", "usuario", f"Usuário #{u.id_usuario} alterado: nome={u.nome}, nível={u.nivel_acesso}." + (" Senha alterada." if senha else ""), id_registro=u.id_usuario)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError(f"Já existe um usuário com o login '{login}'.") from exc
        session.refresh(u); return u
    finally: session.close()

def excluir_usuario(id_usuario):
    _exigir_administrador()
    session=get_session()
    try:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        u=session.get(Usuario,id_usuario)
        if not u: return False
        if u.nivel_acesso == "Administrador":
            administradores = session.query(Usuario).filter(Usuario.nivel_acesso == "Administrador").count()
            if administradores <= 1:
                raise ValueError("Não é possível excluir o último administrador.")
        session.query(UsuarioPermissao).filter(UsuarioPermissao.id_usuario==id_usuario).delete(synchronize_session=False)
        nome=u.nome
        session.delete(u)
        registrar_auditoria(session, "EXCLUSÃO", "usuario", f"Usuário #{id_usuario} excluído: {nome}.", id_registro=id_usuario)
        session.commit(); return True
    finally: session.close()
