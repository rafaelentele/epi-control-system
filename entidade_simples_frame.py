"""Tela genérica para cadastros simples, com suporte opcional a empresa."""
import tkinter as tk
from tkinter import ttk, messagebox
from sqlalchemy import inspect as sqlalchemy_inspect
from gui.utils import TreeviewBusca, adicionar_pesquisa
from app.repositories.crud_simple import listar_empresas


class EntidadeSimplesFrame(ttk.Frame):
    def __init__(self, parent, titulo, criar_fn, listar_fn, atualizar_fn, excluir_fn,
                 tem_contato=False, tem_empresa=False, tem_cpf=False, permissao_consulta=None,
                 permissao_cadastro=None, permissao_edicao=None, permissao_exclusao=None):
        super().__init__(parent, padding=10)
        self.titulo, self.criar_fn, self.listar_fn = titulo, criar_fn, listar_fn
        self.atualizar_fn, self.excluir_fn = atualizar_fn, excluir_fn
        self.tem_contato, self.tem_empresa, self.tem_cpf = tem_contato, tem_empresa, tem_cpf
        self.id_selecionado = None
        self._empresa_por_nome = {}
        from app.auth import tem_permissao
        self.tem_permissao = tem_permissao
        self.permissao_consulta, self.permissao_cadastro = permissao_consulta, permissao_cadastro
        self.permissao_edicao, self.permissao_exclusao = permissao_edicao, permissao_exclusao
        self._montar_widgets()
        self.atualizar_lista()

    def _montar_widgets(self):
        form = ttk.LabelFrame(self, text=f"Cadastro de {self.titulo}", padding=10)
        form.pack(fill="x", pady=(0, 10))
        ttk.Label(form, text="Nome:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.entry_nome = ttk.Entry(form, width=40)
        self.entry_nome.grid(row=0, column=1, sticky="w", pady=4)
        linha = 1
        if self.tem_cpf:
            ttk.Label(form, text="CPF (obrigatório):").grid(row=linha, column=0, sticky="w", padx=(0, 6), pady=4)
            self.entry_cpf = ttk.Entry(form, width=40)
            self.entry_cpf.grid(row=linha, column=1, sticky="w", pady=4)
            linha += 1
        if self.tem_empresa:
            ttk.Label(form, text="Empresa (obrigatório):").grid(row=linha, column=0, sticky="w", padx=(0, 6), pady=4)
            self.combo_empresa = ttk.Combobox(form, width=38, state="readonly")
            self.combo_empresa.grid(row=linha, column=1, sticky="w", pady=4)
            linha += 1
            self._carregar_empresas()
        if self.tem_contato:
            ttk.Label(form, text="Contato:").grid(row=linha, column=0, sticky="w", padx=(0, 6), pady=4)
            self.entry_contato = ttk.Entry(form, width=40)
            self.entry_contato.grid(row=linha, column=1, sticky="w", pady=4)
            linha += 1
        botoes = ttk.Frame(form); botoes.grid(row=linha, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.btn_novo = ttk.Button(botoes, text="Novo", command=self.limpar_formulario); self.btn_novo.pack(side="left", padx=(0, 6))
        self.btn_salvar = ttk.Button(botoes, text="Salvar", command=self.salvar); self.btn_salvar.pack(side="left", padx=(0, 6))
        self.btn_excluir = ttk.Button(botoes, text="Excluir selecionado", command=self.excluir); self.btn_excluir.pack(side="left")
        if self.permissao_cadastro and not self.tem_permissao(self.permissao_cadastro):
            self.btn_novo.state(["disabled"]); self.btn_salvar.state(["disabled"])
        if self.permissao_exclusao and not self.tem_permissao(self.permissao_exclusao): self.btn_excluir.state(["disabled"])
        colunas = ["id", "nome"]
        if self.tem_cpf: colunas.append("cpf")
        if self.tem_empresa: colunas.append("empresa")
        if self.tem_contato: colunas.append("contato")
        self.tree = TreeviewBusca(self, columns=tuple(colunas), show="headings", height=12)
        self.tree.heading("id", text="Id"); self.tree.heading("nome", text="Nome")
        self.tree.column("id", width=60, anchor="center"); self.tree.column("nome", width=260)
        if self.tem_cpf:
            self.tree.heading("cpf", text="CPF"); self.tree.column("cpf", width=150, anchor="center")
        if self.tem_empresa:
            self.tree.heading("empresa", text="Empresa"); self.tree.column("empresa", width=260)
        if self.tem_contato:
            self.tree.heading("contato", text="Contato"); self.tree.column("contato", width=180)
        self.tree.pack(fill="both", expand=True); adicionar_pesquisa(self.tree)
        self.tree.bind("<<TreeviewSelect>>", self._ao_selecionar)

    def _carregar_empresas(self):
        empresas = listar_empresas()
        self._empresa_por_nome = {e.razao_social: e.id_empresa for e in empresas}
        self.combo_empresa["values"] = [e.razao_social for e in empresas]

    def atualizar_lista(self):
        for linha in self.tree.get_children(): self.tree.delete(linha)
        itens = self.listar_fn()
        for item in itens:
            # Busca a chave primária real do modelo, sem depender da ordem
            # dos atributos carregados pelo SQLAlchemy (ex.: id_empresa).
            estado = sqlalchemy_inspect(item)
            chave_primaria = estado.mapper.primary_key[0].key
            id_valor = getattr(item, chave_primaria)
            valores = [id_valor, item.nome]
            if self.tem_cpf: valores.append(getattr(item, "cpf", None) or "(não informado)")
            if self.tem_empresa: valores.append(item.empresa.razao_social if item.empresa else "(sem empresa)")
            if self.tem_contato: valores.append(item.contato or "")
            self.tree.insert("", "end", values=tuple(valores))

    def _ao_selecionar(self, _evento):
        selecionado = self.tree.selection()
        if not selecionado: return
        valores = self.tree.item(selecionado[0], "values")
        self.id_selecionado = int(valores[0])
        self.entry_nome.delete(0, tk.END); self.entry_nome.insert(0, valores[1])
        pos = 2
        if self.tem_cpf:
            self.entry_cpf.delete(0, tk.END)
            cpf = valores[pos] if len(valores) > pos else ""
            self.entry_cpf.insert(0, "" if cpf == "(não informado)" else cpf)
            pos += 1
        if self.tem_empresa:
            self._carregar_empresas()
            nome_empresa = valores[pos]
            self.combo_empresa.set("" if nome_empresa == "(sem empresa)" else nome_empresa)
            pos += 1
        if self.tem_contato:
            self.entry_contato.delete(0, tk.END); self.entry_contato.insert(0, valores[pos] if len(valores) > pos else "")

    def limpar_formulario(self):
        self.id_selecionado = None
        self.entry_nome.delete(0, tk.END)
        if self.tem_cpf: self.entry_cpf.delete(0, tk.END)
        if self.tem_empresa: self.combo_empresa.set("")
        if self.tem_contato: self.entry_contato.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def salvar(self):
        if self.id_selecionado is None and self.permissao_cadastro and not self.tem_permissao(self.permissao_cadastro):
            messagebox.showerror("Sem permissão", "Você não tem permissão para cadastrar este item."); return
        if self.id_selecionado is not None and self.permissao_edicao and not self.tem_permissao(self.permissao_edicao):
            messagebox.showerror("Sem permissão", "Você não tem permissão para editar este item."); return
        nome = self.entry_nome.get().strip()
        if not nome:
            messagebox.showwarning("Campo obrigatório", "Digite o nome antes de salvar."); return
        cpf = self.entry_cpf.get().strip() if self.tem_cpf else None
        if self.tem_cpf and not cpf:
            messagebox.showwarning("Campo obrigatório", "Informe o CPF do funcionário."); return
        try:
            if self.tem_empresa and self.tem_cpf:
                self._carregar_empresas()
                empresa_nome = self.combo_empresa.get().strip()
                id_empresa = self._empresa_por_nome.get(empresa_nome)
                if not id_empresa:
                    messagebox.showwarning("Campo obrigatório", "Cadastre e selecione a empresa do funcionário."); return
                if self.id_selecionado is None: self.criar_fn(nome, cpf, id_empresa)
                else: self.atualizar_fn(self.id_selecionado, nome, cpf, id_empresa)
            elif self.tem_empresa:
                self._carregar_empresas()
                empresa_nome = self.combo_empresa.get().strip()
                id_empresa = self._empresa_por_nome.get(empresa_nome)
                if not id_empresa:
                    messagebox.showwarning("Campo obrigatório", "Cadastre e selecione a empresa do funcionário."); return
                if self.id_selecionado is None: self.criar_fn(nome, id_empresa)
                else: self.atualizar_fn(self.id_selecionado, nome, id_empresa)
            elif self.tem_contato:
                contato = self.entry_contato.get().strip() or None
                if self.id_selecionado is None: self.criar_fn(nome, contato)
                else: self.atualizar_fn(self.id_selecionado, nome, contato)
            elif self.id_selecionado is None: self.criar_fn(nome)
            else: self.atualizar_fn(self.id_selecionado, nome)
            messagebox.showinfo("Sucesso", "Cadastro salvo com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", str(e)); return
        self.limpar_formulario(); self.atualizar_lista()

    def excluir(self):
        if self.permissao_exclusao and not self.tem_permissao(self.permissao_exclusao):
            messagebox.showerror("Sem permissão", "Você não tem permissão para excluir este item."); return
        if self.id_selecionado is None:
            messagebox.showwarning("Nada selecionado", "Selecione um item na lista antes de excluir."); return
        if not messagebox.askyesno("Confirmar exclusão", "Tem certeza que deseja excluir este item?"): return
        try:
            sucesso = self.excluir_fn(self.id_selecionado)
            if not sucesso: messagebox.showerror("Erro", "Item não encontrado (pode já ter sido excluído).")
        except Exception as e:
            messagebox.showerror("Erro", str(e)); return
        self.limpar_formulario(); self.atualizar_lista()
