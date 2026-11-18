import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import html
import tempfile
import webbrowser

from app.repositories.relatorios import (
    estoque_entradas_por_tamanho,
    historico_funcionario, historico_produto, listagem_geral, formatar_listagem_geral,
    estoque_pivot, historico_operacoes,
)
from app.repositories.crud_simple import listar_funcionarios, listar_fornecedores
from app.repositories.crud_produtos import listar_produtos
from app.repositories.crud_pedido_compra import pesquisar_pedidos_compra
from gui.utils import formatar_opcao, extrair_id, criar_notebook_sem_abas, SubtelasMixin, ComboBusca, TreeviewBusca, BarraPesquisa, adicionar_pesquisa
from app.auth import tem_permissao


def _criar_tabela(parent, colunas_com_titulo, altura=15):
    """Cria um Treeview simples a partir de uma lista [(chave, título, largura), ...]."""
    colunas = [c[0] for c in colunas_com_titulo]
    tree = TreeviewBusca(parent, columns=colunas, show="headings", height=altura)
    for chave, titulo, largura in colunas_com_titulo:
        tree.heading(chave, text=titulo)
        tree.column(chave, width=largura, anchor="center" if chave in ("saldo", "entrou", "saiu", "quantidade") else "w")
    tree.pack(fill="both", expand=True, pady=(0, 0))
    adicionar_pesquisa(tree)
    return tree


class RelatoriosFrame(SubtelasMixin, ttk.Frame):
    """Relatórios. As sub-telas não têm abas visíveis: o menu Relatórios (app_gui.py)
    abre cada uma pela chave (status, entradas, hist_func, hist_prod, pesquisa_compra,
    listagem, hist_operacoes)."""

    def __init__(self, parent, status_only=False):
        super().__init__(parent, padding=10)
        self._iniciar_subtelas()
        self._status_container = None
        self._combo_func = None
        self._combo_prod = None
        if not tem_permissao("acessar_relatorios"):
            ttk.Label(self, text="Seu usuário não possui permissão para acessar os relatórios.", font=("TkDefaultFont", 12, "bold")).pack(pady=40)
            return
        self.sub_notebook = criar_notebook_sem_abas(self)
        self.sub_notebook.pack(fill="both", expand=True)
        sub_notebook = self.sub_notebook

        self._adicionar_subtela("status", self._aba_status_estoque(sub_notebook), "Status do Estoque")
        if not status_only:
            self._adicionar_subtela("entradas", self._aba_entradas_por_tamanho(sub_notebook), "Entradas por Tamanho")
            self._adicionar_subtela("hist_func", self._aba_historico_funcionario(sub_notebook), "Histórico por Funcionário")
            self._adicionar_subtela("hist_prod", self._aba_historico_produto(sub_notebook), "Histórico por Produto")
            self._adicionar_subtela("pesquisa_compra", self._aba_pesquisa_compra(sub_notebook), "Pesquisa de Registro de Compra")
            self._adicionar_subtela("listagem", self._aba_listagem_geral(sub_notebook), "Listagem Geral")
            self._adicionar_subtela("hist_operacoes", self._aba_historico_operacoes(sub_notebook), "Histórico de Operações")

    def atualizar_dados(self, chave=None):
        """Recarrega só o que muda com o uso, conforme o relatório aberto
        (chave=None atualiza tudo)."""
        if self._status_container is not None and chave in (None, "status"):
            self._carregar_status_estoque(self._status_container)
        if self._combo_func is not None and chave in (None, "hist_func"):
            self._combo_func["values"] = [formatar_opcao(f.id_funcionario, f.nome) for f in listar_funcionarios()]
        if self._combo_prod is not None and chave in (None, "hist_prod"):
            self._combo_prod["values"] = [formatar_opcao(p.id_produto, p.nome) for p in listar_produtos()]

    # ------------------------------------------------------------
    def _aba_status_estoque(self, parent):
        aba = ttk.Frame(parent, padding=10)
        ttk.Label(aba, text="Status do estoque — o alerta considera o TOTAL do produto, somando todos os tamanhos.").pack(anchor="w")
        botoes = ttk.Frame(aba)
        botoes.pack(fill="x", pady=(4, 8))
        ttk.Button(botoes, text="🔄 Atualizar", command=lambda: self._carregar_status_estoque(container)).pack(side="left")
        ttk.Button(botoes, text="🖨 Imprimir estoque", command=self._imprimir_status_estoque).pack(side="left", padx=(8, 0))
        self._barra_status = BarraPesquisa(botoes, None)
        self._barra_status.pack(side="left", padx=(24, 0))

        legenda = ttk.Frame(aba)
        legenda.pack(fill="x", pady=(4, 0))
        ttk.Label(legenda, text="🟨 Estoque baixo = total igual ou abaixo do mínimo cadastrado | 🟥 Zerado = total 0 ou negativo").pack(anchor="w")

        container = ttk.Frame(aba)
        container.pack(fill="both", expand=True)
        self._status_container = container
        self._carregar_status_estoque(container)
        return aba

    def _carregar_status_estoque(self, container):
        for filho in container.winfo_children():
            filho.destroy()

        nomes_tamanho, linhas = estoque_pivot()
        colunas = ["produto", "setor"] + nomes_tamanho + ["geral", "minimo", "status"]
        tree = TreeviewBusca(container, columns=colunas, show="headings", height=20)
        barra = getattr(self, "_barra_status", None)
        if barra is not None:
            barra.ligar(tree)  # mantém o texto pesquisado ao atualizar
        tree.heading("produto", text="Produto")
        tree.column("produto", width=220, anchor="w")
        tree.heading("setor", text="Setor")
        tree.column("setor", width=110, anchor="w")
        for nome in nomes_tamanho:
            tree.heading(nome, text=nome)
            tree.column(nome, width=42, anchor="center")
        tree.heading("geral", text="TOTAL")
        tree.column("geral", width=65, anchor="center")
        tree.heading("minimo", text="Mínimo")
        tree.column("minimo", width=65, anchor="center")
        tree.heading("status", text="Status")
        tree.column("status", width=120, anchor="center")

        tree.tag_configure("estoque_baixo", background="#fff3cd", foreground="#7a4b00")
        tree.tag_configure("estoque_zerado", background="#f8d7da", foreground="#842029")

        scroll_x = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        scroll_y = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="we")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        if not linhas:
            tree.insert("", "end", values=("(nenhum produto cadastrado)",))
            return

        for l in linhas:
            valores = [l["produto"], l["setor"]] + [l["saldos"][nome] for nome in nomes_tamanho]
            valores += [l["geral"], l["estoque_minimo"], l["status"]]
            tag = "estoque_zerado" if l["status"] == "ZERADO" else ("estoque_baixo" if l["status"] == "ESTOQUE BAIXO" else "")
            tree.insert("", "end", values=valores, tags=(tag,) if tag else ())

    def _imprimir_status_estoque(self):
        """Gera uma versão imprimível do status para conferência física.

        Para cada produto, imprime uma linha com o estoque do sistema e,
        logo abaixo, uma segunda linha destinada à anotação manual da
        contagem física de cada tamanho. Assim, por exemplo, a quantidade
        4 do tamanho 36 fica imediatamente acima de uma célula em branco
        onde o usuário pode escrever a quantidade encontrada.
        """
        nomes_tamanho, linhas = estoque_pivot()
        if not linhas:
            messagebox.showinfo("Estoque", "Não há produtos cadastrados para imprimir.")
            return

        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        cabecalhos = ["Produto", "Setor"] + nomes_tamanho + ["TOTAL", "Mínimo", "Status"]
        linhas_html = []

        for l in linhas:
            valores = [l["produto"], l["setor"]]
            valores += [l["saldos"][nome] for nome in nomes_tamanho]
            valores += [l["geral"], l["estoque_minimo"], l["status"]]

            classe = ""
            if l["status"] == "ZERADO":
                classe = "zerado"
            elif l["status"] == "ESTOQUE BAIXO":
                classe = "baixo"

            celulas = "".join(f"<td>{html.escape(str(v))}</td>" for v in valores)
            linhas_html.append(f"<tr class='sistema {classe}'>{celulas}</tr>")

            # Linha imediatamente abaixo: reservada para a contagem física.
            # As células dos tamanhos e do total ficam propositalmente vazias.
            qtd_vazias = len(nomes_tamanho) + 3  # tamanhos + total + mínimo + status
            fisico_cells = [
                "<td class='fisico-label'>FÍSICO</td>",
                "<td class='fisico-setor'></td>",
            ]
            fisico_cells += ["<td class='campo-anotacao'>&nbsp;</td>"] * len(nomes_tamanho)
            fisico_cells += [
                "<td class='campo-anotacao'>&nbsp;</td>",
                "<td class='campo-anotacao'>&nbsp;</td>",
                "<td class='campo-anotacao'>&nbsp;</td>",
            ]
            linhas_html.append("<tr class='linha-fisico'>" + "".join(fisico_cells) + "</tr>")

        th = "".join(f"<th>{html.escape(str(c))}</th>" for c in cabecalhos)
        corpo = "\n".join(linhas_html)
        documento = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Status do Estoque - Conferência Física</title>
<style>
@page {{ size: A4 landscape; margin: 8mm; }}
body {{ font-family: Arial, sans-serif; font-size: 8.5px; color: #111; }}
h1 {{ margin: 0 0 4px; font-size: 18px; }}
p {{ margin: 2px 0 8px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ border: 1px solid #777; padding: 3px 2px; text-align: center; }}
th {{ background: #e9ecef; font-weight: bold; }}
td:first-child, td:nth-child(2) {{ text-align: left; }}
tr.sistema.baixo td {{ background: #fff3cd; }}
tr.sistema.zerado td {{ background: #f8d7da; }}
tr.sistema td {{ height: 18px; }}
tr.linha-fisico td {{ height: 22px; }}
tr.linha-fisico .fisico-label {{ font-weight: bold; text-align: left; font-size: 7.5px; }}
tr.linha-fisico .fisico-setor {{ background: #fafafa; }}
tr.linha-fisico .campo-anotacao {{ background: #fff; height: 24px; }}
tr.sistema {{ break-after: avoid; }}
tr.linha-fisico {{ break-after: auto; }}
.footer {{ margin-top: 8px; font-size: 8px; }}
</style>
</head>
<body>
<h1>Status do Estoque — Conferência Física</h1>
<p>Gerado em: {agora} &nbsp; | &nbsp; A linha <strong>FÍSICO</strong> abaixo de cada produto é para anotar manualmente a quantidade encontrada em cada tamanho.</p>
<table>
<thead><tr>{th}</tr></thead>
<tbody>{corpo}</tbody>
</table>
<div class="footer">Após a contagem, compare a linha do sistema com a linha FÍSICO para identificar as diferenças e realizar os ajustes no sistema.</div>
</body>
</html>"""

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix="_status_estoque.html", delete=False, encoding="utf-8") as arquivo:
                arquivo.write(documento)
                caminho = arquivo.name
            webbrowser.open_new_tab(caminho)
        except Exception as exc:
            messagebox.showerror("Impressão", f"Não foi possível abrir o relatório para impressão.\n\n{exc}")

    def _aba_entradas_por_tamanho(self, parent):
        aba = ttk.Frame(parent, padding=10)
        ttk.Label(aba, text="Total que entrou por tamanho (bruto, sem descontar saída):").pack(anchor="w")
        ttk.Button(aba, text="Atualizar", command=lambda: self._carregar_entradas_tamanho(tree)).pack(anchor="w", pady=(4, 0))
        tree = _criar_tabela(aba, [
            ("produto", "Produto", 220), ("tamanho", "Tamanho", 100), ("entrou", "Total Entrada", 100),
        ])
        self._carregar_entradas_tamanho(tree)
        return aba

    def _carregar_entradas_tamanho(self, tree):
        for linha in tree.get_children():
            tree.delete(linha)
        linhas = estoque_entradas_por_tamanho()
        if not linhas:
            tree.insert("", "end", values=("(nenhuma entrada registrada ainda)", "", ""))
        for l in linhas:
            tree.insert("", "end", values=(l["produto"], l["tamanho"], l["total_entrada"]))

    # ------------------------------------------------------------
    def _aba_historico_funcionario(self, parent):
        aba = ttk.Frame(parent, padding=10)
        topo = ttk.Frame(aba)
        topo.pack(fill="x")
        ttk.Label(topo, text="Funcionário:").pack(side="left")
        combo = ComboBusca(topo, width=35)
        combo["values"] = [formatar_opcao(f.id_funcionario, f.nome) for f in listar_funcionarios()]
        combo.pack(side="left", padx=(4, 12))
        self._combo_func = combo
        tree = _criar_tabela(aba, [
            ("data", "Data", 90), ("pedido", "Pedido #", 70), ("produto", "Produto", 160),
            ("tamanho", "Tam.", 60), ("quantidade", "Qtd.", 60), ("setor", "Setor", 120),
            ("usuario", "Baixa por", 130), ("observacao", "Observação", 160),
        ])
        ttk.Button(topo, text="Buscar", command=lambda: self._carregar_historico_funcionario(combo, tree)).pack(side="left")
        return aba

    def _carregar_historico_funcionario(self, combo, tree):
        id_funcionario = extrair_id(combo.get())
        if id_funcionario is None:
            messagebox.showwarning("Selecione", "Escolha um funcionário primeiro.")
            return
        for linha in tree.get_children():
            tree.delete(linha)
        movimentos = historico_funcionario(id_funcionario)
        if not movimentos:
            tree.insert("", "end", values=("(nenhuma saída registrada para esse funcionário)", "", "", "", "", "", "", ""))
        for m in movimentos:
            tree.insert("", "end", values=(
                m["data_saida"], m["id_pedido_saida"], m["produto"], m["tamanho"],
                m["quantidade"], m["setor_loja"], m["usuario"], m["observacao"] or "",
            ))

    # ------------------------------------------------------------
    def _aba_historico_produto(self, parent):
        aba = ttk.Frame(parent, padding=10)
        topo = ttk.Frame(aba)
        topo.pack(fill="x")
        ttk.Label(topo, text="Produto:").pack(side="left")
        combo = ComboBusca(topo, width=35)
        combo["values"] = [formatar_opcao(p.id_produto, p.nome) for p in listar_produtos()]
        combo.pack(side="left", padx=(4, 12))
        self._combo_prod = combo
        tree = _criar_tabela(aba, [
            ("data", "Data", 90), ("tipo", "Tipo", 80), ("quantidade", "Quantidade", 90), ("detalhe", "Detalhe", 320),
        ])
        ttk.Button(topo, text="Buscar", command=lambda: self._carregar_historico_produto(combo, tree)).pack(side="left")
        return aba

    def _carregar_historico_produto(self, combo, tree):
        id_produto = extrair_id(combo.get())
        if id_produto is None:
            messagebox.showwarning("Selecione", "Escolha um produto primeiro.")
            return
        for linha in tree.get_children():
            tree.delete(linha)
        resultado = historico_produto(id_produto)
        if not resultado["movimentos"]:
            tree.insert("", "end", values=("(nenhuma movimentação registrada)", "", "", ""))
        for m in resultado["movimentos"]:
            sinal = "+ Entrada" if m["tipo"] == "entrada" else "- Saída"
            tree.insert("", "end", values=(m["data"], sinal, m["quantidade"], m["detalhe"]))

    # ------------------------------------------------------------
    def _aba_pesquisa_compra(self, parent):
        aba = ttk.Frame(parent, padding=10)
        filtros = ttk.Frame(aba)
        filtros.pack(fill="x")

        ttk.Label(filtros, text="Produto:").grid(row=0, column=0, sticky="w")
        combo_produto = ComboBusca(filtros, width=25)
        combo_produto["values"] = ["(todos)"] + [formatar_opcao(p.id_produto, p.nome) for p in listar_produtos()]
        combo_produto.current(0)
        combo_produto.grid(row=0, column=1, padx=(4, 12))

        ttk.Label(filtros, text="Fornecedor:").grid(row=0, column=2, sticky="w")
        combo_fornecedor = ComboBusca(filtros, width=25)
        combo_fornecedor["values"] = ["(todos)"] + [formatar_opcao(f.id_fornecedor, f.nome) for f in listar_fornecedores()]
        combo_fornecedor.current(0)
        combo_fornecedor.grid(row=0, column=3, padx=(4, 12))

        ttk.Label(filtros, text="Nº do pedido:").grid(row=0, column=4, sticky="w")
        entry_numero = ttk.Entry(filtros, width=10)
        entry_numero.grid(row=0, column=5, padx=(4, 12))

        tree = _criar_tabela(aba, [
            ("id", "Pedido #", 70), ("produto", "Produto", 170), ("fornecedor", "Fornecedor", 140),
            ("quantidade", "Qtd.", 60), ("preco", "Vl. Unit.", 80), ("total", "Vl. Total", 90),
            ("data", "Data", 90), ("observacao", "Observação", 200),
        ])

        def buscar():
            id_produto = extrair_id(combo_produto.get()) if combo_produto.get() != "(todos)" else None
            id_fornecedor = extrair_id(combo_fornecedor.get()) if combo_fornecedor.get() != "(todos)" else None
            numero_texto = entry_numero.get().strip()
            id_pedido = int(numero_texto) if numero_texto.isdigit() else None

            for linha in tree.get_children():
                tree.delete(linha)
            resultados = pesquisar_pedidos_compra(id_produto=id_produto, id_fornecedor=id_fornecedor, id_pedido_compra=id_pedido)
            if not resultados:
                tree.insert("", "end", values=("(nenhum pedido de compra encontrado)", "", "", "", "", "", "", ""))
            for p in resultados:
                preco = float(p.preco) if p.preco is not None else 0
                total = preco * p.quantidade
                tree.insert("", "end", values=(
                    p.id_pedido_compra, p.produto.nome, p.fornecedor.nome,
                    p.quantidade, f"{preco:.2f}", f"{total:.2f}", p.data_compra, p.observacao or "",
                ))

        ttk.Button(filtros, text="Buscar", command=buscar).grid(row=0, column=6)
        buscar()
        return aba

    # ------------------------------------------------------------
    def _aba_historico_operacoes(self, parent):
        aba=ttk.Frame(parent,padding=10)
        topo=ttk.Frame(aba); topo.pack(fill="x")
        ttk.Label(topo,text="Tipo:").pack(side="left")
        combo=ttk.Combobox(topo,state="readonly",width=20,values=["(todos)","CRIAÇÃO","ALTERAÇÃO","EXCLUSÃO","ENTRADA","BAIXA","AJUSTE"])
        combo.current(0); combo.pack(side="left",padx=(4,10))
        tree=_criar_tabela(aba,[("data","Data/Hora",145),("usuario","Usuário",130),("operacao","Operação",90),("entidade","Entidade",130),("registro","Registro #",80),("descricao","Descrição",520)],altura=18)
        def carregar():
            for linha in tree.get_children(): tree.delete(linha)
            tipo=None if combo.get()=="(todos)" else combo.get()
            registros=historico_operacoes(limite=500,operacao=tipo)
            if not registros:
                tree.insert("","end",values=("","","","","","Nenhuma operação registrada.")); return
            for r in registros:
                tree.insert("","end",values=(r.data_hora.strftime("%d/%m/%Y %H:%M:%S") if r.data_hora else "",r.usuario.nome if r.usuario else "Sistema/Desconhecido",r.operacao,r.entidade,r.id_registro or "",r.descricao))
        ttk.Button(topo,text="Atualizar",command=carregar).pack(side="left")
        ttk.Label(aba,text="O histórico registra operações realizadas após a implantação da auditoria.").pack(anchor="w",pady=(8,0))
        carregar(); return aba

    def _aba_listagem_geral(self, parent):
        aba = ttk.Frame(parent, padding=10)
        botoes = ttk.Frame(aba)
        botoes.pack(fill="x")
        ttk.Button(botoes, text="Atualizar", command=lambda: self._carregar_listagem_geral(texto)).pack(side="left", padx=(0, 6))
        ttk.Button(botoes, text="Salvar como .txt...", command=lambda: self._salvar_listagem_geral(texto)).pack(side="left")

        texto = tk.Text(aba, wrap="word")
        texto.pack(fill="both", expand=True, pady=(8, 0))
        self._carregar_listagem_geral(texto)
        return aba

    def _carregar_listagem_geral(self, texto_widget):
        conteudo = formatar_listagem_geral(listagem_geral())
        texto_widget.delete("1.0", tk.END)
        texto_widget.insert("1.0", conteudo)

    def _salvar_listagem_geral(self, texto_widget):
        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivo de texto", "*.txt")],
            initialfile="listagem_geral.txt",
        )
        if not caminho:
            return
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(texto_widget.get("1.0", tk.END))
        messagebox.showinfo("Salvo", f"Listagem salva em:\n{caminho}")
