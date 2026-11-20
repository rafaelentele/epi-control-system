import tkinter as tk
from datetime import date, datetime
from tkinter import ttk, messagebox

from app.repositories.crud_entrada import criar_entrada, listar_entradas, atualizar_entrada, excluir_entrada
from app.repositories.crud_pedido_compra import listar_pedidos_compra
from app.repositories.crud_simple import listar_tamanhos
from app.repositories.crud_usuario import listar_usuarios
from gui.utils import formatar_opcao, extrair_id, ler_data_campo, TreeviewBusca, adicionar_pesquisa
from app.auth import tem_permissao, obter_usuario_atual


def _formatar_pedido(p):
    return f"{p.id_pedido_compra} - {p.produto.nome} ({p.quantidade} un) - {p.fornecedor.nome}"


class EntradaFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.id_selecionado = None
        self.cache_entradas = {}
        self.cache_pedidos = {}
        self.id_pedido_selecionado = None
        self._montar_widgets()
        self.atualizar_combos()
        self.atualizar_lista()

    def _montar_widgets(self):
        form = ttk.LabelFrame(self, text="Registrar Entrada de Estoque", padding=10)
        form.pack(fill="x", pady=(0, 10))

        ttk.Label(form, text="Código do Pedido de Compra:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        pedido_busca = ttk.Frame(form)
        pedido_busca.grid(row=0, column=1, sticky="w", pady=4)
        self.entry_pedido = ttk.Entry(pedido_busca, width=15)
        self.entry_pedido.pack(side="left")
        self.entry_pedido.bind("<Return>", self._buscar_pedido_por_codigo)
        ttk.Button(pedido_busca, text="🔎 Buscar", command=self._buscar_pedido_por_codigo).pack(side="left", padx=(6, 0))
        self.label_pedido_info = ttk.Label(form, text="Digite o código e pressione Enter ou Buscar.", foreground="#555")
        self.label_pedido_info.grid(row=0, column=2, sticky="w", padx=(10, 0), pady=4)

        ttk.Label(form, text="Produto (do pedido):").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        self.label_produto = ttk.Label(form, text="-", foreground="#555")
        self.label_produto.grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Fornecedor (do pedido):").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=4)
        self.label_fornecedor = ttk.Label(form, text="-", foreground="#555")
        self.label_fornecedor.grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Tamanho:").grid(row=3, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_tamanho = ttk.Combobox(form, width=37, state="readonly")
        self.combo_tamanho.grid(row=3, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Quantidade recebida:").grid(row=4, column=0, sticky="w", padx=(0, 6), pady=4)
        quantidade_frame = ttk.Frame(form)
        quantidade_frame.grid(row=4, column=1, sticky="w", pady=4)
        self.entry_quantidade = ttk.Entry(quantidade_frame, width=15)
        self.entry_quantidade.pack(side="left")
        self.label_restante = ttk.Label(quantidade_frame, text="", foreground="#555")
        self.label_restante.pack(side="left", padx=(8, 0))

        ttk.Label(form, text="Usuário:").grid(row=5, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_usuario = ttk.Entry(form, width=37, state="readonly")
        self.entry_usuario.grid(row=5, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Data (dd/mm/aaaa):").grid(row=6, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_data = ttk.Entry(form, width=15)
        self.entry_data.grid(row=6, column=1, sticky="w", pady=4)
        self.entry_data.insert(0, date.today().strftime("%d/%m/%Y"))

        ttk.Label(form, text="Observação:").grid(row=7, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_observacao = ttk.Entry(form, width=40)
        self.entry_observacao.grid(row=7, column=1, sticky="w", pady=4)

        botoes = ttk.Frame(form)
        botoes.grid(row=8, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(botoes, text="Novo", command=self.limpar_formulario).pack(side="left", padx=(0, 6))
        ttk.Button(botoes, text="Salvar", command=self.salvar).pack(side="left", padx=(0, 6))
        ttk.Button(botoes, text="Excluir selecionado", command=self.excluir).pack(side="left", padx=(0, 6))
        ttk.Button(botoes, text="🔄 Atualizar", command=self.atualizar_dados).pack(side="left")

        colunas = ("id", "pedido", "produto", "tamanho", "quantidade", "fornecedor", "data")
        self.tree = TreeviewBusca(self, columns=colunas, show="headings", height=10)
        for col, texto, largura in [
            ("id", "Id", 40), ("pedido", "Pedido #", 70), ("produto", "Produto", 160), ("tamanho", "Tam.", 60),
            ("quantidade", "Qtd.", 60), ("fornecedor", "Fornecedor", 130), ("data", "Data", 90),
        ]:
            self.tree.heading(col, text=texto)
            self.tree.column(col, width=largura, anchor="center" if col in ("id", "pedido", "tamanho", "quantidade", "data") else "w")
        self.tree.pack(fill="both", expand=True)
        adicionar_pesquisa(self.tree)
        self.tree.bind("<<TreeviewSelect>>", self._ao_selecionar)

    def atualizar_dados(self):
        """Recarrega listas e tabela diretamente do banco."""
        self.atualizar_combos()
        self.atualizar_lista()

    def atualizar_combos(self):
        self.cache_pedidos = {p.id_pedido_compra: p for p in listar_pedidos_compra()}
        self.combo_tamanho["values"] = [formatar_opcao(t.id_tamanho, t.nome) for t in listar_tamanhos()]
        usuario_atual = obter_usuario_atual()
        self.entry_usuario.configure(state="normal")
        self.entry_usuario.delete(0, tk.END)
        if usuario_atual:
            self.entry_usuario.insert(0, usuario_atual.get("nome", ""))
        self.entry_usuario.configure(state="readonly")

    def _buscar_pedido_por_codigo(self, _evento=None):
        texto = self.entry_pedido.get().strip().replace("#", "")
        if not texto.isdigit():
            self.id_pedido_selecionado = None
            messagebox.showwarning("Pedido inválido", "Digite somente o código numérico do pedido de compra.")
            return "break"
        id_pedido = int(texto)
        self.cache_pedidos = {p.id_pedido_compra: p for p in listar_pedidos_compra()}
        pedido = self.cache_pedidos.get(id_pedido)
        if pedido is None:
            self.id_pedido_selecionado = None
            self.label_produto.configure(text="-")
            self.label_fornecedor.configure(text="-")
            self.label_pedido_info.configure(text="Pedido não encontrado.", foreground="#a00")
            messagebox.showwarning("Pedido não encontrado", f"Não existe pedido de compra com o código #{id_pedido}.")
            return "break"
        self.id_pedido_selecionado = id_pedido
        self.label_pedido_info.configure(text=f"#{pedido.id_pedido_compra} | {pedido.produto.nome} | {pedido.fornecedor.nome}", foreground="#075")
        self.label_produto.configure(text=pedido.produto.nome)
        self.label_fornecedor.configure(text=pedido.fornecedor.nome)
        self._atualizar_limite_pedido(id_pedido_compra=id_pedido, id_entrada=None)
        return "break"

    def _atualizar_limite_pedido(self, id_pedido_compra, id_entrada=None):
        """Mostra quanto ainda pode ser recebido do pedido selecionado."""
        if id_pedido_compra is None:
            self.label_restante.configure(text="")
            return
        try:
            pedidos = listar_pedidos_compra()
            pedido = next((p for p in pedidos if p.id_pedido_compra == id_pedido_compra), None)
            if pedido is None:
                self.label_restante.configure(text="")
                return
            recebido = sum(
                int(e.quantidade) for e in listar_entradas()
                if e.id_pedido_compra == id_pedido_compra and e.id_entrada != id_entrada
            )
            restante = max(int(pedido.quantidade) - recebido, 0)
            self.label_restante.configure(text=f"Máximo permitido nesta entrada: {restante}")
        except Exception:
            self.label_restante.configure(text="")

    def atualizar_lista(self):
        for linha in self.tree.get_children():
            self.tree.delete(linha)
        self.cache_entradas = {}
        for e in listar_entradas():
            self.cache_entradas[e.id_entrada] = e
            self.tree.insert("", "end", values=(
                e.id_entrada, e.id_pedido_compra or "-", e.produto.nome,
                e.tamanho.nome if e.tamanho else "-", e.quantidade, e.fornecedor.nome, e.data_entrada,
            ))

    def _ao_selecionar(self, _evento):
        selecionado = self.tree.selection()
        if not selecionado:
            return
        id_entrada = int(self.tree.item(selecionado[0], "values")[0])
        entrada = self.cache_entradas.get(id_entrada)
        if entrada is None:
            return

        self.id_selecionado = id_entrada
        self.id_pedido_selecionado = entrada.id_pedido_compra
        self.entry_pedido.delete(0, tk.END)
        self.entry_pedido.insert(0, str(entrada.id_pedido_compra or ""))
        self.entry_pedido.configure(state="disabled")  # pedido de compra não é editável numa entrada já existente
        self.label_produto.configure(text=entrada.produto.nome)
        self.label_fornecedor.configure(text=entrada.fornecedor.nome)
        self.combo_tamanho.set(formatar_opcao(entrada.id_tamanho, entrada.tamanho.nome) if entrada.tamanho else "")
        self.entry_quantidade.delete(0, tk.END)
        self.entry_quantidade.insert(0, str(entrada.quantidade))
        self._atualizar_limite_pedido(id_pedido_compra=entrada.id_pedido_compra, id_entrada=entrada.id_entrada)
        self.entry_usuario.configure(state="normal")
        self.entry_usuario.delete(0, tk.END)
        self.entry_usuario.insert(0, entrada.usuario.nome if entrada.usuario else "")
        self.entry_usuario.configure(state="readonly")
        self.entry_data.delete(0, tk.END)
        self.entry_data.insert(0, entrada.data_entrada.strftime("%d/%m/%Y") if entrada.data_entrada else "")
        self.entry_observacao.delete(0, tk.END)
        self.entry_observacao.insert(0, entrada.observacao or "")

    def limpar_formulario(self):
        self.id_selecionado = None
        self.id_pedido_selecionado = None
        self.entry_pedido.configure(state="normal")
        self.entry_pedido.delete(0, tk.END)
        self.label_pedido_info.configure(text="Digite o código e pressione Enter ou Buscar.", foreground="#555")
        self.label_produto.configure(text="-")
        self.label_fornecedor.configure(text="-")
        self.combo_tamanho.set("")
        self.entry_quantidade.delete(0, tk.END)
        self.label_restante.configure(text="")
        usuario_atual = obter_usuario_atual()
        self.entry_usuario.configure(state="normal")
        self.entry_usuario.delete(0, tk.END)
        if usuario_atual:
            self.entry_usuario.insert(0, usuario_atual.get("nome", ""))
        self.entry_usuario.configure(state="readonly")
        self.entry_data.delete(0, tk.END)
        self.entry_data.insert(0, date.today().strftime("%d/%m/%Y"))
        self.entry_observacao.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _ler_data(self):
        """Data do campo; None (com aviso) se estiver inválida - nesse caso não salvar."""
        return ler_data_campo(self.entry_data)

    def salvar(self):
        if not tem_permissao("dar_entrada"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para realizar esta operação."); return
        id_tamanho = extrair_id(self.combo_tamanho.get())
        quantidade_texto = self.entry_quantidade.get().strip()
        observacao = self.entry_observacao.get().strip() or None
        data_entrada = self._ler_data()
        if data_entrada is None:
            return

        if not quantidade_texto.isdigit():
            messagebox.showwarning("Quantidade inválida", "Digite um número inteiro para a quantidade.")
            return
        quantidade = int(quantidade_texto)
        if quantidade <= 0:
            messagebox.showwarning("Quantidade inválida", "A quantidade deve ser maior que zero.")
            return

        id_pedido_selecionado = self.id_pedido_selecionado
        if id_pedido_selecionado is not None:
            try:
                pedido = self.cache_pedidos.get(id_pedido_selecionado)
                if pedido is None:
                    self.atualizar_combos()
                    pedido = self.cache_pedidos.get(id_pedido_selecionado)
                if pedido is not None:
                    recebido = sum(
                        int(e.quantidade) for e in listar_entradas()
                        if e.id_pedido_compra == id_pedido_selecionado and e.id_entrada != self.id_selecionado
                    )
                    restante = int(pedido.quantidade) - recebido
                    if quantidade > restante:
                        messagebox.showerror(
                            "Quantidade acima do pedido",
                            f"O pedido #{pedido.id_pedido_compra} foi feito para {pedido.quantidade} unidade(s).\n\n"
                            f"Já recebido: {recebido}\n"
                            f"Restante permitido: {max(restante, 0)}\n"
                            f"Você informou: {quantidade}",
                        )
                        return
            except Exception as exc:
                messagebox.showerror("Erro ao conferir pedido", str(exc))
                return

        try:
            if self.id_selecionado is None:
                id_pedido = self.id_pedido_selecionado
                usuario_atual = obter_usuario_atual()
                id_usuario = usuario_atual.get("id_usuario") if usuario_atual else None
                if id_pedido is None:
                    messagebox.showwarning("Campo obrigatório", "Escolha o pedido de compra dessa entrada.")
                    return
                if id_usuario is None or id_tamanho is None:
                    messagebox.showwarning("Campos obrigatórios", "Preencha o tamanho. O usuário é definido automaticamente pelo login.")
                    return
                criar_entrada(id_pedido, id_tamanho, quantidade, id_usuario,
                               data_entrada=data_entrada, observacao=observacao)
                messagebox.showinfo("Sucesso", "Entrada registrada!")
            else:
                atualizar_entrada(self.id_selecionado, quantidade=quantidade, id_tamanho=id_tamanho,
                                   data_entrada=data_entrada, observacao=observacao)
                messagebox.showinfo("Sucesso", "Entrada atualizada!")
        except ValueError as e:
            messagebox.showerror("Erro", str(e))
            return

        self.limpar_formulario()
        self.atualizar_lista()

    def excluir(self):
        if not tem_permissao("excluir_produtos"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para realizar esta operação."); return
        if self.id_selecionado is None:
            messagebox.showwarning("Nada selecionado", "Selecione uma entrada na lista antes de excluir.")
            return
        if not messagebox.askyesno("Confirmar exclusão", "Tem certeza que deseja excluir esta entrada?"):
            return
        sucesso = excluir_entrada(self.id_selecionado)
        if not sucesso:
            messagebox.showerror("Erro", "Entrada não encontrada.")
        self.limpar_formulario()
        self.atualizar_lista()
