"""Cria a tabela de permissoes individuais sem apagar dados."""
from app.config.database import Base, engine
from app.models.models import UsuarioPermissao

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine, tables=[UsuarioPermissao.__table__])
    print("Migracao de permissoes concluida com sucesso.")
