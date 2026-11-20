"""Cria um banco independente com registros inteiramente fictícios para testes."""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("EPICONTROL_SEED_DB_PATH", TEST_DIR / "epicontrol_teste.db")).expanduser().resolve()
BUILDING_DB_PATH = DB_PATH.with_name(f".{DB_PATH.stem}.building{DB_PATH.suffix}")

if DB_PATH.exists() or BUILDING_DB_PATH.exists():
    raise SystemExit("O banco de teste já existe. Ele não será substituído.")

sys.path.insert(0, str(ROOT / "app"))
os.environ["EPICONTROL_TEST_DB_PATH"] = str(BUILDING_DB_PATH)

from app.auth import (  # noqa: E402
    criar_primeiro_administrador,
    definir_usuario_atual,
)
from app.config.database import engine  # noqa: E402
from app.repositories.crud_simple import (  # noqa: E402
    criar_categoria,
    criar_empresa,
    criar_fornecedor,
    criar_funcionario,
    criar_setor_loja,
    criar_tamanho,
)
from app.repositories.crud_produtos import criar_produto  # noqa: E402
from app.repositories.crud_pedido_compra import criar_pedido_compra  # noqa: E402
from app.repositories.crud_entrada import criar_entrada  # noqa: E402
from app.repositories.crud_saida import criar_pedido_saida  # noqa: E402
from app.repositories.crud_usuario import listar_usuarios  # noqa: E402


def _cpf_valido(base: int) -> str:
    digitos = [int(ch) for ch in f"{base:09d}"]
    primeiro = (sum(d * peso for d, peso in zip(digitos, range(10, 1, -1))) * 10) % 11
    primeiro = 0 if primeiro == 10 else primeiro
    digitos.append(primeiro)
    segundo = (sum(d * peso for d, peso in zip(digitos, range(11, 1, -1))) * 10) % 11
    segundo = 0 if segundo == 10 else segundo
    return "".join(map(str, digitos)) + str(segundo)


def main() -> None:
    try:
        admin_id = criar_primeiro_administrador(
            "Administrador de Teste",
            "admin_teste",
            "Teste123",
            "Teste123",
        )
        definir_usuario_atual({"id_usuario": admin_id, "nome": "Administrador de Teste", "login": "admin_teste", "nivel_acesso": "Administrador", "permissoes": set()})

        empresas = [
            criar_empresa("Empresa Fictícia Alfa Ltda", "99000000000101"),
            criar_empresa("Empresa Fictícia Beta Ltda", "99000000000202"),
            criar_empresa("Empresa Fictícia Gama Ltda", "99000000000303"),
        ]
        funcionarios = []
        for empresa_idx, empresa in enumerate(empresas, start=1):
            for funcionario_idx in range(1, 6):
                base_cpf = 900_000_000 + empresa_idx * 1_000 + funcionario_idx
                funcionarios.append(criar_funcionario(
                    f"Funcionário Teste {empresa_idx}-{funcionario_idx:02d}",
                    _cpf_valido(base_cpf),
                    empresa.id_empresa,
                ))

        fornecedores = [
            criar_fornecedor(
                f"Fornecedor Fictício {idx:02d}",
                f"contato{idx:02d}@example.invalid",
            )
            for idx in range(1, 6)
        ]
        categoria_epi = criar_categoria("EPI")
        categoria_fardamento = criar_categoria("Fardamento")
        estoque = criar_setor_loja("Estoque de Teste")

        tamanhos = {}
        for nome in ("36", "37", "38", "39", "40", "41", "P", "M", "G", "GG", "XG", "7", "8", "9", "10", "UNICO"):
            tamanhos[nome] = criar_tamanho(nome)

        produtos = [
            criar_produto("Bota de Segurança Teste", categoria_epi.id_categoria, admin_id, "Registro fictício para teste de grade", estoque.id_setor_loja, 5, "CA-TESTE-BOTAS"),
            criar_produto("Camisa UV Teste", categoria_fardamento.id_categoria, admin_id, "Camisa UV; dado fictício", estoque.id_setor_loja, 4),
            criar_produto("Capacete de Segurança Teste", categoria_epi.id_categoria, admin_id, "CA ilustrativo, não oficial", estoque.id_setor_loja, 2, "CA-TESTE-001"),
            criar_produto("Luva de Proteção Teste", categoria_epi.id_categoria, admin_id, "CA ilustrativo, não oficial", estoque.id_setor_loja, 3, "CA-TESTE-002"),
            criar_produto("Óculos de Proteção Teste", categoria_epi.id_categoria, admin_id, "CA ilustrativo, não oficial; quinto pedido de teste", estoque.id_setor_loja, 2, "CA-TESTE-003"),
        ]

        pedidos_cfg = [
            # produto, quantidade, preço unitário, grade de entradas por tamanho
            (0, 30, 89.90, [("36", 3), ("37", 5), ("38", 7), ("39", 6), ("40", 5), ("41", 4)]),
            (1, 20, 42.50, [("P", 2), ("M", 4), ("G", 7), ("GG", 5), ("XG", 2)]),
            (2, 10, 55.00, [("M", 4), ("G", 6)]),
            (3, 16, 18.75, [("7", 3), ("8", 5), ("9", 5), ("10", 3)]),
            (4, 12, 12.40, [("UNICO", 12)]),
        ]
        for idx, (produto_idx, quantidade, preco, grade) in enumerate(pedidos_cfg):
            pedido = criar_pedido_compra(
                produtos[produto_idx].id_produto,
                quantidade,
                preco,
                fornecedores[idx].id_fornecedor,
                data_compra=date(2026, 11, 1 + idx),
                observacao="Pedido e quantidades fictícios para teste do Epi Control.",
            )
            for tamanho_nome, qtd in grade:
                criar_entrada(
                    pedido.id_pedido_compra,
                    tamanhos[tamanho_nome].id_tamanho,
                    qtd,
                    admin_id,
                    data_entrada=date(2026, 11, 10 + idx),
                    observacao="Entrada fictícia para testar estoque por tamanho.",
                )

        pedido_saida = criar_pedido_saida(
            funcionarios[0].id_funcionario,
            estoque.id_setor_loja,
            admin_id,
            [
                {"id_produto": produtos[0].id_produto, "id_tamanho": tamanhos["36"].id_tamanho, "quantidade": 1},
                {"id_produto": produtos[2].id_produto, "id_tamanho": tamanhos["M"].id_tamanho, "quantidade": 1},
            ],
            data_saida=date(2026, 11, 19),
            observacao="Saída fictícia para validar detalhes e geração de termo.",
        )

        engine.dispose()
        BUILDING_DB_PATH.replace(DB_PATH)
        print("Banco fictício criado:", DB_PATH)
        print("Empresas: 3 | Funcionários: 15 (5 por empresa) | Fornecedores: 5")
        print("Pedidos de compra: 5 | Entradas de estoque por tamanho: 18")
        print(f"Pedido de saída: 1 (2 itens) | Número: {pedido_saida.id_pedido_saida}")
        print("Admin de teste: admin_teste / Teste123")
    except Exception:
        engine.dispose()
        if BUILDING_DB_PATH.exists():
            BUILDING_DB_PATH.unlink()
        raise


if __name__ == "__main__":
    main()
