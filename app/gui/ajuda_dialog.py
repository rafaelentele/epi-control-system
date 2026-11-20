"""Botão Ajuda / Manual: mostra o manual de instruções em uma janela."""
import re
import tkinter as tk
from tkinter import ttk, messagebox

from app.branding import asset_path

ARQUIVO_MANUAL = "MANUAL_DE_INSTRUCOES.md"


def interpretar_manual(texto: str):
    """Converte o Markdown simples do manual em lista de (trecho, [tags])."""
    saida = []

    def inline(linha, base):
        linha = linha.replace("`", "")
        partes = re.split(r"(\*\*[^*]+\*\*)", linha)
        for p in partes:
            if p.startswith("**") and p.endswith("**") and len(p) > 4:
                saida.append((p[2:-2], base + ["negrito"]))
            elif p:
                saida.append((p, base))

    for bruta in texto.splitlines():
        linha = bruta.rstrip()
        if not linha.strip():
            saida.append(("\n", []))
        elif linha.startswith("## "):
            saida.append((linha[3:].strip() + "\n", ["h2"]))
        elif linha.startswith("# "):
            saida.append((linha[2:].strip() + "\n", ["h1"]))
        elif linha.startswith("- "):
            saida.append(("  \u2022 ", ["item"]))
            inline(linha[2:], ["item"])
            saida.append(("\n", ["item"]))
        elif re.match(r"^\d+\.\s", linha):
            saida.append(("  ", ["item"]))
            inline(linha, ["item"])
            saida.append(("\n", ["item"]))
        else:
            inline(linha, [])
            saida.append(("\n", []))
    return saida


def abrir_manual(parent):
    # Reaproveita a janela se já estiver aberta.
    atual = getattr(parent, "_janela_manual", None)
    try:
        if atual is not None and atual.winfo_exists():
            atual.deiconify()
            atual.lift()
            atual.focus_force()
            return
    except Exception:
        pass

    try:
        texto = asset_path(ARQUIVO_MANUAL).read_text(encoding="utf-8")
    except Exception as e:
        messagebox.showerror("Manual", f"Não foi possível abrir o manual.\n\n{e}", parent=parent)
        return

    janela = tk.Toplevel(parent)
    parent._janela_manual = janela
    janela.title("Manual de instruções")
    janela.geometry("820x640")
    janela.minsize(560, 400)
    janela.transient(parent.winfo_toplevel())

    quadro = ttk.Frame(janela, padding=8)
    quadro.pack(fill="both", expand=True)
    rolagem = ttk.Scrollbar(quadro, orient="vertical")
    rolagem.pack(side="right", fill="y")
    caixa = tk.Text(quadro, wrap="word", yscrollcommand=rolagem.set, padx=14, pady=10,
                    font=("Segoe UI", 10), bg="white", relief="flat", spacing3=3)
    caixa.pack(side="left", fill="both", expand=True)
    rolagem.config(command=caixa.yview)

    caixa.tag_configure("h1", font=("Segoe UI", 16, "bold"), foreground="#17365D", spacing1=4, spacing3=10)
    caixa.tag_configure("h2", font=("Segoe UI", 12, "bold"), foreground="#17365D", spacing1=12, spacing3=4)
    caixa.tag_configure("negrito", font=("Segoe UI", 10, "bold"))
    caixa.tag_configure("item", lmargin1=12, lmargin2=34)

    for trecho, tags in interpretar_manual(texto):
        caixa.insert("end", trecho, tuple(tags))
    caixa.configure(state="disabled")

    ttk.Button(janela, text="Fechar", command=janela.destroy).pack(pady=(0, 10))
