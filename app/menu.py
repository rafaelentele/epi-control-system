"""
Menu interativo do Epi Control.
Rode com: python menu.py

Um menu de texto simples, com submenus pra cada tabela. Serve como
primeira "cara" do sistema, antes de pensar numa interface gráfica.
"""

from datetime import date, datetime
from getpass import getpass

from app.repositories.crud_simple import (
    criar_categoria, listar_categorias, atualizar_categoria, excluir_categoria,
    criar_fornecedor, listar_fornecedores, atualizar_fornecedor, excluir_fornecedor,
    criar_funcionario, listar_funcionarios, atualizar_funcionario, excluir_funcionario,
    criar_setor_loja, listar_setores_loja, atualizar_setor_loja, excluir_setor_loja,
    criar_tamanho, listar_tamanhos, atualizar_tamanho, excluir_tamanho,
)
from app.repositories.crud_produtos import (
    criar_produto, listar_produtos, atualizar_produto, excluir_produto,
)
from app.repositories.crud_entrada import (
    criar_entrada, listar_entradas, atualizar_entrada, excluir_entrada,
)
from app.repositories.crud_pedido_compra import (
    criar_pedido_compra, listar_pedidos_compra, atualizar_pedido_compra,
    excluir_pedido_compra, pesquisar_pedidos_compra,
)
from app.repositories.crud_saida import (
    criar_pedido_saida, listar_pedidos_saida, buscar_pedido_saida,
    atualizar_pedido_saida, excluir_pedido_saida,
)
from app.repositories.relatorios import (
    estoque_atual, estoque_entradas_por_tamanho, estoque_saldo_por_tamanho,
    historico_funcionario, historico_produto, listagem_geral, formatar_listagem_geral,
    formatar_estoque_pivot,
)
from app.repositories.crud_usuario import (
    criar_usuario, listar_usuarios, atualizar_usuario, excluir_usuario, NIVEIS_VALIDOS,
)
from app.auth import (
    garantir_estrutura_autenticacao,
    precisa_configurar_administrador,
    criar_primeiro_administrador,
    autenticar,
    definir_usuario_atual,
)


# ------------------------------------------------------------
# Utilidades de entrada de dados
# ------------------------------------------------------------
def ler_int(mensagem: str, opcional: bool = False):
    while True:
        valor = input(mensagem).strip()
        if opcional and valor == "":
            return None
        try:
            return int(valor)
        except ValueError:
            print("  Digite um número válido.")


def ler_texto(mensagem: str, opcional: bool = False):
    valor = input(mensagem).strip()
    if opcional and valor == "":
        return None
    return valor


def ler_data(mensagem: str):
    valor = input(f"{mensagem} (dd/mm/aaaa, Enter para hoje): ").strip()
    if valor == "":
        return date.today()
    try:
        return datetime.strptime(valor, "%d/%m/%Y").date()
    except ValueError:
        print("  Data inválida, usando a data de hoje.")
        return date.today()


def pausar():
    input("\nPressione Enter para continuar...")


# ------------------------------------------------------------
# Submenu genérico para as tabelas simples (nome, e opcionalmente contato)
# ------------------------------------------------------------
def menu_entidade_simples(titulo, criar_fn, listar_fn, atualizar_fn, excluir_fn, tem_contato=False):
    while True:
        print(f"\n--- {titulo} ---")
        print("1. Listar")
        print("2. Cadastrar")
        print("3. Editar")
        print("4. Excluir")
        print("0. Voltar")
        opcao = input("Escolha: ").strip()

        if opcao == "1":
            itens = listar_fn()
            if not itens:
                print("Nada cadastrado ainda.")
            else:
                id_attr = [a for a in vars(itens[0]) if a.startswith("id_")][0]
                itens.sort(key=lambda item: getattr(item, id_attr))
                largura = max(len(str(getattr(item, id_attr))) for item in itens)
                for item in itens:
                    extra = f" | {item.contato}" if tem_contato and getattr(item, "contato", None) else ""
                    print(f"  {getattr(item, id_attr):>{largura}}: {item.nome}{extra}")
            pausar()

        elif opcao == "2":
            nome = ler_texto("Nome: ")
            if tem_contato:
                contato = ler_texto("Contato (Enter para pular): ", opcional=True)
                novo = criar_fn(nome, contato)
            else:
                novo = criar_fn(nome)
            id_attr = [a for a in vars(novo) if a.startswith("id_")][0]
            print(f"Cadastrado com sucesso! id={getattr(novo, id_attr)}")
            pausar()

        elif opcao == "3":
            id_item = ler_int("Id para editar: ")
            novo_nome = ler_texto("Novo nome (Enter para manter): ", opcional=True)
            if tem_contato:
                novo_contato = ler_texto("Novo contato (Enter para manter): ", opcional=True)
                resultado = atualizar_fn(id_item, novo_nome, novo_contato)
            else:
                if novo_nome is None:
                    print("Nada a alterar.")
                    pausar()
                    continue
                resultado = atualizar_fn(id_item, novo_nome)
            print("Atualizado!" if resultado else "Id não encontrado.")
            pausar()

        elif opcao == "4":
            id_item = ler_int("Id para excluir: ")
            confirmar = input("Confirma exclusão? (s/n): ").strip().lower()
            if confirmar == "s":
                sucesso = excluir_fn(id_item)
                print("Excluído!" if sucesso else "Id não encontrado.")
            pausar()

        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


# ------------------------------------------------------------
# Submenu de Produtos
# ------------------------------------------------------------
def menu_produtos():
    while True:
        print("\n--- Produtos ---")
        print("1. Listar")
        print("2. Cadastrar")
        print("3. Editar")
        print("4. Excluir")
        print("0. Voltar")
        opcao = input("Escolha: ").strip()

        if opcao == "1":
            produtos = listar_produtos()
            if not produtos:
                print("Nenhum produto cadastrado ainda.")
            for p in produtos:
                cat = p.categoria.nome if p.categoria else "-"
                setor = p.setor_padrao.nome if p.setor_padrao else "-"
                desc = f" | descrição: {p.descricao}" if p.descricao else ""
                print(f"  {p.id_produto}: {p.nome} | categoria: {cat} | setor padrão: {setor}{desc}")
            pausar()

        elif opcao == "2":
            nome = ler_texto("Nome do produto: ")
            id_categoria = ler_int("Id da categoria: ")
            id_usuario = ler_int("Id do usuário (quem está cadastrando): ")
            id_setor_padrao = ler_int("Id do setor padrão (Enter para pular): ", opcional=True)
            descricao = ler_texto("Descrição (Enter para pular): ", opcional=True)
            try:
                novo = criar_produto(nome, id_categoria, id_usuario, descricao, id_setor_padrao=id_setor_padrao)
                print(f"Cadastrado! id={novo.id_produto}")
            except ValueError as e:
                print(f"Erro: {e}")
            pausar()

        elif opcao == "3":
            id_produto = ler_int("Id do produto para editar: ")
            nome = ler_texto("Novo nome (Enter para manter): ", opcional=True)
            id_categoria = ler_int("Nova id de categoria (Enter para manter): ", opcional=True)
            id_setor_padrao = ler_int("Novo id de setor padrão (Enter para manter): ", opcional=True)
            descricao = ler_texto("Nova descrição (Enter para manter): ", opcional=True)
            try:
                resultado = atualizar_produto(id_produto, nome=nome, id_categoria=id_categoria,
                                               descricao=descricao, id_setor_padrao=id_setor_padrao)
                print("Atualizado!" if resultado else "Id não encontrado.")
            except ValueError as e:
                print(f"Erro: {e}")
            pausar()

        elif opcao == "4":
            id_produto = ler_int("Id do produto para excluir: ")
            confirmar = input("Confirma exclusão? (s/n): ").strip().lower()
            if confirmar == "s":
                sucesso = excluir_produto(id_produto)
                print("Excluído!" if sucesso else "Id não encontrado.")
            pausar()

        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


# ------------------------------------------------------------
# Submenu de Entrada (estoque)
# ------------------------------------------------------------
def menu_pedido_compra():
    while True:
        print("\n--- Pedido de Compra ---")
        print("1. Listar")
        print("2. Cadastrar")
        print("3. Editar")
        print("4. Excluir")
        print("0. Voltar")
        opcao = input("Escolha: ").strip()

        if opcao == "1":
            pedidos = listar_pedidos_compra()
            if not pedidos:
                print("Nenhum pedido de compra cadastrado ainda.")
            for p in pedidos:
                preco = float(p.preco) if p.preco is not None else 0
                print(
                    f"  {p.id_pedido_compra}: {p.produto.nome} | qtd: {p.quantidade} | "
                    f"vl. unit.: R$ {preco:.2f} | fornecedor: {p.fornecedor.nome} | data: {p.data_compra}"
                )
            pausar()

        elif opcao == "2":
            id_produto = ler_int("Id do produto: ")
            quantidade = ler_int("Quantidade: ")
            preco = ler_texto("Valor unitário (ex: 49.90): ")
            id_fornecedor = ler_int("Id do fornecedor: ")
            data_compra = ler_data("Data da compra")
            observacao = ler_texto("Observação (Enter para pular): ", opcional=True)
            try:
                novo = criar_pedido_compra(id_produto, quantidade, float(preco.replace(",", ".")), id_fornecedor,
                                            data_compra=data_compra, observacao=observacao)
                print(f"Cadastrado! número do pedido: {novo.id_pedido_compra}")
            except ValueError as e:
                print(f"Erro: {e}")
            pausar()

        elif opcao == "3":
            id_pedido = ler_int("Número do pedido para editar: ")
            quantidade = ler_int("Nova quantidade (Enter para manter): ", opcional=True)
            preco_texto = ler_texto("Novo valor unitário (Enter para manter): ", opcional=True)
            preco = float(preco_texto.replace(",", ".")) if preco_texto else None
            observacao = ler_texto("Nova observação (Enter para manter): ", opcional=True)
            resultado = atualizar_pedido_compra(id_pedido, quantidade=quantidade, preco=preco, observacao=observacao)
            print("Atualizado!" if resultado else "Pedido não encontrado.")
            pausar()

        elif opcao == "4":
            id_pedido = ler_int("Número do pedido para excluir: ")
            confirmar = input("Confirma exclusão? (s/n): ").strip().lower()
            if confirmar == "s":
                try:
                    sucesso = excluir_pedido_compra(id_pedido)
                    print("Excluído!" if sucesso else "Pedido não encontrado.")
                except Exception as e:
                    print(f"Não foi possível excluir (provavelmente há entradas ligadas a ele): {e}")
            pausar()

        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


def menu_entrada():
    while True:
        print("\n--- Entrada de Estoque ---")
        print("1. Listar")
        print("2. Registrar entrada")
        print("3. Editar")
        print("4. Excluir")
        print("0. Voltar")
        opcao = input("Escolha: ").strip()

        if opcao == "1":
            entradas = listar_entradas()
            if not entradas:
                print("Nenhuma entrada registrada ainda.")
            for e in entradas:
                print(
                    f"  {e.id_entrada}: pedido #{e.id_pedido_compra} - {e.produto.nome} | tamanho: {e.tamanho.nome} "
                    f"| qtd: {e.quantidade} | fornecedor: {e.fornecedor.nome} | data: {e.data_entrada}"
                )
            pausar()

        elif opcao == "2":
            id_pedido_compra = ler_int("Número do pedido de compra: ")
            id_tamanho = ler_int("Id do tamanho: ")
            quantidade = ler_int("Quantidade recebida: ")
            id_usuario = ler_int("Id do usuário: ")
            data_entrada = ler_data("Data da entrada")
            observacao = ler_texto("Observação (Enter para pular): ", opcional=True)
            try:
                nova = criar_entrada(
                    id_pedido_compra, id_tamanho, quantidade, id_usuario,
                    data_entrada=data_entrada, observacao=observacao,
                )
                print(f"Registrada! id={nova.id_entrada} (produto e fornecedor vieram do pedido #{id_pedido_compra})")
            except ValueError as e:
                print(f"Erro: {e}")
            pausar()

        elif opcao == "3":
            id_entrada = ler_int("Id da entrada para editar: ")
            quantidade = ler_int("Nova quantidade (Enter para manter): ", opcional=True)
            observacao = ler_texto("Nova observação (Enter para manter): ", opcional=True)
            try:
                resultado = atualizar_entrada(id_entrada, quantidade=quantidade, observacao=observacao)
                print("Atualizada!" if resultado else "Id não encontrado.")
            except ValueError as e:
                print(f"Erro: {e}")
            pausar()

        elif opcao == "4":
            id_entrada = ler_int("Id da entrada para excluir: ")
            confirmar = input("Confirma exclusão? (s/n): ").strip().lower()
            if confirmar == "s":
                sucesso = excluir_entrada(id_entrada)
                print("Excluída!" if sucesso else "Id não encontrado.")
            pausar()

        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


# ------------------------------------------------------------
# Submenu de Saída (pedido com vários itens)
# ------------------------------------------------------------
def imprimir_pedido_saida(pedido):
    print(
        f"\nPedido #{pedido.id_pedido_saida} | {pedido.funcionario.nome} | "
        f"setor: {pedido.setor_loja.nome} | data: {pedido.data_saida} | baixa dada por: {pedido.usuario.nome}"
    )
    if pedido.observacao:
        print(f"  Observação: {pedido.observacao}")
    if not pedido.itens:
        print("  (sem itens)")
    for item in pedido.itens:
        print(f"  - item {item.id_saida}: {item.quantidade}x {item.produto.nome} (tam. {item.tamanho.nome if item.tamanho else '-'})")


def menu_saida():
    while True:
        print("\n--- Saída (Pedidos de Entrega de Fardamento) ---")
        print("1. Listar pedidos de saída")
        print("2. Registrar novo pedido de saída")
        print("3. Consultar pedido por número")
        print("4. Editar dados do pedido (bloqueado: pedido fechado)")
        print("5. Excluir pedido inteiro")
        print("0. Voltar")
        opcao = input("Escolha: ").strip()

        if opcao == "1":
            pedidos = listar_pedidos_saida()
            if not pedidos:
                print("Nenhum pedido de saída registrado ainda.")
            for p in pedidos:
                imprimir_pedido_saida(p)
            pausar()

        elif opcao == "2":
            id_funcionario = ler_int("Id do funcionário: ")
            id_setor_loja = ler_int("Id do setor/loja: ")
            id_usuario = ler_int("Id do usuário: ")
            data_saida = ler_data("Data da saída")
            observacao = ler_texto("Observação do pedido (Enter para pular): ", opcional=True)

            itens = []
            while True:
                print(f"\n-- Item {len(itens) + 1} do pedido --")
                id_produto = ler_int("Id do produto: ")
                id_tamanho = ler_int("Id do tamanho: ")
                quantidade = ler_int("Quantidade: ")
                itens.append({"id_produto": id_produto, "id_tamanho": id_tamanho, "quantidade": quantidade})

                mais = input("Deseja adicionar mais itens a esse pedido? (s/n): ").strip().lower()
                if mais != "s":
                    break

            try:
                pedido = criar_pedido_saida(
                    id_funcionario, id_setor_loja, id_usuario, itens,
                    data_saida=data_saida, observacao=observacao,
                )
                print(f"\nPedido registrado! número: {pedido.id_pedido_saida}, com {len(itens)} item(ns).")
            except ValueError as e:
                print(f"Erro: {e}")
            pausar()

        elif opcao == "3":
            id_pedido = ler_int("Número do pedido: ")
            pedido = buscar_pedido_saida(id_pedido)
            if pedido is None:
                print("Pedido não encontrado.")
            else:
                imprimir_pedido_saida(pedido)
            pausar()

        elif opcao == "4":
            id_pedido = ler_int("Número do pedido para editar: ")
            id_setor_loja = ler_int("Novo id de setor/loja (Enter para manter): ", opcional=True)
            data_saida_texto = input("Nova data (dd/mm/aaaa, Enter para manter): ").strip()
            nova_data = None
            if data_saida_texto:
                try:
                    nova_data = datetime.strptime(data_saida_texto, "%d/%m/%Y").date()
                except ValueError:
                    print("  Data inválida, mantendo a anterior.")
            observacao = ler_texto("Nova observação (Enter para manter): ", opcional=True)
            try:
                resultado = atualizar_pedido_saida(id_pedido, id_setor_loja=id_setor_loja, data_saida=nova_data, observacao=observacao)
                print("Atualizado!" if resultado else "Pedido não encontrado.")
            except ValueError as e:
                print(f"Erro: {e}")
            pausar()

        elif opcao == "5":
            id_pedido = ler_int("Número do pedido para excluir (todos os itens vão junto): ")
            confirmar = input("Confirma exclusão do pedido inteiro? (s/n): ").strip().lower()
            if confirmar == "s":
                sucesso = excluir_pedido_saida(id_pedido)
                print("Excluído!" if sucesso else "Pedido não encontrado.")
            pausar()

        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


# ------------------------------------------------------------
# Submenu de Relatórios
# ------------------------------------------------------------
def menu_relatorios():
    while True:
        print("\n--- Relatórios ---")
        print("1. Estoque atual (saldo por produto)")
        print("2. Estoque atual por tamanho (saldo)")
        print("3. Status do estoque (tabela produto x tamanho)")
        print("4. Entradas por tamanho (bruto, sem descontar saída)")
        print("5. Histórico de um funcionário")
        print("6. Histórico de um produto")
        print("7. Pesquisa de registro de compra")
        print("8. Listagem geral (tudo, para imprimir/copiar)")
        print("0. Voltar")
        opcao = input("Escolha: ").strip()

        if opcao == "1":
            linhas = estoque_atual()
            if not linhas:
                print("Nenhuma movimentação registrada ainda.")
            for l in linhas:
                print(f"  {l['produto']}: entrou {l['total_entrada']}, saiu {l['total_saida']}, saldo = {l['saldo']}")
            pausar()

        elif opcao == "2":
            linhas = estoque_saldo_por_tamanho()
            if not linhas:
                print("Nenhuma movimentação registrada ainda.")
            for l in linhas:
                print(f"  {l['produto']} | tamanho {l['tamanho']}: entrou {l['total_entrada']}, saiu {l['total_saida']}, saldo = {l['saldo']}")
            pausar()

        elif opcao == "3":
            print()
            print(formatar_estoque_pivot())
            print()
            pausar()

        elif opcao == "4":
            linhas = estoque_entradas_por_tamanho()
            if not linhas:
                print("Nenhuma entrada registrada ainda.")
            for l in linhas:
                print(f"  {l['produto']} | tamanho {l['tamanho']}: {l['total_entrada']} unidades")
            pausar()

        elif opcao == "5":
            id_funcionario = ler_int("Id do funcionário: ")
            movimentos = historico_funcionario(id_funcionario)
            if not movimentos:
                print("Nenhuma saída registrada para esse funcionário.")
            for m in movimentos:
                obs = f" | obs: {m['observacao']}" if m["observacao"] else ""
                print(f"  {m['data_saida']}: pedido #{m['id_pedido_saida']} - recebeu {m['quantidade']}x {m['produto']} (tam. {m['tamanho']}) em {m['setor_loja']} | baixa dada por: {m['usuario']}{obs}")
            pausar()

        elif opcao == "6":
            id_produto = ler_int("Id do produto: ")
            resultado = historico_produto(id_produto)
            if not resultado["movimentos"]:
                print("Nenhuma movimentação registrada para esse produto.")
            else:
                print(f"Histórico de: {resultado['produto']}")
                for m in resultado["movimentos"]:
                    sinal = "+" if m["tipo"] == "entrada" else "-"
                    print(f"  {m['data']}: {sinal}{m['quantidade']} ({m['detalhe']})")
            pausar()

        elif opcao == "7":
            id_pedido = ler_int("Número do pedido (Enter para pular): ", opcional=True)
            id_produto = ler_int("Id do produto (Enter para pular): ", opcional=True)
            id_fornecedor = ler_int("Id do fornecedor (Enter para pular): ", opcional=True)
            resultados = pesquisar_pedidos_compra(id_produto=id_produto, id_fornecedor=id_fornecedor, id_pedido_compra=id_pedido)
            if not resultados:
                print("Nenhum pedido de compra encontrado com esses filtros.")
            for p in resultados:
                preco = float(p.preco) if p.preco is not None else 0
                total = preco * p.quantidade
                print(
                    f"  {p.id_pedido_compra}: {p.produto.nome} | qtd: {p.quantidade} | vl. unit.: R$ {preco:.2f} "
                    f"| vl. total: R$ {total:.2f} | fornecedor: {p.fornecedor.nome} | data: {p.data_compra}"
                )
            pausar()

        elif opcao == "8":
            texto = formatar_listagem_geral(listagem_geral())
            print()
            print(texto)
            print()
            salvar = input("Salvar isso em um arquivo .txt pra imprimir/copiar depois? (s/n): ").strip().lower()
            if salvar == "s":
                nome_arquivo = f"listagem_geral_{date.today().strftime('%Y-%m-%d')}.txt"
                with open(nome_arquivo, "w", encoding="utf-8") as arquivo:
                    arquivo.write(texto)
                print(f"Salvo como '{nome_arquivo}' na pasta do projeto.")
            pausar()

        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


# ------------------------------------------------------------
# Submenu de Configurações (usuários e permissões)
# ------------------------------------------------------------
def menu_configuracoes():
    while True:
        print("\n--- Configurações: Usuários e Permissões ---")
        print("1. Listar usuários")
        print("2. Cadastrar usuário")
        print("3. Editar usuário (nome/login/senha/permissão)")
        print("4. Excluir usuário")
        print("0. Voltar")
        opcao = input("Escolha: ").strip()

        if opcao == "1":
            usuarios = listar_usuarios()
            if not usuarios:
                print("Nenhum usuário cadastrado ainda.")
            for u in usuarios:
                print(f"  {u.id_usuario}: {u.nome} | login: {u.login} | permissão: {u.nivel_acesso}")
            pausar()

        elif opcao == "2":
            nome = ler_texto("Nome completo: ")
            login = ler_texto("Login (único, sem espaço): ")
            senha = getpass("Senha (mínimo 8 caracteres, letras e números): ")
            print(f"Permissões disponíveis: {', '.join(NIVEIS_VALIDOS)}")
            nivel = ler_texto("Permissão (Enter para 'Operador'): ", opcional=True) or "Operador"
            if nivel not in NIVEIS_VALIDOS:
                print(f"Permissão inválida, usando 'Operador'. (opções válidas: {', '.join(NIVEIS_VALIDOS)})")
                nivel = "Operador"
            try:
                novo = criar_usuario(nome, login, nivel, senha)
                print(f"Cadastrado! id={novo.id_usuario}")
            except Exception as e:
                print(f"Erro: {e}")
            pausar()

        elif opcao == "3":
            id_usuario = ler_int("Id do usuário para editar: ")
            nome = ler_texto("Novo nome (Enter para manter): ", opcional=True)
            login_novo = ler_texto("Novo login (Enter para manter): ", opcional=True)
            senha_nova = getpass("Nova senha (Enter para manter): ")
            print(f"Permissões disponíveis: {', '.join(NIVEIS_VALIDOS)}")
            nivel = ler_texto("Nova permissão (Enter para manter): ", opcional=True)
            if nivel is not None and nivel not in NIVEIS_VALIDOS:
                print(f"Permissão inválida, mantendo a anterior. (opções válidas: {', '.join(NIVEIS_VALIDOS)})")
                nivel = None
            try:
                resultado = atualizar_usuario(
                    id_usuario,
                    nome=nome,
                    login=login_novo,
                    nivel_acesso=nivel,
                    senha=senha_nova or None,
                )
                print("Atualizado!" if resultado else "Id não encontrado.")
            except Exception as e:
                print(f"Erro: {e}")
            pausar()

        elif opcao == "4":
            id_usuario = ler_int("Id do usuário para excluir: ")
            confirmar = input("Confirma exclusão? (s/n): ").strip().lower()
            if confirmar == "s":
                try:
                    sucesso = excluir_usuario(id_usuario)
                    print("Excluído!" if sucesso else "Id não encontrado.")
                except Exception as e:
                    print(f"Erro: {e}")
            pausar()

        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


# ------------------------------------------------------------
# Menu principal
# ------------------------------------------------------------
def main():
    try:
        garantir_estrutura_autenticacao()
        if precisa_configurar_administrador():
            print("\nPrimeiro acesso: crie o administrador do Epi Control.")
            nome = input("Nome: ").strip()
            login = input("Login: ").strip()
            senha = getpass("Senha (mínimo 8 caracteres, letras e números): ")
            confirmacao = getpass("Confirme a senha: ")
            criar_primeiro_administrador(nome, login, senha, confirmacao)
        login = input("Login: ").strip()
        senha = getpass("Senha: ")
        usuario = autenticar(login, senha)
        if usuario is None:
            print("Login ou senha inválidos. Encerrando.")
            return
        definir_usuario_atual(usuario)
    except (ValueError, PermissionError) as e:
        print(f"Não foi possível iniciar: {e}")
        return

    while True:
        print("\n===== EPI CONTROL =====")
        print("1. Categorias")
        print("2. Fornecedores")
        print("3. Tamanhos")
        print("4. Funcionários")
        print("5. Setores/Lojas")
        print("6. Produtos")
        print("7. Pedido de Compra")
        print("8. Entrada de estoque")
        print("9. Saída (entrega)")
        print("10. Relatórios")
        print("11. Configurações (usuários e permissões)")
        print("0. Sair")
        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            menu_entidade_simples("Categorias", criar_categoria, listar_categorias, atualizar_categoria, excluir_categoria)
        elif opcao == "2":
            menu_entidade_simples("Fornecedores", criar_fornecedor, listar_fornecedores, atualizar_fornecedor, excluir_fornecedor, tem_contato=True)
        elif opcao == "3":
            menu_entidade_simples("Tamanhos", criar_tamanho, listar_tamanhos, atualizar_tamanho, excluir_tamanho)
        elif opcao == "4":
            menu_entidade_simples("Funcionários", criar_funcionario, listar_funcionarios, atualizar_funcionario, excluir_funcionario)
        elif opcao == "5":
            menu_entidade_simples("Setores/Lojas", criar_setor_loja, listar_setores_loja, atualizar_setor_loja, excluir_setor_loja)
        elif opcao == "6":
            menu_produtos()
        elif opcao == "7":
            menu_pedido_compra()
        elif opcao == "8":
            menu_entrada()
        elif opcao == "9":
            menu_saida()
        elif opcao == "10":
            menu_relatorios()
        elif opcao == "11":
            menu_configuracoes()
        elif opcao == "0":
            print("Até logo!")
            break
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()
