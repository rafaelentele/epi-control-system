"""Tela de cadastro de empresas: razão social e CNPJ."""
import tkinter as tk
from tkinter import ttk, messagebox
from gui.utils import TreeviewBusca, adicionar_pesquisa

class EmpresaFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        from app.repositories.crud_simple import criar_empresa, listar_empresas, atualizar_empresa, excluir_empresa
        self.criar_fn, self.listar_fn = criar_empresa, listar_empresas
        self.atualizar_fn, self.excluir_fn = atualizar_empresa, excluir_empresa
        self.id_selecionado = None
        form = ttk.LabelFrame(self, text="Cadastro de Empresas", padding=10); form.pack(fill="x", pady=(0,10))
        ttk.Label(form, text="Razão social:").grid(row=0,column=0,sticky="w",padx=(0,6),pady=4)
        self.razao = ttk.Entry(form,width=55); self.razao.grid(row=0,column=1,sticky="w",pady=4)
        ttk.Label(form, text="CNPJ:").grid(row=1,column=0,sticky="w",padx=(0,6),pady=4)
        self.cnpj = ttk.Entry(form,width=25); self.cnpj.grid(row=1,column=1,sticky="w",pady=4)
        botoes=ttk.Frame(form); botoes.grid(row=2,column=0,columnspan=2,sticky="w",pady=(8,0))
        ttk.Button(botoes,text="Novo",command=self.limpar).pack(side="left",padx=(0,6))
        ttk.Button(botoes,text="Salvar",command=self.salvar).pack(side="left",padx=(0,6))
        ttk.Button(botoes,text="Excluir selecionada",command=self.excluir).pack(side="left")
        self.tree=TreeviewBusca(self,columns=("id","razao","cnpj"),show="headings",height=12)
        for col,titulo in (("id","ID"),("razao","Razão social"),("cnpj","CNPJ")): self.tree.heading(col,text=titulo)
        self.tree.column("id",width=60,anchor="center"); self.tree.column("razao",width=430); self.tree.column("cnpj",width=180)
        self.tree.pack(fill="both",expand=True); adicionar_pesquisa(self.tree); self.tree.bind("<<TreeviewSelect>>",self.selecionar)
        self.atualizar_lista()
    def atualizar_lista(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for e in self.listar_fn(): self.tree.insert("","end",values=(e.id_empresa,e.razao_social,e.cnpj))
    def selecionar(self,_event=None):
        sel=self.tree.selection()
        if not sel:return
        v=self.tree.item(sel[0],"values"); self.id_selecionado=int(v[0])
        self.razao.delete(0,tk.END); self.razao.insert(0,v[1]); self.cnpj.delete(0,tk.END); self.cnpj.insert(0,v[2])
    def limpar(self):
        self.id_selecionado=None; self.razao.delete(0,tk.END); self.cnpj.delete(0,tk.END); self.tree.selection_remove(self.tree.selection())
    def salvar(self):
        razao=self.razao.get().strip(); cnpj=self.cnpj.get().strip()
        if not razao or not cnpj: messagebox.showwarning("Campos obrigatórios","Preencha razão social e CNPJ."); return
        try:
            if self.id_selecionado is None:self.criar_fn(razao,cnpj)
            else:self.atualizar_fn(self.id_selecionado,razao,cnpj)
        except Exception as e: messagebox.showerror("Erro ao salvar empresa",str(e)); return
        messagebox.showinfo("Sucesso","Empresa salva com sucesso."); self.limpar(); self.atualizar_lista()
    def excluir(self):
        if self.id_selecionado is None: messagebox.showwarning("Seleção necessária","Selecione uma empresa."); return
        if not messagebox.askyesno("Confirmar","Deseja excluir a empresa selecionada?"):return
        try:self.excluir_fn(self.id_selecionado)
        except Exception as e:messagebox.showerror("Não foi possível excluir",str(e));return
        self.limpar(); self.atualizar_lista()
