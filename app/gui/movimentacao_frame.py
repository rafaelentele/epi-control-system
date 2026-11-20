"""Agrupa as operações de movimentação de estoque (sem abas visíveis)."""
from tkinter import ttk
from gui.entrada_frame import EntradaFrame
from gui.saida_frame import SaidaFrame
from gui.ajuste_estoque_frame import AjusteEstoqueFrame
from gui.utils import criar_notebook_sem_abas, SubtelasMixin


class MovimentacaoFrame(SubtelasMixin, ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.sub_notebook = criar_notebook_sem_abas(self)
        self.sub_notebook.pack(fill="both", expand=True)
        self._iniciar_subtelas()
        nb = self.sub_notebook
        self.entrada = self._adicionar_subtela("entrada", EntradaFrame(nb), "Entrada")
        self.saida = self._adicionar_subtela("saida", SaidaFrame(nb), "Saída")
        self.ajuste = self._adicionar_subtela("ajuste", AjusteEstoqueFrame(nb), "Ajuste de Estoque")
