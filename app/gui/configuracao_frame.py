"""Configuração: usuários/permissões e configurações do sistema (sem abas visíveis)."""
from tkinter import ttk
from gui.usuarios_frame import UsuariosFrame
from gui.configuracoes_sistema_frame import ConfiguracoesSistemaFrame
from gui.utils import criar_notebook_sem_abas, SubtelasMixin


class ConfiguracaoFrame(SubtelasMixin, ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.sub_notebook = criar_notebook_sem_abas(self)
        self.sub_notebook.pack(fill="both", expand=True)
        self._iniciar_subtelas()
        nb = self.sub_notebook
        self._adicionar_subtela("usuarios", UsuariosFrame(nb), "Usuários e Permissões")
        self._adicionar_subtela("sistema", ConfiguracoesSistemaFrame(nb), "Termo, Backup e Importação")
