import tkinter as tk
from tkinter import ttk, messagebox

from app.repositories.crud_produtos import criar_produto, listar_produtos, atualizar_produto, excluir_produto, categoria_e_epi
from app.repositories.crud_simple import listar_categorias, listar_setores_loja
from app.repositories.crud_usuario import listar_usuarios
from gui.utils import formatar_opcao, extrair_id, TreeviewBusca, adicionar_pesquisa
from app.auth import tem_permissao, obter_usuario_atual


class ProdutosFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.id_selecionado = None
        self.cache_produtos = {}
        self._montar_widgets()
        self.atualizar_combos()
        self.atualizar_lista()

    def _montar_widgets(self):
        form = ttk.LabelFrame(self, text="Cadastro de Produto", padding=10)
        form.pack(fill="x", pady=(0, 10))

        ttk.Label(form, text="Nome:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_nome = ttk.Entry(form, width=40)
        self.entry_nome.grid(row=0, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Categoria:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_categoria = ttk.Combobox(form, width=37, state="readonly")
        self.combo_categoria.grid(row=1, column=1, sticky="w", pady=4)
        self.combo_categoria.bind("<<ComboboxSelected>>", self._categoria_alterada)

        ttk.Label(form, text="CA (Certificado de Aprovação):").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_ca = ttk.Entry(form, width=20)
        self.entry_ca.grid(row=2, column=1, sticky="w", pady=4)
        self.label_ca = ttk.Label(form, text="Obrigatório para EPI", foreground="#a00")
        self.label_ca.grid(row=2, column=2, sticky="w", padx=(6, 0), pady=4)

        ttk.Label(form, text="Cadastrado por:").grid(row=3, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_usuario = ttk.Entry(form, width=39, state="readonly")
        self.entry_usuario.grid(row=3, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Setor padrão:").grid(row=4, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_setor = ttk.Combobox(form, width=37, state="readonly")
        self.combo_setor.grid(row=4, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Descrição:").grid(row=5, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_descricao = ttk.Entry(form, width=40)
        self.entry_descricao.grid(row=5, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Estoque mínimo:").grid(row=6, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_estoque_minimo = ttk.Entry(form, width=12)
        self.entry_estoque_minimo.grid(row=6, column=1, sticky="w", pady=4)
        ttk.Label(form, text="(quantidade total do produto)").grid(row=6, column=2, sticky="w", padx=(6, 0), pady=4)

        botoes = ttk.Frame(form)
        botoes.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.btn_novo = ttk.Button(botoes, text="Novo", command=self.limpar_formulario); self.btn_novo.pack(side="left", padx=(0, 6))
        self.btn_salvar = ttk.Button(botoes, text="Salvar", command=self.salvar); self.btn_salvar.pack(side="left", padx=(0, 6))
        self.btn_excluir = ttk.Button(botoes, text="Excluir selecionado", command=self.excluir); self.btn_excluir.pack(side="left", padx=(0, 6))
        if not tem_permissao("cadastrar_produtos"): self.btn_novo.state(["disabled"])
        if not tem_permissao("excluir_produtos"): self.btn_excluir.state(["disabled"])
        ttk.Button(botoes, text="🔄 Atualizar", command=self.atualizar_dados).pack(side="left")

        colunas = ("id", "nome", "categoria", "ca", "setor", "descricao", "estoque_minimo")
        self.tree = TreeviewBusca(self, columns=colunas, show="headings", height=12)
        self.tree.heading("id", text="Id")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("ca", text="CA")
        self.tree.heading("setor", text="Setor padrão")
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("estoque_minimo", text="Estoque mínimo")
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("nome", width=200)
        self.tree.column("categoria", width=110)
        self.tree.column("ca", width=100)
        self.tree.column("setor", width=110)
        self.tree.column("descricao", width=220)
        self.tree.column("estoque_minimo", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True)
        adicionar_pesquisa(self.tree)
        self.tree.bind("<<TreeviewSelect>>", self._ao_selecionar)

    def _categoria_alterada(self, _evento=None):
        self._atualizar_estado_ca()

    def _atualizar_estado_ca(self):
        id_categoria = extrair_id(self.combo_categoria.get())
        categoria = next((c for c in listar_categorias() if c.id_categoria == id_categoria), None) if id_categoria else None
        if categoria_e_epi(categoria):
            self.label_ca.configure(text="Obrigatório para EPI", foreground="#a00")
            self.entry_ca.configure(state="normal")
        else:
            self.label_ca.configure(text="Somente EPI", foreground="#666")
            self.entry_ca.configure(state="normal")

    def _mostrar_usuario_atual(self):
        usuario = obter_usuario_atual() or {}
        self.entry_usuario.configure(state="normal")
        self.entry_usuario.delete(0, tk.END)
        self.entry_usuario.insert(0, usuario.get("nome", ""))
        self.entry_usuario.configure(state="readonly")

    def atualizar_dados(self):
        """Recarrega campos e tabela diretamente do banco."""
        self.atualizar_combos()
        self.atualizar_lista()

    def atualizar_combos(self):
        categorias = listar_categorias()
        setores = listar_setores_loja()
        self.combo_categoria["values"] = [formatar_opcao(c.id_categoria, c.nome) for c in categorias]
        self._mostrar_usuario_atual()
        self.combo_setor["values"] = [formatar_opcao(s.id_setor_loja, s.nome) for s in setores]

    def atualizar_lista(self):
        for linha in self.tree.get_children():
            self.tree.delete(linha)
        self.cache_produtos = {}
        for p in listar_produtos():
            self.cache_produtos[p.id_produto] = p
            cat = p.categoria.nome if p.categoria else "-"
            setor = p.setor_padrao.nome if p.setor_padrao else "-"
            self.tree.insert("", "end", values=(p.id_produto, p.nome, cat, p.ca or "-", setor, p.descricao or "", p.estoque_minimo or 0))

    def _ao_selecionar(self, _evento):
        selecionado = self.tree.selection()
        if not selecionado:
            return
        id_produto = int(self.tree.item(selecionado[0], "values")[0])
        produto = self.cache_produtos.get(id_produto)
        if produto is None:
            return

        self.id_selecionado = id_produto
        self.entry_nome.delete(0, tk.END)
        self.entry_nome.insert(0, produto.nome)
        self.entry_ca.delete(0, tk.END)
        self.entry_ca.insert(0, produto.ca or "")
        if produto.categoria:
            self.combo_categoria.set(formatar_opcao(produto.id_categoria, produto.categoria.nome))
        self._mostrar_usuario_atual()
        if produto.setor_padrao:
            self.combo_setor.set(formatar_opcao(produto.id_setor_padrao, produto.setor_padrao.nome))
        else:
            self.combo_setor.set("")
        self.entry_descricao.delete(0, tk.END)
        self.entry_descricao.insert(0, produto.descricao or "")
        self.entry_estoque_minimo.delete(0, tk.END)
        self.entry_estoque_minimo.insert(0, str(produto.estoque_minimo or 0))

    def limpar_formulario(self):
        self.id_selecionado = None
        self.entry_nome.delete(0, tk.END)
        self.combo_categoria.set("")
        self.entry_ca.delete(0, tk.END)
        self._atualizar_estado_ca()
        self._mostrar_usuario_atual()
        self.combo_setor.set("")
        self.entry_descricao.delete(0, tk.END)
        self.entry_estoque_minimo.delete(0, tk.END)
        self.entry_estoque_minimo.insert(0, "0")
        self.tree.selection_remove(self.tree.selection())

    def salvar(self):
        if self.id_selecionado is None and not tem_permissao("cadastrar_produtos"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para cadastrar produtos."); return
        if self.id_selecionado is not None and not tem_permissao("editar_produtos"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para editar produtos."); return
        nome = self.entry_nome.get().strip()
        id_categoria = extrair_id(self.combo_categoria.get())
        usuario_atual = obter_usuario_atual() or {}
        id_usuario = usuario_atual.get("id_usuario")
        ca = self.entry_ca.get().strip() or None
        id_setor_padrao = extrair_id(self.combo_setor.get())
        descricao = self.entry_descricao.get().strip() or None
        estoque_minimo_texto = self.entry_estoque_minimo.get().strip()
        if estoque_minimo_texto == "":
            estoque_minimo = 0
        elif estoque_minimo_texto.isdigit():
            estoque_minimo = int(estoque_minimo_texto)
        else:
            messagebox.showwarning("Campo inválido", "Informe o estoque mínimo como um número inteiro maior ou igual a zero.")
            return

        if not nome:
            messagebox.showwarning("Campo obrigatório", "Digite o nome do produto.")
            return
        if id_categoria is None:
            messagebox.showwarning("Campo obrigatório", "Escolha uma categoria.")
            return
        categoria = next((c for c in listar_categorias() if c.id_categoria == id_categoria), None)
        if categoria_e_epi(categoria) and not ca:
            messagebox.showwarning("CA obrigatório", "Este produto é um EPI. Informe o CA (Certificado de Aprovação).")
            self.entry_ca.focus_set()
            return
        if id_usuario is None:
            messagebox.showwarning("Sessão inválida", "Não foi possível identificar o usuário conectado. Faça login novamente.")
            return

        try:
            if self.id_selecionado is None:
                criar_produto(nome, id_categoria, id_usuario, descricao, id_setor_padrao=id_setor_padrao, estoque_minimo=estoque_minimo, ca=ca)
                messagebox.showinfo("Sucesso", "Produto cadastrado!")
            else:
                atualizar_produto(self.id_selecionado, nome=nome, id_categoria=id_categoria,
                                   descricao=descricao, id_setor_padrao=id_setor_padrao, estoque_minimo=estoque_minimo, ca=ca)
                messagebox.showinfo("Sucesso", "Produto atualizado!")
        except ValueError as e:
            messagebox.showerror("Erro", str(e))
            return

        self.limpar_formulario()
        self.atualizar_lista()

    def excluir(self):
        if not tem_permissao("excluir_produtos"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para excluir produtos."); return
        if self.id_selecionado is None:
            messagebox.showwarning("Nada selecionado", "Selecione um produto na lista antes de excluir.")
            return
        if not messagebox.askyesno("Confirmar exclusão", "Tem certeza que deseja excluir este produto?"):
            return
        sucesso = excluir_produto(self.id_selecionado)
        if not sucesso:
            messagebox.showerror("Erro", "Produto não encontrado.")
        self.limpar_formulario()
        self.atualizar_lista()
