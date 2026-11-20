import tkinter as tk
import tkinter.font as tkfont
from datetime import date, datetime
from tkinter import ttk, messagebox

from app.repositories.crud_saida import (
    criar_pedido_saida, listar_pedidos_saida, buscar_pedido_saida,
    excluir_pedido_saida, consultar_saldo,
)
from app.repositories.crud_produtos import listar_produtos
from app.repositories.crud_simple import listar_tamanhos, listar_funcionarios, listar_setores_loja
from gui.utils import formatar_opcao, extrair_id, ler_data_campo, ComboBusca, TreeviewBusca, adicionar_pesquisa
from app.auth import tem_permissao, obter_usuario_atual


class PedidoSaidaDialog(tk.Toplevel):
    """Popup com os dados de um pedido de saída já registrado (somente leitura)."""

    def __init__(self, parent, pedido, abrir_termo=None):
        super().__init__(parent)
        numero = pedido.id_pedido_saida
        self.title(f"Pedido de Saída #{numero}")
        self.transient(parent.winfo_toplevel())
        self.minsize(520, 320)

        negrito = tkfont.nametofont("TkDefaultFont").copy()
        negrito.configure(weight="bold")
        self._fonte = negrito  # mantém a referência

        corpo = ttk.Frame(self, padding=14)
        corpo.pack(fill="both", expand=True)
        corpo.columnconfigure(1, weight=1)
        ttk.Label(corpo, text=f"Pedido de Saída #{numero}", font=negrito).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        data = pedido.data_saida.strftime("%d/%m/%Y") if pedido.data_saida else "-"
        campos = [
            ("Data:", data),
            ("Funcionário:", pedido.funcionario.nome if pedido.funcionario else "-"),
            ("Setor/Loja:", pedido.setor_loja.nome if pedido.setor_loja else "-"),
            ("Baixa por:", pedido.usuario.nome if pedido.usuario else "-"),
            ("Observação:", (getattr(pedido, "observacao", None) or "-")),
        ]
        for i, (rotulo, valor) in enumerate(campos, start=1):
            ttk.Label(corpo, text=rotulo, font=negrito).grid(row=i, column=0, sticky="nw", padx=(0, 10), pady=2)
            ttk.Label(corpo, text=valor, wraplength=420, justify="left").grid(row=i, column=1, sticky="w", pady=2)

        ttk.Label(corpo, text="Itens do pedido", font=negrito).grid(row=len(campos) + 1, column=0, columnspan=2, sticky="w", pady=(12, 4))
        itens = list(pedido.itens or [])
        tabela = ttk.Treeview(corpo, columns=("produto", "categoria", "tamanho", "quantidade"), show="headings", height=min(max(len(itens), 3), 10))
        for col, texto, largura, ancora in [
            ("produto", "Produto", 220, "w"), ("categoria", "Categoria", 110, "w"),
            ("tamanho", "Tamanho", 70, "center"), ("quantidade", "Qtd.", 60, "center"),
        ]:
            tabela.heading(col, text=texto)
            tabela.column(col, width=largura, anchor=ancora)
        for item in itens:
            produto = item.produto
            tabela.insert("", "end", values=(
                produto.nome if produto else "-",
                produto.categoria.nome if produto and produto.categoria else "-",
                item.tamanho.nome if item.tamanho else "-",
                item.quantidade,
            ))
        tabela.grid(row=len(campos) + 2, column=0, columnspan=2, sticky="nsew")
        corpo.rowconfigure(len(campos) + 2, weight=1)

        total = sum(int(i.quantidade or 0) for i in itens)
        ttk.Label(corpo, text=f"{len(itens)} item(ns)  |  {total} peça(s) no total", foreground="#666").grid(
            row=len(campos) + 3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        botoes = ttk.Frame(corpo)
        botoes.grid(row=len(campos) + 4, column=0, columnspan=2, sticky="e", pady=(12, 0))
        if abrir_termo is not None:
            ttk.Button(botoes, text="Gerar Termo", command=lambda: (self.destroy(), abrir_termo(numero))).pack(side="left", padx=(0, 8))
        botao_fechar = ttk.Button(botoes, text="Fechar", command=self.destroy)
        botao_fechar.pack(side="left")
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        try:  # centraliza sobre a janela principal
            principal = parent.winfo_toplevel()
            x = principal.winfo_rootx() + (principal.winfo_width() - self.winfo_reqwidth()) // 2
            y = principal.winfo_rooty() + (principal.winfo_height() - self.winfo_reqheight()) // 3
            self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except tk.TclError:
            pass
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        botao_fechar.focus_set()


class SaidaFrame(ttk.Frame):
    TEXTO_SALDO_VAZIO = "Escolha o produto e o tamanho para ver o saldo em estoque."

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.itens_pendentes = []  # itens do pedido novo, ainda não salvos
        self.cache_pedidos = {}
        self.pedido_selecionado_id = None
        self.id_funcionario_selecionado = None
        self._montar_widgets()
        self.atualizar_combos()
        self.atualizar_lista_pedidos()

    # ------------------------------------------------------------
    def _montar_widgets(self):
        # ===== Bloco: Novo pedido =====
        frame_novo = ttk.LabelFrame(self, text="Novo Pedido de Saída", padding=10)
        frame_novo.pack(fill="x", pady=(0, 8))

        ttk.Label(frame_novo, text="Funcionário (nome ou código):").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        funcionario_busca = ttk.Frame(frame_novo)
        funcionario_busca.grid(row=0, column=1, sticky="w", pady=3)
        self.entry_funcionario = ttk.Entry(funcionario_busca, width=30)
        self.entry_funcionario.pack(side="left")
        self.entry_funcionario.bind("<Return>", self._buscar_funcionario)
        ttk.Button(funcionario_busca, text="🔎 Buscar", command=self._buscar_funcionario).pack(side="left", padx=(6, 0))

        ttk.Label(frame_novo, text="Setor/Loja:").grid(row=0, column=2, sticky="w", padx=(12, 6), pady=3)
        self.combo_setor = ttk.Combobox(frame_novo, width=25, state="readonly")
        self.combo_setor.grid(row=0, column=3, sticky="w", pady=3)

        ttk.Label(frame_novo, text="Usuário (baixa):").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=3)
        self.entry_usuario = ttk.Entry(frame_novo, width=30, state="readonly")
        self.entry_usuario.grid(row=1, column=1, sticky="w", pady=3)

        ttk.Label(frame_novo, text="Data (dd/mm/aaaa):").grid(row=1, column=2, sticky="w", padx=(12, 6), pady=3)
        self.entry_data = ttk.Entry(frame_novo, width=15)
        self.entry_data.grid(row=1, column=3, sticky="w", pady=3)
        self.entry_data.insert(0, date.today().strftime("%d/%m/%Y"))

        ttk.Label(frame_novo, text="Observação:").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=3)
        self.entry_observacao = ttk.Entry(frame_novo, width=60)
        self.entry_observacao.grid(row=2, column=1, columnspan=3, sticky="w", pady=3)

        # -- itens do pedido novo --
        frame_itens = ttk.LabelFrame(frame_novo, text="Itens deste pedido", padding=8)
        frame_itens.grid(row=3, column=0, columnspan=4, sticky="we", pady=(8, 0))

        ttk.Label(frame_itens, text="Produto:").grid(row=0, column=0, sticky="w")
        self.combo_produto_item = ComboBusca(frame_itens, width=34)
        self.combo_produto_item.grid(row=0, column=1, padx=(4, 12))

        ttk.Label(frame_itens, text="Tamanho:").grid(row=0, column=2, sticky="w")
        self.combo_tamanho_item = ttk.Combobox(frame_itens, width=10, state="readonly")
        self.combo_tamanho_item.grid(row=0, column=3, padx=(4, 12))

        ttk.Label(frame_itens, text="Qtd:").grid(row=0, column=4, sticky="w")
        self.entry_quantidade_item = ttk.Entry(frame_itens, width=6)
        self.entry_quantidade_item.grid(row=0, column=5, padx=(4, 12))

        ttk.Button(frame_itens, text="+ Adicionar item", command=self.adicionar_item_pendente).grid(row=0, column=6)

        # Saldo do item escolhido (evita descobrir só ao salvar que não há estoque)
        self.lbl_saldo = ttk.Label(frame_itens, text=self.TEXTO_SALDO_VAZIO, foreground="#666")
        self.lbl_saldo.grid(row=1, column=0, columnspan=7, sticky="w", pady=(6, 0))
        self.combo_produto_item.bind("<<ComboboxSelected>>", self._atualizar_saldo, add="+")
        self.combo_tamanho_item.bind("<<ComboboxSelected>>", self._atualizar_saldo, add="+")
        self.entry_quantidade_item.bind("<KeyRelease>", self._atualizar_saldo, add="+")

        self.tree_itens_pendentes = ttk.Treeview(frame_itens, columns=("produto", "tamanho", "quantidade"), show="headings", height=4)
        self.tree_itens_pendentes.heading("produto", text="Produto")
        self.tree_itens_pendentes.heading("tamanho", text="Tamanho")
        self.tree_itens_pendentes.heading("quantidade", text="Quantidade")
        self.tree_itens_pendentes.grid(row=2, column=0, columnspan=7, sticky="we", pady=(6, 0))

        ttk.Button(frame_itens, text="Remover item da lista", command=self.remover_item_pendente).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        botoes_novo = ttk.Frame(frame_novo)
        botoes_novo.grid(row=4, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Button(botoes_novo, text="Salvar Pedido", command=self.salvar_pedido).pack(side="left", padx=(0, 6))
        ttk.Button(botoes_novo, text="Limpar tudo", command=self.limpar_formulario_novo).pack(side="left", padx=(0, 6))
        ttk.Button(botoes_novo, text="🔄 Atualizar", command=self.atualizar_dados).pack(side="left")

        # ===== Bloco: Pedidos existentes =====
        frame_lista = ttk.LabelFrame(self, text="Pedidos de Saída Registrados", padding=8)
        frame_lista.pack(fill="both", expand=True)

        botoes_lista = ttk.Frame(frame_lista)
        botoes_lista.pack(side="bottom", fill="x", pady=(6, 0))
        ttk.Button(botoes_lista, text="Excluir pedido selecionado", command=self.excluir_pedido).pack(side="left")
        ttk.Label(botoes_lista, text="Dê duplo clique em um pedido para ver os detalhes.", foreground="#666").pack(side="left", padx=14)

        colunas = ("id", "funcionario", "setor", "data", "usuario", "itens")
        self.tree_pedidos = TreeviewBusca(frame_lista, columns=colunas, show="headings", height=10)
        for col, texto, largura in [
            ("id", "Pedido #", 70), ("funcionario", "Funcionário", 160), ("setor", "Setor", 120),
            ("data", "Data", 90), ("usuario", "Baixa por", 140), ("itens", "Qtd. Itens", 70),
        ]:
            self.tree_pedidos.heading(col, text=texto)
            self.tree_pedidos.column(col, width=largura, anchor="center" if col in ("id", "data", "itens") else "w")
        self.tree_pedidos.pack(side="top", fill="both", expand=True)
        adicionar_pesquisa(self.tree_pedidos)
        self.tree_pedidos.bind("<<TreeviewSelect>>", self._ao_selecionar_pedido)
        self.tree_pedidos.bind("<Double-1>", self._ao_clicar_pedido)
        self.tree_pedidos.bind("<Return>", self._ao_enter_pedido)

    # ------------------------------------------------------------
    def atualizar_dados(self):
        """Recarrega campos e pedidos diretamente do banco."""
        self.atualizar_combos()
        self.atualizar_lista_pedidos()
        self._atualizar_saldo()

    def atualizar_combos(self):
        setores = [formatar_opcao(s.id_setor_loja, s.nome) for s in listar_setores_loja()]
        usuario_atual = obter_usuario_atual()
        produtos = [formatar_opcao(p.id_produto, p.nome) for p in listar_produtos()]
        tamanhos = [formatar_opcao(t.id_tamanho, t.nome) for t in listar_tamanhos()]

        self.combo_setor["values"] = setores
        self.combo_produto_item["values"] = produtos
        self.combo_tamanho_item["values"] = tamanhos
        self.entry_usuario.configure(state="normal")
        self.entry_usuario.delete(0, tk.END)
        if usuario_atual:
            self.entry_usuario.insert(0, usuario_atual.get("nome", ""))
        self.entry_usuario.configure(state="readonly")

    # --- itens do pedido novo (ainda não salvo) ---
    def _buscar_funcionario(self, _evento=None):
        texto = self.entry_funcionario.get().strip()
        if not texto:
            self.id_funcionario_selecionado = None
            messagebox.showwarning("Funcionário", "Digite o nome ou código do funcionário.")
            return "break"
        funcionarios = listar_funcionarios()
        if texto.replace("#", "").isdigit():
            id_funcionario = int(texto.replace("#", ""))
            encontrados = [f for f in funcionarios if f.id_funcionario == id_funcionario]
        else:
            termo = texto.casefold()
            exatos = [f for f in funcionarios if f.nome.casefold() == termo]
            encontrados = exatos or [f for f in funcionarios if termo in f.nome.casefold()]
        if not encontrados:
            self.id_funcionario_selecionado = None
            messagebox.showwarning("Funcionário não encontrado", f"Nenhum funcionário encontrado para: {texto}")
            return "break"
        if len(encontrados) > 1:
            nomes = "\n".join(f"#{f.id_funcionario} - {f.nome}" for f in encontrados[:10])
            if len(encontrados) > 10:
                nomes += "\n..."
            self.id_funcionario_selecionado = None
            messagebox.showwarning("Mais de um funcionário encontrado", "Refine a busca digitando o nome completo ou o código.\n\n" + nomes)
            return "break"
        funcionario = encontrados[0]
        self.id_funcionario_selecionado = funcionario.id_funcionario
        self.entry_funcionario.delete(0, tk.END)
        self.entry_funcionario.insert(0, funcionario.nome)
        return "break"

    def _reservado_no_pedido(self, id_produto, id_tamanho):
        """Quantidade do mesmo produto/tamanho já lançada neste pedido (ainda não salvo)."""
        return sum(i["quantidade"] for i in self.itens_pendentes
                   if i["id_produto"] == id_produto and i["id_tamanho"] == id_tamanho)

    def _saldo_restante(self, id_produto, id_tamanho):
        """(saldo no estoque, já neste pedido, restante) ou None se não deu para consultar."""
        try:
            saldo = int(consultar_saldo(id_produto, id_tamanho))
        except Exception:
            return None
        reservado = self._reservado_no_pedido(id_produto, id_tamanho)
        return saldo, reservado, saldo - reservado

    def _atualizar_saldo(self, _evento=None):
        id_produto = extrair_id(self.combo_produto_item.get())
        id_tamanho = extrair_id(self.combo_tamanho_item.get())
        if id_produto is None or id_tamanho is None:
            self.lbl_saldo.configure(text=self.TEXTO_SALDO_VAZIO, foreground="#666")
            return
        dados = self._saldo_restante(id_produto, id_tamanho)
        if dados is None:
            self.lbl_saldo.configure(text="Não foi possível consultar o saldo agora.", foreground="#666")
            return
        saldo, reservado, restante = dados
        texto = f"Em estoque: {saldo}"
        if reservado:
            texto += f"   |   já neste pedido: {reservado}   |   restam: {restante}"
        cor = "#1a7f37"
        qtd = self.entry_quantidade_item.get().strip()
        if restante <= 0:
            cor = "firebrick"
            texto += "   -   sem saldo para este item"
        elif qtd.isdigit() and int(qtd) > restante:
            cor = "firebrick"
            texto += f"   -   quantidade acima do saldo ({qtd})"
        self.lbl_saldo.configure(text=texto, foreground=cor)

    def adicionar_item_pendente(self):
        id_produto = extrair_id(self.combo_produto_item.get())
        id_tamanho = extrair_id(self.combo_tamanho_item.get())
        quantidade_texto = self.entry_quantidade_item.get().strip()

        if id_produto is None or id_tamanho is None:
            messagebox.showwarning("Campos obrigatórios", "Escolha o produto e o tamanho do item.")
            return
        if not quantidade_texto.isdigit() or int(quantidade_texto) <= 0:
            messagebox.showwarning("Quantidade inválida", "Digite um número inteiro maior que zero.")
            return

        dados = self._saldo_restante(id_produto, id_tamanho)
        if dados is not None:
            saldo, reservado, restante = dados
            if int(quantidade_texto) > restante:
                messagebox.showwarning(
                    "Estoque insuficiente",
                    f"{self.combo_produto_item.get()} - tamanho {self.combo_tamanho_item.get()}\n\n"
                    f"Em estoque: {saldo}\n"
                    f"Já neste pedido: {reservado}\n"
                    f"Ainda disponível: {max(restante, 0)}\n"
                    f"Você pediu: {quantidade_texto}",
                )
                return

        item = {"id_produto": id_produto, "id_tamanho": id_tamanho, "quantidade": int(quantidade_texto)}
        self.itens_pendentes.append(item)
        self.tree_itens_pendentes.insert("", "end", values=(
            self.combo_produto_item.get(), self.combo_tamanho_item.get(), item["quantidade"]
        ))
        self.combo_produto_item.set("")
        self.combo_tamanho_item.set("")
        self.entry_quantidade_item.delete(0, tk.END)
        self._atualizar_saldo()
        self.combo_produto_item.focus_set()

    def remover_item_pendente(self):
        selecionado = self.tree_itens_pendentes.selection()
        if not selecionado:
            messagebox.showwarning("Nada selecionado", "Selecione um item da lista pra remover.")
            return
        indice = self.tree_itens_pendentes.index(selecionado[0])
        self.tree_itens_pendentes.delete(selecionado[0])
        del self.itens_pendentes[indice]
        self._atualizar_saldo()

    def limpar_formulario_novo(self):
        self.id_funcionario_selecionado = None
        self.entry_funcionario.delete(0, tk.END)
        self.combo_setor.set("")
        self.entry_data.delete(0, tk.END)
        self.entry_data.insert(0, date.today().strftime("%d/%m/%Y"))
        self.entry_observacao.delete(0, tk.END)
        self.itens_pendentes = []
        for linha in self.tree_itens_pendentes.get_children():
            self.tree_itens_pendentes.delete(linha)
        self.combo_produto_item.set("")
        self.combo_tamanho_item.set("")
        self.entry_quantidade_item.delete(0, tk.END)
        self._atualizar_saldo()

    def _ler_data(self):
        """Data do campo; None (com aviso) se estiver inválida - nesse caso não salvar."""
        return ler_data_campo(self.entry_data)

    def salvar_pedido(self):
        if not tem_permissao("dar_baixa"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para realizar esta operação."); return
        id_funcionario = self.id_funcionario_selecionado
        id_setor_loja = extrair_id(self.combo_setor.get())
        usuario_atual = obter_usuario_atual()
        id_usuario = usuario_atual.get("id_usuario") if usuario_atual else None
        observacao = self.entry_observacao.get().strip() or None
        data_saida = self._ler_data()
        if data_saida is None:
            return

        if id_funcionario is None or id_setor_loja is None or id_usuario is None:
            messagebox.showwarning("Campos obrigatórios", "Escolha funcionário e setor/loja. O usuário da baixa é definido automaticamente pelo login.")
            return
        if not self.itens_pendentes:
            messagebox.showwarning("Sem itens", "Adicione pelo menos um item ao pedido.")
            return

        try:
            pedido = criar_pedido_saida(
                id_funcionario, id_setor_loja, id_usuario, self.itens_pendentes,
                data_saida=data_saida, observacao=observacao,
            )
        except ValueError as e:
            messagebox.showerror("Erro", str(e))
            return

        numero = pedido.id_pedido_saida
        quantidade_itens = len(self.itens_pendentes)
        self.limpar_formulario_novo()
        self.atualizar_lista_pedidos()
        self._oferecer_termo(numero, quantidade_itens)

    def _oferecer_termo(self, numero, quantidade_itens):
        """Confirma o pedido e, se o usuário puder, já oferece gerar o Termo de Responsabilidade."""
        texto = f"Pedido #{numero} registrado com {quantidade_itens} item(ns)!"
        abrir_termo = getattr(self.winfo_toplevel(), "abrir_termo_do_pedido", None)
        if callable(abrir_termo) and tem_permissao("gerar_termo"):
            if messagebox.askyesno("Pedido registrado", texto + "\n\nDeseja gerar o Termo de Responsabilidade agora?"):
                abrir_termo(numero)
        else:
            messagebox.showinfo("Sucesso", texto)

    # --- lista de pedidos existentes ---
    def atualizar_lista_pedidos(self):
        for linha in self.tree_pedidos.get_children():
            self.tree_pedidos.delete(linha)
        self.cache_pedidos = {}
        for p in listar_pedidos_saida():
            self.cache_pedidos[p.id_pedido_saida] = p
            self.tree_pedidos.insert("", "end", values=(
                p.id_pedido_saida, p.funcionario.nome, p.setor_loja.nome,
                p.data_saida.strftime("%d/%m/%Y") if p.data_saida else "", p.usuario.nome, len(p.itens),
            ))
        self.pedido_selecionado_id = None

    def _ao_selecionar_pedido(self, _evento):
        selecionado = self.tree_pedidos.selection()
        if not selecionado:
            return
        self.pedido_selecionado_id = int(self.tree_pedidos.item(selecionado[0], "values")[0])

    def _ao_clicar_pedido(self, evento):
        """Duplo clique numa linha abre o popup do pedido (título não abre pedido)."""
        if self.tree_pedidos.identify_region(evento.x, evento.y) != "cell":
            return
        linha = self.tree_pedidos.identify_row(evento.y)
        if linha:
            self._abrir_popup_pedido(int(self.tree_pedidos.item(linha, "values")[0]))

    def _ao_enter_pedido(self, _evento=None):
        selecionado = self.tree_pedidos.selection()
        if selecionado:
            self._abrir_popup_pedido(int(self.tree_pedidos.item(selecionado[0], "values")[0]))
        return "break"

    def _abrir_popup_pedido(self, id_pedido):
        dialogo = getattr(self, "_dialogo_pedido", None)
        try:
            if dialogo is not None and dialogo.winfo_exists():
                dialogo.lift()
                return
        except tk.TclError:
            pass
        self.pedido_selecionado_id = id_pedido
        try:
            pedido = buscar_pedido_saida(id_pedido)
        except Exception as exc:
            messagebox.showerror("Erro", f"Não foi possível carregar o pedido: {exc}")
            return
        if pedido is None:
            messagebox.showwarning("Pedido não encontrado", "Esse pedido não existe mais. A lista será atualizada.")
            self.atualizar_lista_pedidos()
            return
        abrir_termo = getattr(self.winfo_toplevel(), "abrir_termo_do_pedido", None)
        if not (callable(abrir_termo) and tem_permissao("gerar_termo")):
            abrir_termo = None
        self._dialogo_pedido = PedidoSaidaDialog(self, pedido, abrir_termo)

    def excluir_pedido(self):
        if not tem_permissao("excluir_produtos"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para realizar esta operação."); return
        if self.pedido_selecionado_id is None:
            messagebox.showwarning("Nada selecionado", "Selecione um pedido na lista antes de excluir.")
            return
        if not messagebox.askyesno("Confirmar exclusão", "Excluir o pedido inteiro (com todos os itens)?"):
            return
        excluir_pedido_saida(self.pedido_selecionado_id)
        self.atualizar_lista_pedidos()
