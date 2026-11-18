"""
Conexão com o banco via SQLAlchemy.

Esta versão comercial usa um SQLite NOVO (não o banco Aiven em produção).
MySQL remoto só liga se ALLOW_REMOTE_DB=true — e mesmo assim deve ser um
banco novo, nunca o defaultdb que já está em uso.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parents[2]
    RESOURCE_DIR = BASE_DIR

CA_FILE_DEFAULT = RESOURCE_DIR / "ca.pem"

load_dotenv(BASE_DIR / ".env")

# Esta edição é o aplicativo desktop local. A edição em nuvem deverá usar uma
# API; credenciais do banco remoto não devem ser distribuídas no computador cliente.
APP_MODE = os.getenv("APP_MODE", "local").strip().lower()
if APP_MODE not in ("local", "cloud"):
    raise ValueError("APP_MODE inválido: use local ou cloud.")
if APP_MODE == "cloud":
    raise RuntimeError(
        "O modo cloud ainda não está disponível nesta edição. "
        "A versão em nuvem deverá se conectar por uma API, sem acesso direto ao Aiven."
    )

DB_ENGINE_NAME = os.getenv("DB_ENGINE", "sqlite").strip().lower()
if DB_ENGINE_NAME in ("", "local"):
    DB_ENGINE_NAME = "sqlite"
if DB_ENGINE_NAME in ("aiven", "nuvem", "cloud"):
    DB_ENGINE_NAME = "mysql"
if DB_ENGINE_NAME not in ("sqlite", "mysql"):
    raise ValueError(
        f"DB_ENGINE inválido: {DB_ENGINE_NAME!r}. Use sqlite ou mysql."
    )

IS_SQLITE = DB_ENGINE_NAME == "sqlite"
IS_MYSQL = DB_ENGINE_NAME == "mysql"
ALLOW_REMOTE_DB = os.getenv("ALLOW_REMOTE_DB", "false").lower() == "true"

if IS_MYSQL and not ALLOW_REMOTE_DB:
    raise RuntimeError(
        "Esta versão comercial não conecta no banco que já está em uso. "
        "O padrão é SQLite novo (epcontrol_comercial.db). "
        "Só use MySQL com ALLOW_REMOTE_DB=true e um banco NOVO."
    )

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "controle_fardamento_rh")
DB_SSL = os.getenv("DB_SSL", "false").lower() == "true"

_sqlite_cfg = os.getenv("SQLITE_PATH", "sistema_fardamento_local.db").strip() or "sistema_fardamento_local.db"
SQLITE_PATH = Path(_sqlite_cfg)
if not SQLITE_PATH.is_absolute():
    SQLITE_PATH = BASE_DIR / SQLITE_PATH

connect_args = {}
engine_kwargs = {"echo": False, "pool_pre_ping": True}

if IS_SQLITE:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{SQLITE_PATH.as_posix()}"
    connect_args = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool
else:
    DATABASE_URL = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        f"?charset=utf8mb4"
    )
    if DB_SSL:
        connect_args = {
            "ssl": {
                "ca": os.getenv("DB_SSL_CA", str(CA_FILE_DEFAULT)),
            }
        }

engine_kwargs["connect_args"] = connect_args
engine = create_engine(DATABASE_URL, **engine_kwargs)

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _ativar_foreign_keys(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_session():
    """Retorna uma nova sessão do banco."""
    return SessionLocal()


def iniciar_esquema():
    """Cria tabelas ausentes (SQLite novo ou MySQL incompleto) sem apagar dados."""
    from app.models import models as _models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    # Migração compatível com bancos já existentes: registros antigos ficam sem empresa.
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "funcionario" in inspector.get_table_names():
        colunas = {c["name"] for c in inspector.get_columns("funcionario")}
        if "id_empresa" not in colunas:
            if IS_SQLITE:
                with engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE funcionario ADD COLUMN id_empresa INTEGER "
                        "REFERENCES empresa(id_empresa)"
                    ))
            else:
                with engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE funcionario ADD COLUMN id_empresa INTEGER NULL"
                    ))
                    # FK é desejável; não refaz a coluna se o servidor não aceitar a constraint.
                    try:
                        conn.execute(text(
                            "ALTER TABLE funcionario ADD CONSTRAINT fk_funcionario_empresa "
                            "FOREIGN KEY (id_empresa) REFERENCES empresa(id_empresa)"
                        ))
                    except Exception:
                        pass
        # CPF: coluna nullable apenas para preservar funcionários antigos sem CPF.
        # A interface e o CRUD exigem CPF válido em novos cadastros/alterações.
        if "cpf" not in colunas:
            with engine.begin() as conn:
                if IS_SQLITE:
                    conn.execute(text("ALTER TABLE funcionario ADD COLUMN cpf VARCHAR(14) NULL"))
                else:
                    conn.execute(text("ALTER TABLE funcionario ADD COLUMN cpf VARCHAR(14) NULL"))
        # Índice único permite vários NULLs (registros antigos) e evita CPF duplicado.
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_funcionario_cpf ON funcionario (cpf)"))
        except Exception:
            # MySQL versões/índices existentes podem não aceitar IF NOT EXISTS.
            try:
                with engine.begin() as conn:
                    conn.execute(text("CREATE UNIQUE INDEX uq_funcionario_cpf ON funcionario (cpf)"))
            except Exception:
                pass

