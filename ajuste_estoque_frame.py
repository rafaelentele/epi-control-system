import tkinter as tk
from tkinter import ttk, messagebox

from app.auth import tem_permissao, obter_usuario_atual
from app.repositories.crud_ajuste_estoque import saldo_produto_tamanho, criar_ajuste, listar_ajustes
from app.repositories.crud_produtos import listar_produtos
from app.repositories.crud_simple import listar_tamanhos
from gui.utils import formatar_opcao, extrair_id, ComboBusca


class AjusteEstoqueFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.usuario = obter_usuario_atual() or {}
        ttk.Label(self, text="Ajuste de Estoque", font=("TkDefaultFont", 15, "bold")).pack(anchor="w")
        ttk.Label(self, text="Use esta tela para conciliar o estoque do sistema com a contagem física. O ajuste é registrado na auditoria.").pack(anchor="w", pady=(2, 12))
        if not tem_permissao("ajustar_estoque"):
            ttk.Label(self, text="Seu usuário não possui permissão para ajustar o estoque.", font=("TkDefaultFont", 12, "bold")).pack(pady=40)
            return
        form=ttk.LabelFrame(self,text="Novo ajuste",padding=10); form.pack(fill="x")
        ttk.Label(form,text="Produto:").grid(row=0,column=0,sticky="w")
        self.combo_produto=ComboBusca(form,width=42); self.combo_produto.grid(row=0,column=1,padx=6,pady=4,sticky="w")
        ttk.Label(form,text="Tamanho:").grid(row=0,column=2,sticky="w")
        self.combo_tamanho=ttk.Combobox(form,width=12,state="readonly"); self.combo_tamanho.grid(row=0,column=3,padx=6,pady=4)
        self.combo_produto.bind("<<ComboboxSelected>>",lambda e:self.atualizar_estoque_atual())
        self.combo_tamanho.bind("<<ComboboxSelected>>",lambda e:self.atualizar_estoque_atual())
        ttk.Label(form,text="Estoque atual:").grid(row=1,column=0,sticky="w")
        self.lbl_atual=ttk.Label(form,text="-",font=("TkDefaultFont",11,"bold")); self.lbl_atual.grid(row=1,column=1,sticky="w",padx=6)
        ttk.Label(form,text="Quantidade física:").grid(row=2,column=0,sticky="w")
        self.entry_fisico=ttk.Entry(form,width=12); self.entry_fisico.grid(row=2,column=1,sticky="w",padx=6,pady=4); self.entry_fisico.bind("<KeyRelease>",lambda e:self.atualizar_diferenca())
        ttk.Label(form,text="Diferença:").grid(row=2,column=2,sticky="w")
        self.lbl_diferenca=ttk.Label(form,text="-",font=("TkDefaultFont",11,"bold")); self.lbl_diferenca.grid(row=2,column=3,sticky="w",padx=6)
        ttk.Label(form,text="Motivo:").grid(row=3,column=0,sticky="w")
        self.combo_motivo=ttk.Combobox(form,width=42,state="readonly",values=["Inventário físico","Perda","Extravio","Avaria","Devolução","Correção de cadastro","Outros"]); self.combo_motivo.grid(row=3,column=1,padx=6,pady=4,sticky="w")
        ttk.Label(form,text="Observação:").grid(row=4,column=0,sticky="nw")
        self.entry_obs=tk.Text(form,width=58,height=3); self.entry_obs.grid(row=4,column=1,columnspan=3,padx=6,pady=4,sticky="w")
        botoes=ttk.Frame(form); botoes.grid(row=5,column=1,columnspan=3,sticky="w",pady=(8,0))
        ttk.Button(botoes,text="Confirmar ajuste",command=self.confirmar).pack(side="left",padx=(0,6))
        ttk.Button(botoes,text="Limpar",command=self.limpar).pack(side="left")
        hist=ttk.LabelFrame(self,text="Últimos ajustes",padding=8); hist.pack(fill="both",expand=True,pady=(12,0))
        cols=[("data","Data/Hora",145),("produto","Produto",210),("tamanho","Tamanho",80),("anterior","Antes",65),("posterior","Depois",65),("diferenca","Diferença",80),("motivo","Motivo",150),("usuario","Usuário",130)]
        self.tree=ttk.Treeview(hist,columns=[c[0] for c in cols],show="headings",height=10)
        for key,title,w in cols: self.tree.heading(key,text=title); self.tree.column(key,width=w,anchor="center")
        self.tree.pack(fill="both",expand=True)
        self.atualizar_combos(); self.carregar_historico()

    def atualizar_dados(self):
        """Recarrega combos e histórico (chamado ao abrir a tela pelo menu)."""
        if hasattr(self, "combo_produto"):
            self.atualizar_combos()
            self.carregar_historico()

    def atualizar_combos(self):
        self.combo_produto["values"]=[formatar_opcao(p.id_produto,p.nome) for p in listar_produtos()]
        self.combo_tamanho["values"]=[formatar_opcao(t.id_tamanho,t.nome) for t in listar_tamanhos()]

    def atualizar_estoque_atual(self):
        pid=extrair_id(self.combo_produto.get()); tid=extrair_id(self.combo_tamanho.get())
        if pid is None or tid is None: self.lbl_atual.config(text="-"); self.atualizar_diferenca(); return
        try: saldo=saldo_produto_tamanho(pid,tid); self.lbl_atual.config(text=str(saldo))
        except Exception as e: self.lbl_atual.config(text="Erro"); messagebox.showerror("Erro",str(e),parent=self)
        self.atualizar_diferenca()

    def atualizar_diferenca(self):
        atual=self.lbl_atual.cget("text"); fis=self.entry_fisico.get().strip()
        try:
            if atual == "-" or not fis.isdigit(): self.lbl_diferenca.config(text="-"); return
            self.lbl_diferenca.config(text=str(int(fis)-int(atual)))
        except ValueError: self.lbl_diferenca.config(text="-")

    def confirmar(self):
        pid=extrair_id(self.combo_produto.get()); tid=extrair_id(self.combo_tamanho.get()); fis=self.entry_fisico.get().strip(); motivo=self.combo_motivo.get().strip(); obs=self.entry_obs.get("1.0",tk.END).strip()
        if pid is None or tid is None: return messagebox.showwarning("Campos obrigatórios","Escolha o produto e o tamanho.",parent=self)
        if not fis.isdigit(): return messagebox.showwarning("Quantidade inválida","Informe a quantidade física como número inteiro maior ou igual a zero.",parent=self)
        if not motivo: return messagebox.showwarning("Campos obrigatórios","Informe o motivo do ajuste.",parent=self)
        atual=saldo_produto_tamanho(pid,tid); posterior=int(fis); delta=posterior-atual
        if delta==0: return messagebox.showinfo("Sem ajuste","A quantidade física já é igual ao estoque do sistema.",parent=self)
        pergunta=f"Produto: {self.combo_produto.get()}\nTamanho: {self.combo_tamanho.get()}\n\nEstoque atual: {atual}\nEstoque físico: {posterior}\nDiferença: {delta:+d}\nMotivo: {motivo}\n\nConfirmar este ajuste?"
        if not messagebox.askyesno("Confirmar ajuste",pergunta,parent=self): return
        try:
            ajuste=criar_ajuste(pid,tid,posterior,motivo,obs,int(self.usuario["id_usuario"]))
            messagebox.showinfo("Ajuste realizado",f"Ajuste #{ajuste.id_ajuste} registrado.\nEstoque: {ajuste.estoque_anterior} → {ajuste.estoque_posterior}.",parent=self)
            self.limpar(); self.carregar_historico()
        except Exception as e: messagebox.showerror("Erro ao ajustar estoque",str(e),parent=self)

    def limpar(self):
        self.combo_produto.set(""); self.combo_tamanho.set(""); self.entry_fisico.delete(0,tk.END); self.combo_motivo.set(""); self.entry_obs.delete("1.0",tk.END); self.lbl_atual.config(text="-"); self.lbl_diferenca.config(text="-")

    def carregar_historico(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        try: registros=listar_ajustes()
        except Exception: registros=[]
        for a in registros:
            self.tree.insert("","end",values=(a.data_ajuste.strftime("%d/%m/%Y %H:%M:%S") if a.data_ajuste else "",a.produto.nome if a.produto else "",a.tamanho.nome if a.tamanho else "",a.estoque_anterior,a.estoque_posterior,f"{a.quantidade_ajuste:+d}",a.motivo,a.usuario.nome if a.usuario else ""))
