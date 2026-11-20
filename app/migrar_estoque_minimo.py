"""Migração segura e não destrutiva: adiciona estoque_minimo à tabela produtos."""
from sqlalchemy import text
from app.config.database import engine

def main():
    with engine.begin() as conn:
        existe = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'produtos'
              AND COLUMN_NAME = 'estoque_minimo'
        """)).scalar()
        if int(existe or 0) > 0:
            print("A coluna estoque_minimo já existe. Nenhuma alteração foi feita.")
            return
        conn.execute(text("ALTER TABLE produtos ADD COLUMN estoque_minimo INT NOT NULL DEFAULT 0 AFTER descricao"))
        print("Coluna estoque_minimo criada com sucesso. Produtos existentes receberam mínimo 0.")

if __name__ == "__main__":
    main()
