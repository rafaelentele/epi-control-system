"""Agrupa os cadastros básicos acessíveis pelo menu Cadastros.

As sub-telas não mostram abas: a escolha é feita pelo menu suspenso
(ver app_gui.py). Cada sub-tela tem uma chave estável usada pelo menu.
"""
from tkinter import ttk
from app.repositories.crud_simple import (
    criar_categoria, listar_categorias, atualizar_categoria, excluir_categoria,
    criar_fornecedor, listar_fornecedores, atualizar_fornecedor, excluir_fornecedor,
    criar_funcionario, listar_funcionarios, atualizar_funcionario, excluir_funcionario,
    criar_setor_loja, listar_setores_loja, atualizar_setor_loja, excluir_setor_loja,
    criar_tamanho, listar_tamanhos, atualizar_tamanho, excluir_tamanho,
)
from gui.entidade_simples_frame import EntidadeSimplesFrame
from gui.produtos_frame import ProdutosFrame
from gui.empresa_frame import EmpresaFrame
from gui.utils import criar_notebook_sem_abas, SubtelasMixin


class CadastroConfiguracaoFrame(SubtelasMixin, ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.sub_notebook = criar_notebook_sem_abas(self)
        self.sub_notebook.pack(fill="both", expand=True)
        self._iniciar_subtelas()
        nb = self.sub_notebook
        self._adicionar_subtela("empresas", EmpresaFrame(nb), "Empresas")
        self._adicionar_subtela("categorias", EntidadeSimplesFrame(nb, "Categorias", criar_categoria, listar_categorias, atualizar_categoria, excluir_categoria, permissao_cadastro="cadastrar_produtos", permissao_edicao="editar_produtos", permissao_exclusao="excluir_produtos"), "Categorias")
        self._adicionar_subtela("fornecedores", EntidadeSimplesFrame(nb, "Fornecedores", criar_fornecedor, listar_fornecedores, atualizar_fornecedor, excluir_fornecedor, tem_contato=True, permissao_consulta="consultar_fornecedores", permissao_cadastro="cadastrar_fornecedores", permissao_edicao="editar_fornecedores", permissao_exclusao="excluir_fornecedores"), "Fornecedores")
        self._adicionar_subtela("tamanhos", EntidadeSimplesFrame(nb, "Tamanhos", criar_tamanho, listar_tamanhos, atualizar_tamanho, excluir_tamanho), "Tamanhos")
        self._adicionar_subtela("funcionarios", EntidadeSimplesFrame(nb, "Funcionários", criar_funcionario, listar_funcionarios, atualizar_funcionario, excluir_funcionario, tem_empresa=True, tem_cpf=True, permissao_consulta="consultar_funcionarios", permissao_cadastro="cadastrar_funcionarios", permissao_edicao="editar_funcionarios", permissao_exclusao="excluir_funcionarios"), "Funcionários")
        self._adicionar_subtela("setores", EntidadeSimplesFrame(nb, "Setores/Lojas", criar_setor_loja, listar_setores_loja, atualizar_setor_loja, excluir_setor_loja), "Setores/Lojas")
        self._adicionar_subtela("produtos", ProdutosFrame(nb), "Produtos")

    def configurar_permissoes(self):
        """As permissões dos cadastros são aplicadas por cada tela."""
        return None
