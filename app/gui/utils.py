"""Auxiliares compartilhados pelas telas que usam Combobox (ex: escolher
um produto ou categoria por nome, mas trabalhar com o id por trás)."""
import tkinter as tk
from tkinter import ttk


def formatar_opcao(id_, nome):
    return f"{id_} - {nome}"


def extrair_id(texto_opcao: str):
    """Devolve o id do início de 'id - nome'; None se vazio ou fora do formato."""
    if not texto_opcao:
        return None
    try:
        return int(texto_opcao.split(" - ")[0])
    except ValueError:
        return None


# ----------------------------------------------------------------------
# Navegação: sub-telas sem abas visíveis (a escolha é feita pelos menus)
# ----------------------------------------------------------------------
def criar_notebook_sem_abas(parent, nome_estilo="SemAbas.TNotebook"):
    """Cria um ttk.Notebook cujas abas ficam ocultas; a troca é feita só por código."""
    from tkinter import ttk
    estilo = ttk.Style(parent)
    estilo.layout(f"{nome_estilo}.Tab", [])
    return ttk.Notebook(parent, style=nome_estilo)


class SubtelasMixin:
    """Dá a um frame com `sub_notebook` o registro de sub-telas por nome."""

    def _iniciar_subtelas(self):
        self.subtelas = {}

    def _adicionar_subtela(self, chave, frame, texto):
        self.sub_notebook.add(frame, text=texto)
        self.subtelas[chave] = frame
        return frame

    def abrir_subtela(self, chave):
        """Mostra a sub-tela `chave` e devolve o widget (ou None se não existir)."""
        frame = self.subtelas.get(chave)
        if frame is not None:
            self.sub_notebook.select(frame)
        return frame


# ----------------------------------------------------------------------
# Datas: nunca gravar uma data diferente da que a pessoa digitou
# ----------------------------------------------------------------------
def ler_data_campo(entry):
    """Lê uma data dd/mm/aaaa de um campo de texto.

    * campo vazio  -> data de hoje;
    * data válida  -> a data digitada (aceita também 10-10-2026 e 10.10.2026);
    * data inválida -> avisa, deixa o cursor no campo e devolve None.
      Quem chamou deve CANCELAR o salvamento quando receber None.
    """
    import tkinter as tk
    from datetime import date, datetime
    from tkinter import messagebox

    texto = entry.get().strip()
    if not texto:
        return date.today()
    normalizado = texto.replace("-", "/").replace(".", "/")
    try:
        return datetime.strptime(normalizado, "%d/%m/%Y").date()
    except ValueError:
        messagebox.showwarning(
            "Data inválida",
            f"A data \u201c{texto}\u201d não é válida.\n\n"
            "Use o formato dd/mm/aaaa (exemplo: 10/10/2026).\n"
            "Nada foi salvo.",
            parent=entry.winfo_toplevel(),
        )
        entry.focus_set()
        entry.select_range(0, tk.END)
        return None


# ----------------------------------------------------------------------
# Lista suspensa com busca: digite parte do nome para filtrar
# ----------------------------------------------------------------------
def _normalizar(texto):
    import unicodedata
    texto = unicodedata.normalize("NFD", str(texto).casefold())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


class ComboBusca(ttk.Combobox):
    """Combobox em que se pode DIGITAR para filtrar as opções.

    * ignora maiúsculas e acentos; várias palavras valem juntas (ex.: "cam pol");
    * a seta para baixo (ou o clique na setinha) abre a lista já filtrada;
    * Enter / Tab escolhe a opção se só restar uma; se restarem várias, Enter
      abre a lista para a pessoa escolher; texto que não existe na lista é
      descartado - nunca fica um valor inválido no campo;
    * get() só devolve uma opção que realmente existe na lista (senão "").
    Funciona como o Combobox normal: `combo["values"] = [...]` continua valendo.
    """

    _IGNORAR = {
        "Up", "Down", "Left", "Right", "Return", "KP_Enter", "Tab", "ISO_Left_Tab", "Escape",
        "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Caps_Lock",
        "Home", "End", "Prior", "Next",
    }

    def __init__(self, master=None, **kw):
        valores = list(kw.pop("values", ()))
        kw.pop("state", None)  # sempre editável (a validação é feita aqui)
        super().__init__(master, **kw)
        self._todos = valores
        ttk.Combobox.configure(self, values=valores)
        self.bind("<KeyRelease>", self._ao_digitar, add="+")
        self.bind("<Return>", self._ao_enter, add="+")
        self.bind("<KP_Enter>", self._ao_enter, add="+")
        self.bind("<FocusOut>", self._ao_perder_foco, add="+")
        self.bind("<<ComboboxSelected>>", self._ao_escolher_na_lista, add="+")

    # -- valores ---------------------------------------------------------
    def configure(self, cnf=None, **kw):
        if isinstance(cnf, dict) and "values" in cnf:
            self._todos = list(cnf["values"])
        if "values" in kw:
            self._todos = list(kw["values"])
        return super().configure(cnf, **kw)

    config = configure

    def _filtradas(self, texto):
        termos = _normalizar(texto).split()
        if not termos:
            return list(self._todos)
        return [o for o in self._todos if all(t in _normalizar(o) for t in termos)]

    def _mostrar_todas(self):
        ttk.Combobox.configure(self, values=self._todos)

    def _texto(self):
        return ttk.Combobox.get(self)

    def get(self):
        texto = self._texto()
        if not texto or texto in self._todos:
            return texto
        achadas = self._filtradas(texto)
        return achadas[0] if len(achadas) == 1 else ""

    # -- eventos ---------------------------------------------------------
    def _ao_digitar(self, evento):
        if evento.keysym in self._IGNORAR:
            return
        ttk.Combobox.configure(self, values=self._filtradas(self._texto()))

    def _escolher(self, opcao, avancar=False):
        self.set(opcao)
        self._mostrar_todas()
        self.icursor("end")
        self.event_generate("<<ComboboxSelected>>")
        if avancar:
            try:
                self.tk_focusNext().focus_set()
            except Exception:
                pass

    def _ao_enter(self, _evento=None):
        texto = self._texto()
        if not texto:
            return None
        if texto in self._todos:
            self._mostrar_todas()
            return None
        achadas = self._filtradas(texto)
        if len(achadas) == 1:
            self._escolher(achadas[0], avancar=True)
        elif len(achadas) > 1:
            self.event_generate("<Down>")  # abre a lista só com as opções filtradas
        else:
            self._descartar(texto)
        return "break"

    def _ao_escolher_na_lista(self, _evento=None):
        self._mostrar_todas()

    def _ao_perder_foco(self, _evento=None):
        self.after(150, self._validar)

    def _validar(self):
        try:
            if not self.winfo_exists():
                return
            try:  # a lista aberta também tira o foco do campo: nesse caso não valida
                if self.tk.call("winfo", "ismapped", f"{self}.popdown"):
                    return
            except tk.TclError:
                pass
            if self.focus_get() is self:
                return
            texto = self._texto()
            if not texto or texto in self._todos:
                self._mostrar_todas()
                return
            achadas = self._filtradas(texto)
            if len(achadas) == 1:
                self._escolher(achadas[0])
            else:
                self._descartar(texto)
        except tk.TclError:
            pass

    def _descartar(self, texto):
        self.set("")
        self._mostrar_todas()
        self.bell()
        avisar = getattr(self.winfo_toplevel(), "_avisar", None)
        if callable(avisar):
            avisar(f"\u201c{texto}\u201d não corresponde a nenhuma opção da lista.")


# ----------------------------------------------------------------------
# Listas (Treeview) com pesquisa e ordenação por clique no título da coluna
# ----------------------------------------------------------------------
import re as _re

_RE_DATA_BR = _re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_RE_DATA_ISO = _re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def _chave_ordenacao(valor):
    """Chave de ordenação 'natural': datas como datas, números como números
    (aceita 1.234,56 e 49.90) e o resto como texto sem acento/maiúscula."""
    texto = str(valor).strip()
    m = _RE_DATA_BR.match(texto)
    if m:
        dia, mes, ano = m.groups()
        return (0, int(ano), int(mes), int(dia))
    m = _RE_DATA_ISO.match(texto)
    if m:
        ano, mes, dia = m.groups()
        return (0, int(ano), int(mes), int(dia))
    numero = texto.replace("R$", "").replace(" ", "")
    if "," in numero:
        numero = numero.replace(".", "").replace(",", ".")
    try:
        return (1, float(numero))
    except ValueError:
        return (2, _normalizar(texto))


class TreeviewBusca(ttk.Treeview):
    """Treeview que sabe filtrar (pesquisa) e ordenar (clique no título).

    Funciona como o Treeview normal: as telas continuam apagando e inserindo
    linhas como antes; o filtro e a ordem escolhidos são reaplicados sozinhos
    depois de cada recarga. As linhas que não casam com a pesquisa ficam
    apenas ocultas (get_children() continua devolvendo todas, para que
    "apagar tudo e recarregar" funcione).

    Clique no título: crescente -> decrescente -> ordem original.
    """

    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._ocultos = {}        # iid -> None (dict usado como conjunto ordenado)
        self._ordem = {}          # iid -> ordem de inserção (ordem original)
        self._contador = 0
        self._termo = []          # palavras da pesquisa (normalizadas)
        self._col_ordem = None
        self._reverso = False
        self._job = None
        self._barra = None
        for coluna in self["columns"]:
            self.heading(coluna, command=lambda c=coluna: self.ordenar_por(c))

    # -- compatibilidade com o Treeview normal ---------------------------
    def get_children(self, item=None):
        filhos = super().get_children(item)
        if not item:
            return filhos + tuple(self._ocultos)
        return filhos

    def delete(self, *itens):
        for i in itens:
            self._ocultos.pop(i, None)
            self._ordem.pop(i, None)
        return super().delete(*itens)

    def insert(self, parent, index, iid=None, **kw):
        item = super().insert(parent, index, iid=iid, **kw)
        if parent == "":
            self._contador += 1
            self._ordem[item] = self._contador
            self._agendar()
        return item

    # -- pesquisa --------------------------------------------------------
    def definir_filtro(self, texto):
        self._termo = _normalizar(texto).split()
        self._reaplicar()

    def _casa(self, item):
        if not self._termo:
            return True
        texto = _normalizar(" ".join(str(v) for v in self.item(item, "values")))
        return all(t in texto for t in self._termo)

    # -- ordenação -------------------------------------------------------
    def ordenar_por(self, coluna):
        if self._col_ordem == coluna:
            if not self._reverso:
                self._reverso = True
            else:  # terceiro clique: volta à ordem original
                self._col_ordem, self._reverso = None, False
        else:
            self._col_ordem, self._reverso = coluna, False
        self._atualizar_setas()
        self._reaplicar()

    def _atualizar_setas(self):
        for coluna in self["columns"]:
            texto = str(self.heading(coluna, "text")).replace(" ▲", "").replace(" ▼", "")
            if coluna == self._col_ordem:
                texto += " ▼" if self._reverso else " ▲"
            self.heading(coluna, text=texto)

    # -- aplicação -------------------------------------------------------
    def _agendar(self):
        if self._job is None:
            self._job = self.after_idle(self._tarefa)

    def _tarefa(self):
        self._job = None
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._termo or self._col_ordem is not None:
            self._reaplicar()
        else:
            self._contar()

    def _contar(self):
        total = len(super().get_children("")) + len(self._ocultos)
        if self._barra is not None:
            self._barra.atualizar_contagem(total, total)

    def _reaplicar(self):
        atuais = list(super().get_children(""))
        todos = atuais + list(self._ocultos)
        todos.sort(key=lambda i: self._ordem.get(i, 0))
        if self._col_ordem is not None:
            coluna = self._col_ordem
            todos.sort(key=lambda i: _chave_ordenacao(self.set(i, coluna)), reverse=self._reverso)
        visiveis = [i for i in todos if self._casa(i)]
        conjunto = set(visiveis)
        ocultar = [i for i in atuais if i not in conjunto]
        if ocultar:
            self.detach(*ocultar)
        self._ocultos = {i: None for i in todos if i not in conjunto}
        for posicao, i in enumerate(visiveis):
            self.move(i, "", posicao)
        if self._barra is not None:
            self._barra.atualizar_contagem(len(visiveis), len(todos))


class BarraPesquisa(ttk.Frame):
    """Campo 'Pesquisar' + contador, ligado a um TreeviewBusca."""

    def __init__(self, master, tree):
        super().__init__(master)
        self.tree = tree
        if tree is not None:
            tree._barra = self
        ttk.Label(self, text="🔎 Pesquisar:").pack(side="left")
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=32)
        self.entry.pack(side="left", padx=6)
        ttk.Button(self, text="Limpar", width=8, command=self.limpar).pack(side="left")
        self.lbl = ttk.Label(self, text="", foreground="#666")
        self.lbl.pack(side="left", padx=10)
        self._job = None
        self.var.trace_add("write", self._mudou)
        self.entry.bind("<Escape>", lambda e: self.limpar())

    def ligar(self, tree):
        """Liga a barra a uma nova árvore (usado quando a tela recria a tabela) e reaplica a pesquisa."""
        self.tree = tree
        tree._barra = self
        tree.definir_filtro(self.var.get())

    def _mudou(self, *_):
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(200, self._aplicar)

    def _aplicar(self):
        self._job = None
        if self.tree is not None:
            self.tree.definir_filtro(self.var.get())

    def limpar(self):
        self.var.set("")
        self.entry.focus_set()

    def atualizar_contagem(self, visiveis, total):
        if visiveis == total:
            self.lbl.configure(text=f"{total} registro(s)")
        else:
            self.lbl.configure(text=f"{visiveis} de {total}")


def adicionar_pesquisa(tree):
    """Coloca a barra de pesquisa logo acima de um TreeviewBusca (que deve estar em pack)."""
    barra = BarraPesquisa(tree.master, tree)
    barra.pack(side="top", fill="x", pady=(8, 4), before=tree)
    return barra
