import tkinter as tk
from tkinter import ttk, messagebox

from app.auth import (
    PERMISSOES,
    PERMISSOES_OPERADOR_PADRAO,
    obter_usuario_atual,
    atualizar_sessao_permissoes,
)
from app.repositories.crud_usuario import (
    criar_usuario,
    listar_usuarios,
    atualizar_usuario,
    excluir_usuario,
    obter_permissoes,
    salvar_permissoes,
    NIVEIS_VALIDOS,
)


class UsuariosFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.id_selecionado = None
        self.vars = {}
        self.cache = {}
        usuario_atual = obter_usuario_atual() or {}
        if usuario_atual.get("nivel_acesso") != "Administrador":
            ttk.Label(
                self,
                text="Somente o perfil Administrador pode gerenciar usuários e permissões.",
            ).pack(anchor="w", padx=12, pady=12)
            return
        self._montar_widgets()
        self.atualizar_lista()

    def _montar_widgets(self):
        form = ttk.LabelFrame(self, text="Configuração de Usuário", padding=10)
        form.pack(fill="x", pady=(0, 10))
        ttk.Label(form, text="Nome:").grid(row=0, column=0, sticky="w", pady=3)
        self.entry_nome = ttk.Entry(form, width=35)
        self.entry_nome.grid(row=0, column=1, pady=3)
        ttk.Label(form, text="Login:").grid(row=1, column=0, sticky="w", pady=3)
        self.entry_login = ttk.Entry(form, width=35)
        self.entry_login.grid(row=1, column=1, pady=3)
        ttk.Label(form, text="Senha / nova senha:").grid(row=2, column=0, sticky="w", pady=3)
        self.entry_senha = ttk.Entry(form, width=35, show="*")
        self.entry_senha.grid(row=2, column=1, pady=3)
        ttk.Label(form, text="Em branco ao editar mantém a senha atual.").grid(
            row=2, column=2, sticky="w", padx=(8, 0), pady=3
        )
        ttk.Label(form, text="Nível:").grid(row=3, column=0, sticky="w", pady=3)
        self.combo_nivel = ttk.Combobox(
            form, width=32, state="readonly", values=list(NIVEIS_VALIDOS)
        )
        self.combo_nivel.grid(row=3, column=1, pady=3)
        self.combo_nivel.set("Operador")
        self.combo_nivel.bind("<<ComboboxSelected>>", self._ao_mudar_nivel)

        botoes = ttk.Frame(form)
        botoes.grid(row=4, column=0, columnspan=3, sticky="w", pady=7)
        ttk.Button(botoes, text="Novo", command=self.limpar_formulario).pack(side="left", padx=3)
        ttk.Button(botoes, text="Salvar usuário", command=self.salvar).pack(side="left", padx=3)
        ttk.Button(botoes, text="Excluir", command=self.excluir).pack(side="left", padx=3)

        perms = ttk.LabelFrame(self, text="Permissões do usuário", padding=10)
        perms.pack(fill="x", pady=(0, 10))
        for i, (chave, nome) in enumerate(PERMISSOES.items()):
            valor_inicial = chave in PERMISSOES_OPERADOR_PADRAO
            variavel = tk.BooleanVar(value=valor_inicial)
            self.vars[chave] = variavel
            ttk.Checkbutton(perms, text=nome, variable=variavel).grid(
                row=i // 3, column=i % 3, sticky="w", padx=8, pady=3
            )
        ttk.Button(perms, text="Salvar permissões", command=self.salvar_permissoes).grid(
            row=(len(PERMISSOES) + 2) // 3, column=0, sticky="w", pady=(8, 0)
        )

        colunas = ("id", "nome", "login", "nivel")
        self.tree = ttk.Treeview(self, columns=colunas, show="headings", height=9)
        for coluna, rotulo, largura in [
            ("id", "Id", 50),
            ("nome", "Nome", 220),
            ("login", "Login", 160),
            ("nivel", "Nível", 120),
        ]:
            self.tree.heading(coluna, text=rotulo)
            self.tree.column(coluna, width=largura)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._ao_selecionar)

    def _ao_mudar_nivel(self, _evento=None):
        if self.combo_nivel.get() == "Administrador":
            permissoes = set(PERMISSOES)
        elif self.id_selecionado is None:
            permissoes = set(PERMISSOES_OPERADOR_PADRAO)
        else:
            return
        for chave, variavel in self.vars.items():
            variavel.set(chave in permissoes)

    def atualizar_lista(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.cache = {}
        for usuario in listar_usuarios():
            self.cache[usuario.id_usuario] = usuario
            self.tree.insert(
                "", "end",
                values=(usuario.id_usuario, usuario.nome, usuario.login, usuario.nivel_acesso),
            )

    def _ao_selecionar(self, _evento=None):
        selecao = self.tree.selection()
        if not selecao:
            return
        usuario_id = int(self.tree.item(selecao[0], "values")[0])
        usuario = self.cache.get(usuario_id)
        if not usuario:
            return
        self.id_selecionado = usuario_id
        self.entry_nome.delete(0, tk.END)
        self.entry_nome.insert(0, usuario.nome)
        self.entry_login.delete(0, tk.END)
        self.entry_login.insert(0, usuario.login)
        self.entry_senha.delete(0, tk.END)
        self.combo_nivel.set(usuario.nivel_acesso)
        permissoes = obter_permissoes(usuario_id)
        if usuario.nivel_acesso == "Administrador":
            permissoes = set(PERMISSOES)
        for chave, variavel in self.vars.items():
            variavel.set(chave in permissoes)

    def limpar_formulario(self):
        self.id_selecionado = None
        self.entry_nome.delete(0, tk.END)
        self.entry_login.delete(0, tk.END)
        self.entry_senha.delete(0, tk.END)
        self.combo_nivel.set("Operador")
        self.tree.selection_remove(self.tree.selection())
        for chave, variavel in self.vars.items():
            variavel.set(chave in PERMISSOES_OPERADOR_PADRAO)

    def salvar(self):
        nome = self.entry_nome.get().strip()
        login = self.entry_login.get().strip()
        nivel = self.combo_nivel.get()
        senha = self.entry_senha.get()
        if not nome or not login:
            messagebox.showwarning("Campos obrigatórios", "Informe nome e login.")
            return
        permissoes = {chave for chave, variavel in self.vars.items() if variavel.get()}
        try:
            if self.id_selecionado is None:
                if not senha:
                    messagebox.showwarning("Senha obrigatória", "Defina uma senha própria para o novo usuário.")
                    return
                usuario = criar_usuario(nome, login, nivel, senha, permissoes)
                self.id_selecionado = usuario.id_usuario
                messagebox.showinfo("Sucesso", "Usuário cadastrado.")
            else:
                atualizar_usuario(
                    self.id_selecionado,
                    nome=nome,
                    login=login,
                    nivel_acesso=nivel,
                    senha=senha or None,
                )
                salvar_permissoes(self.id_selecionado, permissoes)
                atualizar_sessao_permissoes()
                messagebox.showinfo("Sucesso", "Usuário atualizado.")
        except Exception as erro:
            messagebox.showerror("Erro", str(erro))
            return
        self.atualizar_lista()

    def salvar_permissoes(self, mostrar=True):
        if self.id_selecionado is None:
            messagebox.showwarning("Seleção", "Selecione um usuário primeiro.")
            return
        try:
            selecionadas = {chave for chave, variavel in self.vars.items() if variavel.get()}
            salvar_permissoes(self.id_selecionado, selecionadas)
            atualizar_sessao_permissoes()
            if mostrar:
                messagebox.showinfo("Sucesso", "Permissões salvas com sucesso.")
        except Exception as erro:
            messagebox.showerror("Erro", str(erro))

    def excluir(self):
        if self.id_selecionado is None:
            messagebox.showwarning("Seleção", "Selecione um usuário.")
            return
        if not messagebox.askyesno("Confirmar", "Excluir este usuário?"):
            return
        try:
            excluir_usuario(self.id_selecionado)
        except Exception as erro:
            messagebox.showerror("Erro", str(erro))
            return
        self.limpar_formulario()
        self.atualizar_lista()
