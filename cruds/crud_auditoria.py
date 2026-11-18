from datetime import datetime, timezone, timedelta
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from app.config.database import get_session
from app.models.models import Auditoria

def registrar_auditoria(session, operacao, entidade, descricao, id_registro=None, id_usuario=None):
    if id_usuario is None:
        try:
            from app.auth import obter_usuario_atual
            id_usuario = (obter_usuario_atual() or {}).get("id_usuario")
        except Exception:
            id_usuario = None
    agora_local = datetime.now(timezone(timedelta(hours=-3))).replace(tzinfo=None)
    session.add(Auditoria(id_usuario=id_usuario, data_hora=agora_local, operacao=operacao, entidade=entidade, id_registro=id_registro, descricao=descricao))

def listar_auditoria(limite=500, operacao=None, id_usuario=None):
    session=get_session()
    try:
        q=session.query(Auditoria).options(joinedload(Auditoria.usuario))
        if operacao: q=q.filter(Auditoria.operacao==operacao)
        if id_usuario: q=q.filter(Auditoria.id_usuario==id_usuario)
        return q.order_by(desc(Auditoria.data_hora)).limit(limite).all()
    finally: session.close()
