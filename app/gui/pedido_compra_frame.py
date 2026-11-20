import tkinter as tk
from datetime import date, datetime
from tkinter import ttk, messagebox

from app.repositories.crud_pedido_compra import (
    criar_pedido_compra, listar_pedidos_compra, atualizar_pedido_compra, excluir_pedido_compra,
)
from app.repositories.crud_produtos import listar_produtos
from app.repositories.crud_simple import listar_fornecedores
from gui.utils import formatar_opcao, extrair_id, ler_data_campo, ComboBusca, TreeviewBusca, adicionar_pesquisa
from app.auth import tem_permissao


class PedidoCompraFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.id_selecionado = None
        self.cache_pedidos = {}
        self._montar_widgets()
        self.atualizar_combos()
        self.atualizar_lista()

    def _montar_widgets(self):
        form = ttk.LabelFrame(self, text="Cadastro de Pedido de Compra", padding=10)
        form.pack(fill="x", pady=(0, 10))

        ttk.Label(form, text="Produto:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_produto = ComboBusca(form, width=37)
        self.combo_produto.grid(row=0, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Fornecedor:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_fornecedor = ComboBusca(form, width=37)
        self.combo_fornecedor.grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Quantidade:").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_quantidade = ttk.Entry(form, width=15)
        self.entry_quantidade.grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Valor unitário (R$):").grid(row=3, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_preco = ttk.Entry(form, width=15)
        self.entry_preco.grid(row=3, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Data da compra (dd/mm/aaaa):").grid(row=4, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_data = ttk.Entry(form, width=15)
        self.entry_data.grid(row=4, column=1, sticky="w", pady=4)
        self.entry_data.insert(0, date.today().strftime("%d/%m/%Y"))

        ttk.Label(form, text="Observação:").grid(row=5, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_observacao = ttk.Entry(form, width=40)
        self.entry_observacao.grid(row=5, column=1, sticky="w", pady=4)

        botoes = ttk.Frame(form)
        botoes.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.btn_novo = ttk.Button(botoes, text="Novo", command=self.limpar_formulario)
        self.btn_novo.pack(side="left", padx=(0, 6))
        self.btn_salvar = ttk.Button(botoes, text="Salvar", command=self.salvar)
        self.btn_salvar.pack(side="left", padx=(0, 6))
        self.btn_excluir = ttk.Button(botoes, text="Excluir selecionado", command=self.excluir)
        self.btn_excluir.pack(side="left", padx=(0, 6))
        ttk.Button(botoes, text="🔄 Atualizar", command=self.atualizar_dados).pack(side="left")
        if not tem_permissao("criar_pedido_compra"):
            self.btn_novo.state(["disabled"])
            self.btn_salvar.state(["disabled"])
        if not tem_permissao("excluir_pedido_compra"):
            self.btn_excluir.state(["disabled"])

        colunas = ("id", "produto", "fornecedor", "quantidade", "preco", "total", "data")
        self.tree = TreeviewBusca(self, columns=colunas, show="headings", height=10)
        for col, texto, largura in [
            ("id", "Pedido #", 70), ("produto", "Produto", 170), ("fornecedor", "Fornecedor", 140),
            ("quantidade", "Qtd.", 60), ("preco", "Vl. Unit.", 80), ("total", "Vl. Total", 90), ("data", "Data", 90),
        ]:
            self.tree.heading(col, text=texto)
            self.tree.column(col, width=largura, anchor="center" if col in ("id", "quantidade", "preco", "total", "data") else "w")
        self.tree.pack(fill="both", expand=True)
        adicionar_pesquisa(self.tree)
        self.tree.bind("<<TreeviewSelect>>", self._ao_selecionar)

    def atualizar_dados(self):
        """Recarrega listas e tabela diretamente do banco."""
        self.atualizar_combos()
        self.atualizar_lista()

    def atualizar_combos(self):
        self.combo_produto["values"] = [formatar_opcao(p.id_produto, p.nome) for p in listar_produtos()]
        self.combo_fornecedor["values"] = [formatar_opcao(f.id_fornecedor, f.nome) for f in listar_fornecedores()]

    def atualizar_lista(self):
        for linha in self.tree.get_children():
            self.tree.delete(linha)
        self.cache_pedidos = {}
        for p in listar_pedidos_compra():
            self.cache_pedidos[p.id_pedido_compra] = p
            preco = float(p.preco) if p.preco is not None else 0
            total = preco * p.quantidade
            self.tree.insert("", "end", values=(
                p.id_pedido_compra, p.produto.nome, p.fornecedor.nome,
                p.quantidade, f"{preco:.2f}", f"{total:.2f}", p.data_compra,
            ))

    def _ao_selecionar(self, _evento):
        selecionado = self.tree.selection()
        if not selecionado:
            return
        id_pedido = int(self.tree.item(selecionado[0], "values")[0])
        pedido = self.cache_pedidos.get(id_pedido)
        if pedido is None:
            return

        self.id_selecionado = id_pedido
        self.combo_produto.set(formatar_opcao(pedido.id_produto, pedido.produto.nome))
        self.combo_produto.configure(state="disabled")  # não editável num pedido já existente
        self.combo_fornecedor.set(formatar_opcao(pedido.id_fornecedor, pedido.fornecedor.nome))
        self.combo_fornecedor.configure(state="disabled")
        self.entry_quantidade.delete(0, tk.END)
        self.entry_quantidade.insert(0, str(pedido.quantidade))
        self.entry_preco.delete(0, tk.END)
        self.entry_preco.insert(0, str(pedido.preco) if pedido.preco is not None else "")
        self.entry_data.delete(0, tk.END)
        self.entry_data.insert(0, pedido.data_compra.strftime("%d/%m/%Y") if pedido.data_compra else "")
        self.entry_observacao.delete(0, tk.END)
        self.entry_observacao.insert(0, pedido.observacao or "")

    def limpar_formulario(self):
        self.id_selecionado = None
        self.combo_produto.configure(state="readonly")
        self.combo_produto.set("")
        self.combo_fornecedor.configure(state="readonly")
        self.combo_fornecedor.set("")
        self.entry_quantidade.delete(0, tk.END)
        self.entry_preco.delete(0, tk.END)
        self.entry_data.delete(0, tk.END)
        self.entry_data.insert(0, date.today().strftime("%d/%m/%Y"))
        self.entry_observacao.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _ler_data(self):
        """Data do campo; None (com aviso) se estiver inválida - nesse caso não salvar."""
        return ler_data_campo(self.entry_data)

    def salvar(self):
        if self.id_selecionado is None and not tem_permissao("criar_pedido_compra"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para criar pedidos de compra.")
            return
        if self.id_selecionado is not None and not tem_permissao("editar_pedido_compra"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para editar pedidos de compra.")
            return
        quantidade_texto = self.entry_quantidade.get().strip()
        preco_texto = self.entry_preco.get().strip().replace(",", ".")
        observacao = self.entry_observacao.get().strip() or None
        data_compra = self._ler_data()
        if data_compra is None:
            return

        if not quantidade_texto.isdigit():
            messagebox.showwarning("Quantidade inválida", "Digite um número inteiro para a quantidade.")
            return
        quantidade = int(quantidade_texto)

        try:
            preco = float(preco_texto) if preco_texto else 0.0
        except ValueError:
            messagebox.showwarning("Valor inválido", "Digite o valor unitário como número (ex: 49.90).")
            return

        try:
            if self.id_selecionado is None:
                id_produto = extrair_id(self.combo_produto.get())
                id_fornecedor = extrair_id(self.combo_fornecedor.get())
                if id_produto is None or id_fornecedor is None:
                    messagebox.showwarning("Campos obrigatórios", "Escolha o produto e o fornecedor.")
                    return
                criar_pedido_compra(id_produto, quantidade, preco, id_fornecedor,
                                     data_compra=data_compra, observacao=observacao)
                messagebox.showinfo("Sucesso", "Pedido de compra cadastrado!")
            else:
                atualizar_pedido_compra(self.id_selecionado, quantidade=quantidade, preco=preco,
                                         data_compra=data_compra, observacao=observacao)
                messagebox.showinfo("Sucesso", "Pedido de compra atualizado!")
        except ValueError as e:
            messagebox.showerror("Erro", str(e))
            return

        self.limpar_formulario()
        self.atualizar_lista()

    def excluir(self):
        if not tem_permissao("excluir_pedido_compra"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para excluir pedidos de compra.")
            return
        if self.id_selecionado is None:
            messagebox.showwarning("Nada selecionado", "Selecione um pedido na lista antes de excluir.")
            return
        if not messagebox.askyesno("Confirmar exclusão", "Tem certeza que deseja excluir este pedido de compra?\n(Só é possível se nenhuma entrada estiver ligada a ele.)"):
            return
        try:
            sucesso = excluir_pedido_compra(self.id_selecionado)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível excluir: {e}")
            return
        if not sucesso:
            messagebox.showerror("Erro", "Pedido não encontrado.")
        self.limpar_formulario()
        self.atualizar_lista()
