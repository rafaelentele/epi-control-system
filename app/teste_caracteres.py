from app.config.database import engine

tabelas = [
    "produtos",
    "funcionario",
    "fornecedor",
    "categoria",
    "setor_loja",
    "entrada",
    "saida",
    "pedido_de_compra",
    "pedido_saida",
    "auditoria",
    "usuario",
]

with engine.connect() as c:
    for tabela in tabelas:
        try:
            colunas = c.exec_driver_sql(
                f"SHOW COLUMNS FROM {tabela}"
            ).fetchall()

            colunas_texto = [
                coluna[0]
                for coluna in colunas
                if "char" in coluna[1].lower()
                or "text" in coluna[1].lower()
            ]

            if not colunas_texto:
                continue

            encontrados = []

            for coluna in colunas_texto:
                try:
                    resultado = c.exec_driver_sql(
                        f"SELECT COUNT(*) FROM {tabela} "
                        f"WHERE `{coluna}` LIKE '%%??%%'"
                    ).fetchone()

                    quantidade = resultado[0]

                    if quantidade > 0:
                        encontrados.append(
                            f"{coluna}: {quantidade}"
                        )

                except Exception:
                    pass

            if encontrados:
                print(f"\n{tabela}:")
                for item in encontrados:
                    print(f"  {item}")

        except Exception as e:
            print(f"\nErro em {tabela}: {e}")