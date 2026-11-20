"""Configuração do banco local independente do EPIControl."""
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker


def _diretorio_dados_local():
    """Retorna %LOCALAPPDATA% em Windows, com fallback para ~/.local/share."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "EPIControl" / "data"
    return Path.home() / ".local" / "share" / "EPIControl" / "data"


# O override existe para testes automatizados isolados. O uso normal sempre segue
# o caminho oficial de dados do usuário e ignora configurações de banco antigas.
_test_db_path = os.environ.get("EPICONTROL_TEST_DB_PATH") if not getattr(sys, "frozen", False) else None
SQLITE_PATH = Path(_test_db_path) if _test_db_path else _diretorio_dados_local() / "epicontrol.db"
SQLITE_PATH = SQLITE_PATH.expanduser().resolve()
SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)

IS_SQLITE = True
IS_MYSQL = False
DATABASE_URL = f"sqlite:///{SQLITE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30},
)


@event.listens_for(engine, "connect")
def _ativar_foreign_keys(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_session():
    return SessionLocal()


def iniciar_esquema():
    """Cria as tabelas do modelo local e completa colunas compatíveis ausentes."""
    from app.models import models as _models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    # Migrações não destrutivas mantidas para instalações locais existentes.
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "funcionario" in inspector.get_table_names():
        colunas = {c["name"] for c in inspector.get_columns("funcionario")}
        with engine.begin() as conn:
            if "id_empresa" not in colunas:
                conn.execute(text(
                    "ALTER TABLE funcionario ADD COLUMN id_empresa INTEGER "
                    "REFERENCES empresa(id_empresa)"
                ))
            if "cpf" not in colunas:
                conn.execute(text("ALTER TABLE funcionario ADD COLUMN cpf VARCHAR(14) NULL"))
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_funcionario_cpf ON funcionario (cpf)"
            ))
