"""
Relatórios do sistema de fardamento.

Desde que a tabela saida passou a ter id_tamanho, o saldo (entradas
- saídas) pode ser calculado tanto por produto quanto por produto +
tamanho — veja estoque_atual() e estoque_saldo_por_tamanho().
"""

import os

from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.config.database import get_session
from app.models.models import (
    Entrada, Saida, PedidoSaida, Produto, Tamanho, Funcionario,
    Categoria, Fornecedor, SetorLoja, Usuario, AjusteEstoque,
)



# Limite usado pelo alerta de reposição. Pode ser ajustado sem alterar o banco
# definindo ESTOQUE_MINIMO_ALERTA no ambiente/.env. O padrão é 5 unidades.
ESTOQUE_MINIMO_ALERTA = int(os.getenv("ESTOQUE_MINIMO_ALERTA", "5"))


def estoque_atual() -> list[dict]:
    """Saldo (entradas - saídas) por produto."""
    session = get_session()
    try:
        entradas = dict(
            session.query(Entrada.id_produto, func.sum(Entrada.quantidade))
            .group_by(Entrada.id_produto)
            .all()
        )
        saidas = dict(
            session.query(Saida.id_produto, func.sum(Saida.quantidade))
            .group_by(Saida.id_produto)
            .all()
        )
        ajustes = dict(
            session.query(AjusteEstoque.id_produto, func.sum(AjusteEstoque.quantidade_ajuste))
            .group_by(AjusteEstoque.id_produto)
            .all()
        )

        todos_ids = set(entradas.keys()) | set(saidas.keys())
        produtos = {p.id_produto: p.nome for p in session.query(Produto).all()}

        resultado = []
        for id_produto in todos_ids:
            total_entrada = entradas.get(id_produto, 0)
            total_saida = saidas.get(id_produto, 0)
            total_ajuste = ajustes.get(id_produto, 0)
            resultado.append({
                "id_produto": id_produto,
                "produto": produtos.get(id_produto, f"(produto {id_produto})"),
                "total_entrada": total_entrada,
                "total_saida": total_saida,
                "total_ajuste": total_ajuste,
                "saldo": total_entrada - total_saida + total_ajuste,
            })

        resultado.sort(key=lambda x: x["produto"])
        return resultado
    finally:
        session.close()


def estoque_entradas_por_tamanho() -> list[dict]:
    """Total que entrou de cada produto, por tamanho."""
    session = get_session()
    try:
        linhas = (
            session.query(
                Entrada.id_produto,
                Entrada.id_tamanho,
                func.sum(Entrada.quantidade),
            )
            .group_by(Entrada.id_produto, Entrada.id_tamanho)
            .all()
        )
        produtos = {p.id_produto: p.nome for p in session.query(Produto).all()}
        tamanhos = {t.id_tamanho: t.nome for t in session.query(Tamanho).all()}

        resultado = [
            {
                "produto": produtos.get(id_produto, f"(produto {id_produto})"),
                "tamanho": tamanhos.get(id_tamanho, f"(tamanho {id_tamanho})"),
                "total_entrada": total,
            }
            for id_produto, id_tamanho, total in linhas
        ]
        resultado.sort(key=lambda x: (x["produto"], x["tamanho"]))
        return resultado
    finally:
        session.close()


def estoque_saldo_por_tamanho() -> list[dict]:
    """Saldo (entradas - saídas) por produto + tamanho."""
    session = get_session()
    try:
        entradas = {(p, t): q for p, t, q in
                    session.query(Entrada.id_produto, Entrada.id_tamanho, func.sum(Entrada.quantidade))
                    .group_by(Entrada.id_produto, Entrada.id_tamanho).all()}
        saidas = {(p, t): q for p, t, q in
                  session.query(Saida.id_produto, Saida.id_tamanho, func.sum(Saida.quantidade))
                  .group_by(Saida.id_produto, Saida.id_tamanho).all()}
        ajustes = {(p, t): q for p, t, q in
                   session.query(AjusteEstoque.id_produto, AjusteEstoque.id_tamanho, func.sum(AjusteEstoque.quantidade_ajuste))
                   .group_by(AjusteEstoque.id_produto, AjusteEstoque.id_tamanho).all()}

        produtos = {p.id_produto: p.nome for p in session.query(Produto).all()}
        tamanhos = {t.id_tamanho: t.nome for t in session.query(Tamanho).all()}

        todas_chaves = set(entradas.keys()) | set(saidas.keys()) | set(ajustes.keys())
        resultado = []
        for (id_produto, id_tamanho) in todas_chaves:
            total_entrada = entradas.get((id_produto, id_tamanho), 0)
            total_saida = saidas.get((id_produto, id_tamanho), 0)
            total_ajuste = ajustes.get((id_produto, id_tamanho), 0)
            resultado.append({
                "produto": produtos.get(id_produto, f"(produto {id_produto})"),
                "tamanho": tamanhos.get(id_tamanho, "(sem tamanho)") if id_tamanho else "(sem tamanho)",
                "total_entrada": total_entrada,
                "total_saida": total_saida,
                "total_ajuste": total_ajuste,
                "saldo": total_entrada - total_saida + total_ajuste,
            })
        resultado.sort(key=lambda x: (x["produto"], x["tamanho"]))
        return resultado
    finally:
        session.close()


def historico_funcionario(id_funcionario: int) -> list[dict]:
    """Todos os itens de saída (entregas) recebidos por um funcionário, com dados do pedido."""
    session = get_session()
    try:
        itens = (
            session.query(Saida)
            .join(PedidoSaida)
            .options(
                joinedload(Saida.produto),
                joinedload(Saida.pedido_saida).joinedload(PedidoSaida.setor_loja),
                joinedload(Saida.pedido_saida).joinedload(PedidoSaida.usuario),
            )
            .filter(PedidoSaida.id_funcionario == id_funcionario)
            .order_by(PedidoSaida.data_saida.desc())
            .all()
        )
        return [
            {
                "id_pedido_saida": s.pedido_saida.id_pedido_saida,
                "produto": s.produto.nome,
                "tamanho": s.tamanho.nome if s.tamanho else "-",
                "quantidade": s.quantidade,
                "setor_loja": s.pedido_saida.setor_loja.nome,
                "data_saida": s.pedido_saida.data_saida,
                "observacao": s.pedido_saida.observacao,
                "usuario": s.pedido_saida.usuario.nome,
            }
            for s in itens
        ]
    finally:
        session.close()


def historico_produto(id_produto: int) -> dict:
    """Todo o histórico (entradas e saídas) de um produto, em ordem cronológica."""
    session = get_session()
    try:
        entradas = (
            session.query(Entrada)
            .filter(Entrada.id_produto == id_produto)
            .order_by(Entrada.data_entrada)
            .all()
        )
        saidas = (
            session.query(Saida)
            .join(PedidoSaida)
            .options(
                joinedload(Saida.pedido_saida).joinedload(PedidoSaida.funcionario),
                joinedload(Saida.pedido_saida).joinedload(PedidoSaida.setor_loja),
            )
            .filter(Saida.id_produto == id_produto)
            .order_by(PedidoSaida.data_saida)
            .all()
        )

        movimentos = []
        for e in entradas:
            movimentos.append({
                "tipo": "entrada",
                "data": e.data_entrada,
                "quantidade": e.quantidade,
                "detalhe": f"tamanho {e.tamanho.nome}, fornecedor {e.fornecedor.nome}",
            })
        for s in saidas:
            movimentos.append({
                "tipo": "saida",
                "data": s.pedido_saida.data_saida,
                "quantidade": s.quantidade,
                "detalhe": f"entregue a {s.pedido_saida.funcionario.nome} ({s.pedido_saida.setor_loja.nome}) - pedido #{s.pedido_saida.id_pedido_saida}",
            })
        ajustes = (
            session.query(AjusteEstoque)
            .options(joinedload(AjusteEstoque.tamanho), joinedload(AjusteEstoque.usuario))
            .filter(AjusteEstoque.id_produto == id_produto)
            .order_by(AjusteEstoque.data_ajuste)
            .all()
        )
        for a in ajustes:
            movimentos.append({
                "tipo": "ajuste",
                "data": a.data_ajuste,
                "quantidade": a.quantidade_ajuste,
                "detalhe": f"ajuste físico no tamanho {a.tamanho.nome}: {a.estoque_anterior} -> {a.estoque_posterior} ({a.motivo})",
            })

        movimentos.sort(key=lambda m: (m["data"] is None, m["data"]))

        return {
            "produto": entradas[0].produto.nome if entradas else (saidas[0].produto.nome if saidas else None),
            "movimentos": movimentos,
        }
    finally:
        session.close()


def listagem_geral() -> dict:
    """Junta id + nome de todas as tabelas de cadastro, pronto pra imprimir/copiar."""
    session = get_session()
    try:
        categorias = [(c.id_categoria, c.nome) for c in session.query(Categoria).order_by(Categoria.id_categoria).all()]
        tamanhos = [(t.id_tamanho, t.nome) for t in session.query(Tamanho).order_by(Tamanho.id_tamanho).all()]
        fornecedores = [
            (f.id_fornecedor, f.nome, f.contato)
            for f in session.query(Fornecedor).order_by(Fornecedor.id_fornecedor).all()
        ]
        funcionarios = [
            (f.id_funcionario, f.nome) for f in session.query(Funcionario).order_by(Funcionario.id_funcionario).all()
        ]
        setores_loja = [
            (s.id_setor_loja, s.nome) for s in session.query(SetorLoja).order_by(SetorLoja.id_setor_loja).all()
        ]
        produtos = [
            (p.id_produto, p.nome, p.categoria.nome if p.categoria else "-")
            for p in session.query(Produto).options(joinedload(Produto.categoria)).order_by(Produto.id_produto).all()
        ]
        usuarios = [
            (u.id_usuario, u.nome, u.login, u.nivel_acesso)
            for u in session.query(Usuario).order_by(Usuario.id_usuario).all()
        ]

        return {
            "categorias": categorias,
            "tamanhos": tamanhos,
            "fornecedores": fornecedores,
            "funcionarios": funcionarios,
            "setores_loja": setores_loja,
            "produtos": produtos,
            "usuarios": usuarios,
        }
    finally:
        session.close()


def formatar_listagem_geral(dados: dict) -> str:
    """Transforma o dicionário de listagem_geral() num texto simples, pronto pra imprimir ou copiar."""
    linhas = ["===== LISTAGEM GERAL - SISTEMA DE FARDAMENTO =====", ""]

    linhas.append("--- Categorias ---")
    linhas += [f"{id_}: {nome}" for id_, nome in dados["categorias"]] or ["(nenhuma cadastrada)"]
    linhas.append("")

    linhas.append("--- Tamanhos ---")
    linhas += [f"{id_}: {nome}" for id_, nome in dados["tamanhos"]] or ["(nenhum cadastrado)"]
    linhas.append("")

    linhas.append("--- Fornecedores ---")
    linhas += [
        f"{id_}: {nome}" + (f" | contato: {contato}" if contato else "")
        for id_, nome, contato in dados["fornecedores"]
    ] or ["(nenhum cadastrado)"]
    linhas.append("")

    linhas.append("--- Funcionários ---")
    linhas += [f"{id_}: {nome}" for id_, nome in dados["funcionarios"]] or ["(nenhum cadastrado)"]
    linhas.append("")

    linhas.append("--- Setores/Lojas ---")
    linhas += [f"{id_}: {nome}" for id_, nome in dados["setores_loja"]] or ["(nenhum cadastrado)"]
    linhas.append("")

    linhas.append("--- Produtos ---")
    linhas += [f"{id_}: {nome} | categoria: {categoria}" for id_, nome, categoria in dados["produtos"]] or ["(nenhum cadastrado)"]
    linhas.append("")

    linhas.append("--- Usuários ---")
    linhas += [
        f"{id_}: {nome} | login: {login} | permissão: {nivel}"
        for id_, nome, login, nivel in dados["usuarios"]
    ] or ["(nenhum cadastrado)"]

    return "\n".join(linhas)


# Ordem "natural" de tamanho pra exibição (letras primeiro, depois números
# crescentes), em vez de ordem alfabética pura (onde "35" viria antes de "G").
TAMANHO_ORDEM = ["PP", "P", "M", "G", "GG", "XG", "U",
                  "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "48", "52"]


def _ordenar_tamanhos(tamanhos):
    def chave(t):
        if t.nome in TAMANHO_ORDEM:
            return (0, TAMANHO_ORDEM.index(t.nome))
        return (1, t.nome)
    return sorted(tamanhos, key=chave)


def estoque_pivot():
    """Estoque por produto/tamanho; status usa o total do produto versus estoque mínimo."""
    session = get_session()
    try:
        tamanhos = _ordenar_tamanhos(session.query(Tamanho).all())
        nomes_tamanho = [t.nome for t in tamanhos]
        id_para_nome_tamanho = {t.id_tamanho: t.nome for t in tamanhos}
        entradas = {(p, t): int(q or 0) for p, t, q in session.query(Entrada.id_produto, Entrada.id_tamanho, func.sum(Entrada.quantidade)).group_by(Entrada.id_produto, Entrada.id_tamanho).all()}
        saidas = {(p, t): int(q or 0) for p, t, q in session.query(Saida.id_produto, Saida.id_tamanho, func.sum(Saida.quantidade)).group_by(Saida.id_produto, Saida.id_tamanho).all()}
        ajustes = {(p, t): int(q or 0) for p, t, q in session.query(AjusteEstoque.id_produto, AjusteEstoque.id_tamanho, func.sum(AjusteEstoque.quantidade_ajuste)).group_by(AjusteEstoque.id_produto, AjusteEstoque.id_tamanho).all()}
        produtos = session.query(Produto).options(joinedload(Produto.setor_padrao)).order_by(Produto.nome).all()
        linhas = []
        for p in produtos:
            saldos = {nome: 0 for nome in nomes_tamanho}
            geral = 0
            for id_tamanho, nome_tamanho in id_para_nome_tamanho.items():
                saldo = (
                    entradas.get((p.id_produto, id_tamanho), 0)
                    - saidas.get((p.id_produto, id_tamanho), 0)
                    + ajustes.get((p.id_produto, id_tamanho), 0)
                )
                saldos[nome_tamanho] = saldo
                geral += saldo
            estoque_minimo = int(p.estoque_minimo or 0)
            if geral <= 0 and estoque_minimo > 0:
                status = "ZERADO"
            elif geral <= estoque_minimo:
                status = "ESTOQUE BAIXO"
            else:
                status = "NORMAL"
            linhas.append({
                "id_produto": p.id_produto, "produto": p.nome,
                "setor": p.setor_padrao.nome if p.setor_padrao else "-",
                "saldos": saldos, "geral": geral,
                "estoque_minimo": estoque_minimo, "status": status,
            })
        return nomes_tamanho, linhas
    finally:
        session.close()

def formatar_estoque_pivot() -> str:
    """Versão em texto simples (largura fixa) da tabela produto x tamanho, pro terminal."""
    nomes_tamanho, linhas = estoque_pivot()
    if not linhas:
        return "(nenhuma movimentação registrada ainda)"

    largura_produto = max([len(l["produto"]) for l in linhas] + [len("PRODUTO")]) + 2
    largura_setor = max([len(l["setor"]) for l in linhas] + [len("SETOR")]) + 2
    largura_col = 5

    cabecalho = "PRODUTO".ljust(largura_produto) + "SETOR".ljust(largura_setor)
    cabecalho += "".join(nome.rjust(largura_col) for nome in nomes_tamanho) + "GERAL".rjust(largura_col + 2)
    linhas_texto = [cabecalho, "-" * len(cabecalho)]

    for l in linhas:
        linha = l["produto"].ljust(largura_produto) + l["setor"].ljust(largura_setor)
        linha += "".join(str(l["saldos"][nome]).rjust(largura_col) for nome in nomes_tamanho)
        linha += str(l["geral"]).rjust(largura_col + 2)
        linhas_texto.append(linha)

    return "\n".join(linhas_texto)


def historico_operacoes(limite=500, operacao=None, id_usuario=None):
    from app.repositories.crud_auditoria import listar_auditoria
    return listar_auditoria(limite=limite, operacao=operacao, id_usuario=id_usuario)
