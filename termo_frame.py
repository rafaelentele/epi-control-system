import os
import tempfile
import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox, filedialog

from app.repositories.crud_saida import buscar_pedido_saida
from app.services.termo_responsabilidade import gerar_termo_responsabilidade_pdf
from app.term_config import carregar_configuracoes, modelos_ativos
from app.auth import tem_permissao
from gui.utils import ler_data_campo


class TermoResponsabilidadeFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.pedido_atual = None
        self.cfg = carregar_configuracoes()
        self.modelos = []
        self._montar_widgets()
        self._carregar_modelos()

    def _montar_widgets(self):
        busca = ttk.LabelFrame(self, text="Pedido de Entrega", padding=10)
        busca.pack(fill="x", pady=(0, 10))

        ttk.Label(busca, text="Número do pedido:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.entry_pedido = ttk.Entry(busca, width=24)
        self.entry_pedido.grid(row=0, column=1, sticky="w")
        self.entry_pedido.bind("<Return>", lambda _e: self.buscar())
        ttk.Button(busca, text="Buscar", command=self.buscar).grid(row=0, column=2, padx=(6, 0))

        info = ttk.LabelFrame(self, text="Dados do pedido", padding=10)
        info.pack(fill="x", pady=(0, 10))

        self.label_funcionario = ttk.Label(info, text="Funcionário: -")
        self.label_funcionario.grid(row=0, column=0, sticky="w", padx=(0, 20))
        self.label_setor = ttk.Label(info, text="Setor: -")
        self.label_setor.grid(row=0, column=1, sticky="w", padx=(0, 20))
        self.label_data_pedido = ttk.Label(info, text="Data do pedido: -")
        self.label_data_pedido.grid(row=0, column=2, sticky="w")

        colunas = ("produto", "tipo", "tamanho", "quantidade")
        self.tree_itens = ttk.Treeview(info, columns=colunas, show="headings", height=6)
        for col, texto, largura in [
            ("produto", "Produto", 220), ("tipo", "Tipo/Categoria", 130),
            ("tamanho", "Tamanho", 80), ("quantidade", "Quantidade", 90),
        ]:
            self.tree_itens.heading(col, text=texto)
            self.tree_itens.column(col, width=largura, anchor="center" if col in ("tamanho", "quantidade") else "w")
        self.tree_itens.grid(row=1, column=0, columnspan=3, sticky="we", pady=(8, 0))

        gerar = ttk.LabelFrame(self, text="Gerar Documento", padding=10)
        gerar.pack(fill="x")

        ttk.Label(gerar, text="Modelo do termo:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.combo_modelo = ttk.Combobox(gerar, state="readonly", width=38)
        self.combo_modelo.grid(row=0, column=1, sticky="w")
        self.combo_modelo.bind("<<ComboboxSelected>>", lambda _e: self._modelo_selecionado())
        ttk.Button(gerar, text="Atualizar", command=self.atualizar_modelos).grid(row=0, column=2, padx=(6, 0))

        ttk.Label(gerar, text="Data do documento (dd/mm/aaaa):").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(8, 0))
        self.entry_data = ttk.Entry(gerar, width=15)
        self.entry_data.grid(row=1, column=1, sticky="w", pady=(8, 0))
        self.entry_data.insert(0, date.today().strftime("%d/%m/%Y"))

        self.label_modelo_info = ttk.Label(gerar, text="", foreground="#666")
        self.label_modelo_info.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))

        self.botao_gerar = ttk.Button(gerar, text="Gerar PDF...", command=self.gerar_pdf, state="disabled")
        self.botao_gerar.grid(row=1, column=2, padx=(12, 0), pady=(8, 0))

        self.botao_visualizar = ttk.Button(gerar, text="Visualizar", command=self.visualizar_pdf, state="disabled")
        self.botao_visualizar.grid(row=1, column=3, padx=(6, 0), pady=(8, 0))

        ttk.Label(
            self,
            text="Dica: o modelo padrão já vem selecionado. Você pode trocar o modelo antes de gerar o PDF.",
            foreground="#666",
        ).pack(anchor="w", pady=(10, 0))

    def _carregar_modelos(self, modelo_id=None):
        self.cfg = carregar_configuracoes()
        self.modelos = modelos_ativos(self.cfg)
        nomes = [m.get("nome", "Modelo") for m in self.modelos]
        self.combo_modelo["values"] = nomes
        if not self.modelos:
            self.label_modelo_info.configure(text="Nenhum modelo ativo. Cadastre um em Configurações → Termos de Responsabilidade.")
            return
        alvo = modelo_id or self.cfg.get("modelo_padrao_id") or self.modelos[0].get("id")
        indice = next((i for i, m in enumerate(self.modelos) if m.get("id") == alvo), 0)
        self.combo_modelo.current(indice)
        self._modelo_selecionado()

    def atualizar_modelos(self):
        """Recarrega os modelos salvos em Configurações sem perder o pedido atual."""
        indice = self.combo_modelo.current()
        modelo_id = None
        if 0 <= indice < len(self.modelos):
            modelo_id = self.modelos[indice].get("id")
        self._carregar_modelos(modelo_id=modelo_id)
        if self.modelos:
            self.label_modelo_info.configure(
                text=f"Modelo atualizado: {self.modelos[self.combo_modelo.current()].get('nome', 'Modelo')}"
            )

    def _modelo_selecionado(self):
        indice = self.combo_modelo.current()
        if 0 <= indice < len(self.modelos):
            modelo = self.modelos[indice]
            self.label_modelo_info.configure(text=f"Título: {modelo.get('titulo', 'TERMO DE RESPONSABILIDADE')}")

    def _extrair_numero_pedido(self, texto: str):
        texto = texto.strip()
        if not texto:
            return None
        primeira_parte = texto.split(" - ")[0].split()[0]
        try:
            return int(primeira_parte)
        except ValueError:
            return None

    def buscar(self):
        numero = self._extrair_numero_pedido(self.entry_pedido.get())
        if numero is None:
            messagebox.showwarning("Número inválido", "Digite um número de pedido válido.")
            return

        pedido = buscar_pedido_saida(numero)
        if pedido is None:
            messagebox.showerror("Não encontrado", f"Nenhum pedido de saída com número {numero}.")
            self.pedido_atual = None
            self.botao_gerar.configure(state="disabled")
            self.botao_visualizar.configure(state="disabled")
            return

        self.pedido_atual = pedido
        self.label_funcionario.configure(text=f"Funcionário: {pedido.funcionario.nome}")
        self.label_setor.configure(text=f"Setor: {pedido.setor_loja.nome}")
        self.label_data_pedido.configure(text=f"Data do pedido: {pedido.data_saida}")

        for linha in self.tree_itens.get_children():
            self.tree_itens.delete(linha)
        for item in pedido.itens:
            tipo = item.produto.categoria.nome if item.produto and item.produto.categoria else "-"
            self.tree_itens.insert("", "end", values=(
                item.produto.nome if item.produto else "-", tipo,
                item.tamanho.nome if item.tamanho else "-", item.quantidade,
            ))

        if pedido.data_saida:
            self.entry_data.delete(0, tk.END)
            self.entry_data.insert(0, pedido.data_saida.strftime("%d/%m/%Y"))

        estado = "normal" if pedido.itens and self.modelos else "disabled"
        self.botao_gerar.configure(state=estado)
        self.botao_visualizar.configure(state=estado)
        if not pedido.itens:
            messagebox.showwarning("Pedido sem itens", "Esse pedido não tem itens lançados, não há o que gerar no termo.")
        elif not self.modelos:
            messagebox.showwarning("Modelo não configurado", "Cadastre pelo menos um modelo em Configurações → Termos de Responsabilidade.")

    def _ler_data_documento(self):
        return ler_data_campo(self.entry_data)

    def abrir_pedido(self, numero):
        self.entry_pedido.delete(0, tk.END)
        self.entry_pedido.insert(0, str(numero))
        self.buscar()
        if self.pedido_atual is not None:
            self.botao_visualizar.focus_set()

    def _modelo_id(self):
        indice = self.combo_modelo.current()
        if 0 <= indice < len(self.modelos):
            return self.modelos[indice].get("id")
        return None

    def gerar_pdf(self):
        if not tem_permissao("gerar_termo"):
            messagebox.showerror("Sem permissão", "Você não tem permissão para gerar termos."); return
        if self.pedido_atual is None:
            messagebox.showwarning("Nenhum pedido", "Busque um pedido antes de gerar o PDF."); return
        modelo_id = self._modelo_id()
        if not modelo_id:
            messagebox.showwarning("Modelo", "Selecione um modelo de termo."); return
        data_documento = self._ler_data_documento()
        if data_documento is None: return
        nome_sugerido = f"termo_responsabilidade_pedido_{self.pedido_atual.id_pedido_saida}.pdf"
        caminho = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Documento PDF", "*.pdf")], initialfile=nome_sugerido)
        if not caminho: return
        try:
            gerar_termo_responsabilidade_pdf(self.pedido_atual.id_pedido_saida, data_documento, caminho, modelo_id=modelo_id)
        except ValueError as e:
            messagebox.showerror("Erro", str(e)); return
        except Exception as e:
            messagebox.showerror("Erro ao gerar PDF", str(e)); return
        messagebox.showinfo("Sucesso", f"Termo gerado em:\n{caminho}")
        if os.name == "nt":
            try: os.startfile(caminho)
            except Exception: pass

    def visualizar_pdf(self):
        if self.pedido_atual is None:
            messagebox.showwarning("Nenhum pedido", "Busque um pedido antes de visualizar."); return
        modelo_id = self._modelo_id()
        if not modelo_id:
            messagebox.showwarning("Modelo", "Selecione um modelo de termo."); return
        data_documento = self._ler_data_documento()
        if data_documento is None: return
        pasta_temp = tempfile.gettempdir()
        caminho = os.path.join(pasta_temp, f"termo_visualizacao_pedido_{self.pedido_atual.id_pedido_saida}.pdf")
        try:
            gerar_termo_responsabilidade_pdf(self.pedido_atual.id_pedido_saida, data_documento, caminho, modelo_id=modelo_id)
        except ValueError as e:
            messagebox.showerror("Erro", str(e)); return
        except Exception as e:
            messagebox.showerror("Erro ao gerar PDF", str(e)); return
        if os.name == "nt":
            try:
                os.startfile(caminho)
            except Exception as e:
                messagebox.showerror("Erro ao abrir", f"O PDF foi gerado em {caminho}, mas não consegui abrir automaticamente: {e}")
        else:
            messagebox.showinfo("Gerado", f"PDF de visualização salvo temporariamente em:\n{caminho}")
