"""Adiciona senha aos usuarios existentes sem apagar os dados.

Os usuarios que ja existiam recebem temporariamente a senha 123456.
Troque a senha de cada usuario em Cadastro e Configuracao > Usuarios.
"""

from sqlalchemy import inspect, text
from app.config.database import engine, get_session
from app.auth import gerar_senha_hash
from app.models.models import Usuario


if __name__ == "__main__":
    inspector = inspect(engine)
    colunas = {c["name"] for c in inspector.get_columns("usuario")}
    if "senha_hash" not in colunas:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE usuario ADD COLUMN senha_hash VARCHAR(255) NULL"))
        print("Coluna senha_hash criada.")
    else:
        print("Coluna senha_hash ja existe.")

    session = get_session()
    try:
        senha_inicial = gerar_senha_hash("123456")
        usuarios = session.query(Usuario).all()
        atualizados = 0
        for usuario in usuarios:
            if not usuario.senha_hash:
                usuario.senha_hash = senha_inicial
                atualizados += 1
        session.commit()
        print(f"Migracao concluida. {atualizados} usuario(s) receberam a senha temporaria 123456.")
        print("IMPORTANTE: altere a senha de cada usuario em Cadastro e Configuracao > Usuarios.")
    finally:
        session.close()
