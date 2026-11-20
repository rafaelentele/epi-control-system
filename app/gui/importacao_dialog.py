"""Diálogo de importação de planilha: escolher tipo e arquivo, ver prévia, confirmar."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app.services.importacao_planilha import (
    ROTULO_PARA_TIPO, ErroImportacao, analisar_planilha, importar_planilha,
)


def _resumo(a, limite=8):
    linhas = [f"Novos registros: {len(a.novos)}",
              f"Duplicados (ignorados): {len(a.duplicados)}",
              f"Rejeitados: {len(a.rejeitados)}"]
    if a.novos:
        linhas += ["", "Serão adicionados (primeiros):"] + [f"  • {d['nome']}" for _, d in a.novos[:limite]]
        if len(a.novos) > limite:
            linhas.append(f"  … e mais {len(a.novos) - limite}")
    if a.rejeitados:
        linhas += ["", "Rejeitados:"] + [f"  • linha {n}: {m}" for n, m in a.rejeitados[:limite]]
        if len(a.rejeitados) > limite:
            linhas.append(f"  … e mais {len(a.rejeitados) - limite}")
    return "\n".join(linhas)


def importar_planilha_dialog(parent):
    escolha = {"tipo": None}
    dialog = tk.Toplevel(parent)
    dialog.title("Importar planilha")
    dialog.transient(parent.winfo_toplevel())
    dialog.resizable(False, False)
    ttk.Label(dialog, text="O que você vai importar?").pack(padx=18, pady=(16, 8), anchor="w")
    var = tk.StringVar(value="Categorias")
    ttk.Combobox(dialog, textvariable=var, values=list(ROTULO_PARA_TIPO.keys()), state="readonly", width=28).pack(padx=18, pady=5)

    def continuar():
        escolha["tipo"] = ROTULO_PARA_TIPO[var.get()]
        dialog.destroy()

    ttk.Button(dialog, text="Escolher arquivo...", command=continuar).pack(pady=(8, 16))
    dialog.grab_set()
    dialog.wait_window()
    tipo = escolha["tipo"]
    if not tipo:
        return

    caminho = filedialog.askopenfilename(
        parent=parent, title="Escolher planilha",
        filetypes=[("Planilhas", "*.xlsx *.csv"), ("Excel", "*.xlsx"), ("CSV", "*.csv")],
    )
    if not caminho:
        return
    try:
        analise = analisar_planilha(caminho, tipo)
    except ErroImportacao as e:
        messagebox.showerror("Importação", str(e), parent=parent)
        return
    except Exception as e:
        messagebox.showerror("Importação", f"Erro ao analisar a planilha:\n{e}", parent=parent)
        return

    if not analise.novos:
        messagebox.showinfo("Importação", "Não há nada novo para importar.\n\n" + _resumo(analise), parent=parent)
        return
    if not messagebox.askyesno("Confirmar importação",
                               _resumo(analise) + "\n\nImportar agora? (Faça backup antes, se ainda não fez.)",
                               parent=parent):
        return
    try:
        resultado = importar_planilha(caminho, tipo)
    except ErroImportacao as e:
        messagebox.showerror("Importação", str(e), parent=parent)
        return
    except Exception as e:
        messagebox.showerror("Erro na importação", f"Nada foi gravado.\n\n{e}", parent=parent)
        return
    messagebox.showinfo("Importação concluída",
                        f"Adicionados: {len(resultado.novos)}\nDuplicados ignorados: {len(resultado.duplicados)}\n"
                        f"Rejeitados: {len(resultado.rejeitados)}", parent=parent)
