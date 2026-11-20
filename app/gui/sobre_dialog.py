"""Janela Sobre com a identificação e o contato do responsável pelo Epi Control."""
from datetime import date
import tkinter as tk
from tkinter import ttk

from app.branding import APP_CONTACT_EMAIL, APP_OWNER, APP_VERSION, asset_path


def abrir_sobre(parent):
    """Abre (ou traz à frente) a janela Sobre do aplicativo."""
    atual = getattr(parent, "_janela_sobre", None)
    try:
        if atual is not None and atual.winfo_exists():
            atual.deiconify()
            atual.lift()
            atual.focus_force()
            return
    except tk.TclError:
        pass

    janela = tk.Toplevel(parent)
    parent._janela_sobre = janela
    janela.title("Sobre o Epi Control")
    janela.resizable(False, False)
    janela.transient(parent.winfo_toplevel())
    try:
        janela.iconbitmap(str(asset_path("icone_sistema.ico")))
    except (OSError, tk.TclError):
        pass

    quadro = ttk.Frame(janela, padding=(28, 22))
    quadro.pack(fill="both", expand=True)
    ttk.Label(quadro, text="Epi Control", font=("Segoe UI", 20, "bold"), foreground="#17365D").pack()
    ttk.Label(quadro, text="Sistema independente para gestão de EPI e fardamento").pack(pady=(3, 16))
    ttk.Separator(quadro).pack(fill="x", pady=(0, 14))
    ttk.Label(quadro, text="Desenvolvido e mantido por").pack()
    ttk.Label(quadro, text=APP_OWNER, font=("Segoe UI", 11, "bold")).pack(pady=(3, 12))
    ttk.Label(quadro, text="Contato profissional").pack()
    contato = ttk.Entry(quadro, width=36, justify="center")
    contato.insert(0, APP_CONTACT_EMAIL)
    contato.configure(state="readonly")
    contato.pack(pady=(3, 12))
    ttk.Label(quadro, text=f"Versão {APP_VERSION}  ·  © {date.today().year} {APP_OWNER}").pack()
    botao = ttk.Button(quadro, text="Fechar", command=janela.destroy)
    botao.pack(pady=(18, 0))

    janela.bind("<Escape>", lambda _evento: janela.destroy())
    janela.bind("<Return>", lambda _evento: janela.destroy())
    janela.update_idletasks()
    try:
        x = parent.winfo_rootx() + (parent.winfo_width() - janela.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - janela.winfo_reqheight()) // 3
        janela.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    except tk.TclError:
        pass
    try:
        janela.grab_set()
    except tk.TclError:
        pass
    botao.focus_set()
