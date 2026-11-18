import tkinter as tk
from tkinter import ttk, messagebox
from app.repositories.crud_usuario import (criar_usuario, listar_usuarios, atualizar_usuario, excluir_usuario, obter_permissoes, salvar_permissoes, NIVEIS_VALIDOS)
from app.auth import PERMISSOES, tem_permissao, atualizar_sessao_permissoes

class UsuariosFrame(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent,padding=10); self.id_selecionado=None; self.vars={}; self.cache={}
        self._montar_widgets(); self.atualizar_lista()
    def _montar_widgets(self):
        form=ttk.LabelFrame(self,text="Configuração de Usuário",padding=10); form.pack(fill="x",pady=(0,10))
        ttk.Label(form,text="Nome:").grid(row=0,column=0,sticky="w",pady=3); self.entry_nome=ttk.Entry(form,width=35); self.entry_nome.grid(row=0,column=1,pady=3)
        ttk.Label(form,text="Login:").grid(row=1,column=0,sticky="w",pady=3); self.entry_login=ttk.Entry(form,width=35); self.entry_login.grid(row=1,column=1,pady=3)
        ttk.Label(form,text="Senha:").grid(row=2,column=0,sticky="w",pady=3); self.entry_senha=ttk.Entry(form,width=35,show="*"); self.entry_senha.grid(row=2,column=1,pady=3)
        ttk.Label(form,text="Nível:").grid(row=3,column=0,sticky="w",pady=3); self.combo_nivel=ttk.Combobox(form,width=32,state="readonly",values=list(NIVEIS_VALIDOS)); self.combo_nivel.grid(row=3,column=1,pady=3); self.combo_nivel.current(1)
        botoes=ttk.Frame(form); botoes.grid(row=4,column=0,columnspan=2,sticky="w",pady=7)
        ttk.Button(botoes,text="Novo",command=self.limpar_formulario).pack(side="left",padx=3); ttk.Button(botoes,text="Salvar usuário",command=self.salvar).pack(side="left",padx=3); ttk.Button(botoes,text="Excluir",command=self.excluir).pack(side="left",padx=3)
        perms=ttk.LabelFrame(self,text="Permissões individuais do usuário selecionado",padding=10); perms.pack(fill="x",pady=(0,10))
        for i,(chave,nome) in enumerate(PERMISSOES.items()):
            v=tk.BooleanVar(value=False); self.vars[chave]=v
            ttk.Checkbutton(perms,text=nome,variable=v).grid(row=i//3,column=i%3,sticky="w",padx=8,pady=3)
        ttk.Button(perms,text="Salvar permissões",command=self.salvar_permissoes).grid(row=(len(PERMISSOES)+2)//3,column=0,sticky="w",pady=(8,0))
        colunas=("id","nome","login","nivel"); self.tree=ttk.Treeview(self,columns=colunas,show="headings",height=9)
        for c,t,w in [("id","Id",50),("nome","Nome",220),("login","Login",160),("nivel","Nível",120)]: self.tree.heading(c,text=t); self.tree.column(c,width=w)
        self.tree.pack(fill="both",expand=True); self.tree.bind("<<TreeviewSelect>>",self._ao_selecionar)
    def atualizar_lista(self):
        for x in self.tree.get_children(): self.tree.delete(x)
        self.cache={}
        for u in listar_usuarios(): self.cache[u.id_usuario]=u; self.tree.insert("","end",values=(u.id_usuario,u.nome,u.login,u.nivel_acesso))
    def _ao_selecionar(self,_):
        sel=self.tree.selection()
        if not sel:return
        uid=int(self.tree.item(sel[0],"values")[0]); u=self.cache.get(uid)
        if not u:return
        self.id_selecionado=uid; self.entry_nome.delete(0,tk.END); self.entry_nome.insert(0,u.nome); self.entry_login.configure(state="normal"); self.entry_login.delete(0,tk.END); self.entry_login.insert(0,u.login); self.entry_login.configure(state="disabled"); self.combo_nivel.set(u.nivel_acesso); self.entry_senha.delete(0,tk.END)
        perms=obter_permissoes(uid)
        for k,v in self.vars.items(): v.set(k in perms or u.nivel_acesso=="Administrador")
    def limpar_formulario(self):
        self.id_selecionado=None; self.entry_nome.delete(0,tk.END); self.entry_login.configure(state="normal"); self.entry_login.delete(0,tk.END); self.entry_senha.delete(0,tk.END); self.combo_nivel.set("Operador"); self.tree.selection_remove(self.tree.selection());
        for v in self.vars.values():v.set(False)
    def salvar(self):
        nome=self.entry_nome.get().strip(); login=self.entry_login.get().strip(); nivel=self.combo_nivel.get(); senha=self.entry_senha.get()
        if not nome or not login: messagebox.showwarning("Campos obrigatórios","Informe nome e login."); return
        try:
            if self.id_selecionado is None:
                u=criar_usuario(nome,login,nivel,senha or "123456",{k for k,v in self.vars.items() if v.get()})
                self.id_selecionado=u.id_usuario; messagebox.showinfo("Sucesso","Usuário cadastrado. Senha inicial: " + (senha or "123456"))
            else:
                atualizar_usuario(self.id_selecionado,nome=nome,nivel_acesso=nivel,senha=senha or None); self.salvar_permissoes(mostrar=False); messagebox.showinfo("Sucesso","Usuário atualizado.")
        except Exception as e: messagebox.showerror("Erro",str(e)); return
        self.atualizar_lista()
    def salvar_permissoes(self,mostrar=True):
        if self.id_selecionado is None: messagebox.showwarning("Seleção","Selecione um usuário primeiro."); return
        try:
            salvar_permissoes(self.id_selecionado,{k for k,v in self.vars.items() if v.get()}); atualizar_sessao_permissoes()
            if mostrar: messagebox.showinfo("Sucesso","Permissões salvas com sucesso.")
        except Exception as e: messagebox.showerror("Erro",str(e))
    def excluir(self):
        if self.id_selecionado is None: messagebox.showwarning("Seleção","Selecione um usuário."); return
        if not messagebox.askyesno("Confirmar","Excluir este usuário?"):return
        try: excluir_usuario(self.id_selecionado)
        except Exception as e: messagebox.showerror("Erro",str(e)); return
        self.limpar_formulario(); self.atualizar_lista()
