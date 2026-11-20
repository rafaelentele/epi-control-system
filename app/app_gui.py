"""Interface gráfica principal.

Navegação 100% por menus suspensos, agrupados pelo fluxo de trabalho
(compra -> entrada -> saída -> termo). As abas nativas ficam ocultas.

Para mexer na navegação, edite apenas os dois blocos abaixo:
  * TELAS  - cada tela do sistema (rótulo, onde ela está, quem pode abrir, atalho)
  * MENUS  - a barra principal, em ordem. Uma lista de telas vira um menu suspenso;
             uma única tela (texto) vira um botão direto
"""
import tkinter as tk
import tkinter.font as tkfont
import traceback
from dataclasses import dataclass
from typing import Optional, Tuple

from tkinter import ttk, messagebox
from app.branding import asset_path
from app.repositories.relatorios import estoque_pivot
from app.auth import abrir_login, garantir_estrutura_autenticacao, tem_permissao, obter_usuario_atual
from gui.ajuda_dialog import abrir_manual
from gui.sobre_dialog import abrir_sobre
from gui.cadastro_frame import CadastroConfiguracaoFrame
from gui.pedido_compra_frame import PedidoCompraFrame
from gui.movimentacao_frame import MovimentacaoFrame
from gui.relatorios_frame import RelatoriosFrame
from gui.termo_frame import TermoResponsabilidadeFrame
from gui.configuracao_frame import ConfiguracaoFrame
from gui.utils import criar_notebook_sem_abas

# Mostra botões de acesso rápido na tela Início. Troque para False para
# deixar o Início só com a logo.
MOSTRAR_ATALHOS_NO_INICIO = True

# Mostra no Início o aviso de produtos com estoque baixo/zerado (clicável).
MOSTRAR_ALERTAS_NO_INICIO = True

SEPARADOR = "-"


@dataclass(frozen=True)
class Tela:
    chave: str                    # identificador único
    grupo: str                    # menu "principal" da tela (usado no destaque)
    rotulo: str                   # texto no menu e no título
    pagina: str                   # página do notebook onde ela vive
    sub: Optional[str] = None     # sub-tela dentro da página (se houver)
    perms: Tuple[str, ...] = ()   # basta UMA destas permissões para abrir
    atalho: Optional[str] = None  # tecla de atalho (ex.: "F4")


PERM_PRODUTOS = ("cadastrar_produtos", "consultar_produtos", "editar_produtos", "excluir_produtos")
PERM_FORNECEDORES = ("cadastrar_fornecedores", "consultar_fornecedores", "editar_fornecedores", "excluir_fornecedores")
PERM_FUNCIONARIOS = ("cadastrar_funcionarios", "consultar_funcionarios", "editar_funcionarios", "excluir_funcionarios")
PERM_REL = ("acessar_relatorios",)
PERM_ADMIN = ("gerenciar_usuarios",)

TELAS = [
    # Estoque (botão direto)
    Tela("status", "Estoque", "Status do Estoque", "relatorios", "status", PERM_REL, "F2"),
    # Compras (botão direto)
    Tela("pedidos", "Compras", "Pedidos de Compra", "pedidos", None, ("consultar_pedidos",), "F3"),
    # Movimentação
    Tela("saida", "Movimentação", "Pedido de Saída", "movimentacao", "saida", ("dar_baixa",), "F6"),
    Tela("entrada", "Movimentação", "Entrada de Estoque", "movimentacao", "entrada", ("dar_entrada",), "F4"),
    Tela("ajuste", "Movimentação", "Ajuste de Estoque", "movimentacao", "ajuste", ("ajustar_estoque",)),
    # Termo de Responsabilidade (botão direto)
    Tela("termo", "Termo de Responsabilidade", "Termo de Responsabilidade", "termo", None, ("gerar_termo",), "F7"),
    # Cadastros
    Tela("produtos", "Cadastros", "Produtos", "cadastro", "produtos", PERM_PRODUTOS),
    Tela("empresas", "Cadastros", "Empresas", "cadastro", "empresas", ("gerenciar_empresas",)),
    Tela("categorias", "Cadastros", "Categorias", "cadastro", "categorias", PERM_PRODUTOS),
    Tela("fornecedores", "Cadastros", "Fornecedores", "cadastro", "fornecedores", PERM_PRODUTOS + PERM_FORNECEDORES),
    Tela("tamanhos", "Cadastros", "Tamanhos", "cadastro", "tamanhos", PERM_PRODUTOS),
    Tela("funcionarios", "Cadastros", "Funcionários", "cadastro", "funcionarios", PERM_PRODUTOS + PERM_FUNCIONARIOS),
    Tela("setores", "Cadastros", "Setores/Lojas", "cadastro", "setores", PERM_PRODUTOS),
    # Relatórios (o Status do Estoque também aparece aqui, é a mesma tela)
    Tela("rel_entradas", "Relatórios", "Entradas por Tamanho", "relatorios", "entradas", PERM_REL),
    Tela("rel_hist_func", "Relatórios", "Histórico por Funcionário", "relatorios", "hist_func", PERM_REL),
    Tela("rel_hist_prod", "Relatórios", "Histórico por Produto", "relatorios", "hist_prod", PERM_REL),
    Tela("rel_pesquisa", "Relatórios", "Pesquisa de Registro de Compra", "relatorios", "pesquisa_compra", PERM_REL),
    Tela("rel_listagem", "Relatórios", "Listagem Geral", "relatorios", "listagem", PERM_REL),
    Tela("rel_historico", "Relatórios", "Histórico de Operações", "relatorios", "hist_operacoes", PERM_REL),
    # Configuração
    Tela("cfg_usuarios", "Configuração", "Usuários e Permissões", "configuracao", "usuarios", PERM_ADMIN),
    Tela("cfg_sistema", "Configuração", "Termo, Backup e Importação", "configuracao", "sistema", PERM_ADMIN),
]

MENUS = [
    ("Estoque", "status"),                                   # botão direto
    ("Compras", "pedidos"),                                  # botão direto
    ("Movimentação", ["saida", "entrada", "ajuste"]),
    ("Cadastros", ["produtos", SEPARADOR, "empresas", "categorias", "fornecedores", "tamanhos", "funcionarios", "setores"]),
    ("Relatórios", ["status", SEPARADOR, "rel_entradas", "rel_hist_func", "rel_hist_prod", "rel_pesquisa", "rel_listagem", "rel_historico"]),
    ("Termo de Responsabilidade", "termo"),                  # botão direto
    ("Configuração", ["cfg_usuarios", "cfg_sistema"]),
]

# Botões de acesso rápido do Início: (tela, texto do botão)
ATALHOS_INICIO = [
    ("saida", "Nova Saída"),
    ("entrada", "Nova Entrada"),
    ("termo", "Gerar Termo"),
    ("status", "Status do Estoque"),
]

TITULO_BASE = "Epi Control"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        usuario = obter_usuario_atual() or {}
        self.titulo_base = f"{TITULO_BASE} - {usuario.get('nome', '')}"
        self.title(self.titulo_base)
        try:
            self.iconbitmap(str(asset_path("icone_sistema.ico")))
        except Exception:
            pass
        self.geometry("1100x760")
        self.minsize(900, 650)

        self.telas = {t.chave: t for t in TELAS}
        self.paginas = {}
        self.botoes_menu = {}          # nome do menu -> botão (para destacar o ativo)
        self.tela_atual = None
        self._aviso_job = None

        self._configurar_estilos()

        # --- Barra de menus suspensos + indicador da tela atual ---------------
        self.barra_navegacao = ttk.Frame(self, padding=(8, 8, 8, 2))
        self.barra_navegacao.pack(side="top", fill="x")

        cabecalho = ttk.Frame(self, padding=(10, 2, 10, 0))
        cabecalho.pack(side="top", fill="x")
        self.lbl_tela = ttk.Label(cabecalho, text="Início", font=self._fonte_titulo)
        self.lbl_tela.pack(side="left")
        ttk.Label(cabecalho, text="F5 = atualizar a tela", foreground="gray45").pack(side="right")
        ttk.Separator(self, orient="horizontal").pack(side="top", fill="x", padx=8, pady=(4, 0))

        barra_inferior = ttk.Frame(self)
        barra_inferior.pack(side="bottom", fill="x", padx=8, pady=(0, 8))

        # --- Páginas (abas nativas ocultas) -----------------------------------
        self.notebook = criar_notebook_sem_abas(self, "MenuPrincipal.TNotebook")
        self.notebook.pack(side="top", fill="both", expand=True, padx=8, pady=(4, 4))

        inicio = tk.Frame(self.notebook, bg="white")
        self._adicionar_pagina("inicio", inicio, "Início")
        self._montar_inicio(inicio)

        # Uma única instância dos relatórios (inclui o Status do Estoque).
        self._adicionar_pagina("relatorios", RelatoriosFrame(self.notebook), "Relatórios")
        self._adicionar_pagina("cadastro", CadastroConfiguracaoFrame(self.notebook), "Cadastro")
        self._adicionar_pagina("pedidos", PedidoCompraFrame(self.notebook), "Pedidos")
        self._adicionar_pagina("movimentacao", MovimentacaoFrame(self.notebook), "Movimentação")
        self._adicionar_pagina("termo", TermoResponsabilidadeFrame(self.notebook), "Termo de Responsabilidade")
        self._adicionar_pagina("configuracao", ConfiguracaoFrame(self.notebook), "Configuração")

        # --- Rodapé -----------------------------------------------------------
        ttk.Label(
            barra_inferior,
            text=f"Usuário conectado: {usuario.get('nome', '')} ({usuario.get('nivel_acesso', '')})"
        ).pack(side="left")
        self.lbl_aviso = ttk.Label(barra_inferior, text="", foreground="firebrick")
        self.lbl_aviso.pack(side="left", padx=20)
        # A barra inferior contém somente o usuário conectado, avisos e Sair.
        ttk.Button(barra_inferior, text="Sair", command=self._sair).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self._sair)

        self._criar_menus()
        self._criar_atalhos()
        # A janela nunca fica mais estreita que a barra de menus (botões não ficam cortados).
        self.update_idletasks()
        largura_min = max(900, self.barra_navegacao.winfo_reqwidth() + 30)
        self.minsize(largura_min, 650)
        self.geometry(f"{max(1100, largura_min)}x760")
        self.abrir_inicio()

    # ------------------------------------------------------------------
    # Montagem
    # ------------------------------------------------------------------
    def _configurar_estilos(self):
        estilo = ttk.Style(self)
        fonte_padrao = tkfont.nametofont("TkDefaultFont")
        self._fonte_negrito = fonte_padrao.copy()
        self._fonte_negrito.configure(weight="bold")
        self._fonte_titulo = fonte_padrao.copy()
        self._fonte_titulo.configure(weight="bold", size=fonte_padrao.cget("size") + 2)
        # Menu da tela atual fica em negrito.
        estilo.configure("MenuAtivo.TMenubutton", font=self._fonte_negrito)
        estilo.configure("InicioAtivo.TButton", font=self._fonte_negrito)
        estilo.configure("Atalho.TButton", anchor="center", justify="center")

    def _adicionar_pagina(self, chave, widget, texto):
        self.notebook.add(widget, text=texto)
        self.paginas[chave] = widget

    def _montar_inicio(self, inicio):
        centro = tk.Frame(inicio, bg="white")
        centro.place(relx=0.5, rely=0.45, anchor="center")
        try:
            self._logo_inicio = tk.PhotoImage(file=str(asset_path("logo_inicio.png")))
            tk.Label(centro, image=self._logo_inicio, bg="white", borderwidth=0).pack()
        except Exception:
            pass
        self._frame_atalhos_inicio = tk.Frame(centro, bg="white")
        self._frame_atalhos_inicio.pack(pady=(28, 0))
        self.lbl_alerta = tk.Label(centro, text="", bg="white", font=self._fonte_negrito)
        self.lbl_alerta.pack(pady=(26, 0))
        self.lbl_alerta.bind("<Button-1>", lambda e: self._clique_alerta())

    def _preencher_atalhos_inicio(self):
        if not MOSTRAR_ATALHOS_NO_INICIO:
            return
        coluna = 0
        for chave, texto in ATALHOS_INICIO:
            tela = self.telas[chave]
            if not self._permitida(tela):
                continue
            rotulo = texto + (f"\n({tela.atalho})" if tela.atalho else "")
            ttk.Button(
                self._frame_atalhos_inicio, text=rotulo, width=18, padding=(6, 10), style="Atalho.TButton",
                command=lambda c=chave: self.abrir(c),
            ).grid(row=0, column=coluna, padx=8)
            coluna += 1

    def _criar_menus(self):
        botao_inicio = ttk.Button(self.barra_navegacao, text="Início", command=self.abrir_inicio)
        botao_inicio.pack(side="left", padx=(0, 5))
        self.botoes_menu["Início"] = botao_inicio

        for nome, chaves in MENUS:
            if isinstance(chaves, str):  # tela única: botão direto, sem menu suspenso
                tela = self.telas[chaves]
                if not self._permitida(tela):
                    continue
                botao = ttk.Button(self.barra_navegacao, text=nome,
                                   command=lambda c=chaves, g=nome: self.abrir(c, g))
                botao.pack(side="left", padx=(0, 5))
                self.botoes_menu[nome] = botao
                continue
            telas_menu = [self.telas[c] for c in chaves if c != SEPARADOR]
            # Menu sem nenhuma tela liberada para o usuário não aparece.
            if not any(self._permitida(t) for t in telas_menu):
                continue
            botao = ttk.Menubutton(self.barra_navegacao, text=nome, direction="below")
            menu = tk.Menu(botao, tearoff=False)
            botao.configure(menu=menu)
            indices = {}
            for posicao, chave in enumerate(chaves):
                if chave == SEPARADOR:
                    menu.add_separator()
                    continue
                tela = self.telas[chave]
                menu.add_command(
                    label=tela.rotulo,
                    accelerator=tela.atalho or "",
                    command=lambda c=chave, g=nome: self.abrir(c, g),
                )
                indices[posicao] = tela
            # Reavalia as permissões toda vez que o menu é aberto: itens sem
            # permissão ficam em cinza em vez de clicáveis e sem efeito.
            menu.configure(postcommand=lambda m=menu, i=indices: self._atualizar_estado_menu(m, i))
            self._atualizar_estado_menu(menu, indices)
            botao.pack(side="left", padx=(0, 5))
            self.botoes_menu[nome] = botao

        botao_ajuda = ttk.Menubutton(self.barra_navegacao, text="Ajuda", direction="below")
        menu_ajuda = tk.Menu(botao_ajuda, tearoff=False)
        menu_ajuda.add_command(label="Manual de instruções", command=lambda: abrir_manual(self))
        menu_ajuda.add_command(label="Sobre o Epi Control", command=lambda: abrir_sobre(self))
        botao_ajuda.configure(menu=menu_ajuda)
        botao_ajuda.pack(side="left", padx=(0, 5))
        self.botoes_menu["Ajuda"] = botao_ajuda

        self._preencher_atalhos_inicio()

    def _atualizar_estado_menu(self, menu, indices):
        for posicao, tela in indices.items():
            menu.entryconfigure(posicao, state="normal" if self._permitida(tela) else "disabled")

    def _criar_atalhos(self):
        for tela in TELAS:
            if tela.atalho:
                self.bind_all(f"<{tela.atalho}>", lambda e, c=tela.chave: self._atalho(e, c))
        self.bind_all("<F5>", lambda e: self._atalho(e, None))

    def _atalho(self, evento, chave):
        # Só vale na janela principal (não dispara por trás de uma janela modal).
        try:
            if evento.widget.winfo_toplevel() is not self:
                return
        except Exception:
            return
        if chave is None:
            self.atualizar_tela_atual()
        else:
            self.abrir(chave)

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------
    @staticmethod
    def _permitida(tela):
        return any(tem_permissao(p) for p in tela.perms)

    def abrir_inicio(self):
        self.notebook.select(self.paginas["inicio"])
        self.tela_atual = None
        self._destacar("Início")
        self._mostrar_local("Início")
        self._atualizar_alertas()

    def abrir(self, chave, grupo=None):
        """Abre uma tela pelo nome. `grupo` é o menu de onde veio o clique."""
        tela = self.telas[chave]
        if not self._permitida(tela):
            self._avisar(f"Seu usuário não tem permissão para abrir “{tela.rotulo}”.")
            return
        pagina = self.paginas[tela.pagina]
        try:
            self.notebook.select(pagina)
            alvo = pagina.abrir_subtela(tela.sub) if tela.sub else pagina
        except (tk.TclError, AttributeError):
            traceback.print_exc()
            self._avisar(f"Não foi possível abrir “{tela.rotulo}”.")
            return
        self.tela_atual = chave
        grupo = grupo or tela.grupo
        self._destacar(grupo)
        self._mostrar_local(tela.rotulo if grupo == tela.rotulo else f"{grupo}  ›  {tela.rotulo}")
        self._atualizar_widget(tela, pagina, alvo)

    def atualizar_tela_atual(self):
        if self.tela_atual is None:
            self._atualizar_alertas()
            self._avisar("Tela atualizada.", erro=False)
            return
        tela = self.telas[self.tela_atual]
        pagina = self.paginas[tela.pagina]
        alvo = pagina.subtelas.get(tela.sub) if tela.sub else pagina
        self._atualizar_widget(tela, pagina, alvo)
        self._avisar("Tela atualizada.", erro=False)

    def _atualizar_widget(self, tela, pagina, alvo):
        """Recarrega do banco os dados da tela aberta (combos, listas, status)."""
        try:
            if tela.pagina == "relatorios":
                pagina.atualizar_dados(tela.sub)
                return
            for nome in ("atualizar_dados", "atualizar_lista"):
                funcao = getattr(alvo, nome, None)
                if callable(funcao):
                    funcao()
                    return
        except Exception:
            # Falha de atualização (ex.: sem internet) não pode impedir a navegação.
            traceback.print_exc()
            self._avisar("Não foi possível atualizar os dados desta tela.")

    def abrir_termo_do_pedido(self, numero):
        """Abre o Termo de Responsabilidade já com o pedido carregado (chamado pela tela de Saída)."""
        self.abrir("termo")
        if self.tela_atual == "termo":
            self.paginas["termo"].abrir_pedido(numero)

    # --- alertas de estoque no Início -----------------------------------
    def _atualizar_alertas(self):
        """Mostra no Início quantos produtos estão zerados / com estoque baixo
        (mesma regra da tela Status do Estoque)."""
        self._alerta_clicavel = False
        if not MOSTRAR_ALERTAS_NO_INICIO or not self._permitida(self.telas["status"]):
            self.lbl_alerta.configure(text="")
            return
        try:
            _, linhas = estoque_pivot()
        except Exception:
            traceback.print_exc()
            self.lbl_alerta.configure(text="")
            return
        zerados = sum(1 for l in linhas if l["status"] == "ZERADO")
        baixos = sum(1 for l in linhas if l["status"] == "ESTOQUE BAIXO")
        if zerados + baixos == 0:
            self.lbl_alerta.configure(text="✔  Nenhum produto abaixo do estoque mínimo", fg="#2e7d32", cursor="")
            return
        partes = []
        if baixos:
            partes.append(f"{baixos} com estoque baixo")
        if zerados:
            partes.append(f"{zerados} zerado" + ("s" if zerados > 1 else ""))
        total = zerados + baixos
        texto = f"⚠  {total} produto" + ("s" if total > 1 else "") + ": " + " e ".join(partes) + "  (clique para ver)"
        self._alerta_clicavel = True
        self.lbl_alerta.configure(text=texto, fg="#b45309", cursor="hand2")

    def _clique_alerta(self):
        if getattr(self, "_alerta_clicavel", False):
            self.abrir("status")

    def _destacar(self, nome_ativo):
        for nome, botao in self.botoes_menu.items():
            ativo = nome == nome_ativo
            if isinstance(botao, ttk.Menubutton):
                botao.configure(style="MenuAtivo.TMenubutton" if ativo else "TMenubutton")
            else:
                botao.configure(style="InicioAtivo.TButton" if ativo else "TButton")

    def _mostrar_local(self, texto):
        self.lbl_tela.configure(text=texto)
        self.title(self.titulo_base if texto == "Início" else f"{self.titulo_base}  |  {texto}")

    def _avisar(self, texto, erro=True):
        self.lbl_aviso.configure(text=texto, foreground="firebrick" if erro else "gray30")
        if self._aviso_job is not None:
            self.after_cancel(self._aviso_job)
        self._aviso_job = self.after(4000, lambda: self.lbl_aviso.configure(text=""))

    def _sair(self):
        self.destroy()


def main():
    try:
        garantir_estrutura_autenticacao()
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Erro ao iniciar",
            "Não foi possível preparar o login/banco de dados.\n\n" + str(exc),
            parent=root,
        )
        root.destroy()
        return

    usuario = abrir_login()
    if usuario is None:
        return

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
