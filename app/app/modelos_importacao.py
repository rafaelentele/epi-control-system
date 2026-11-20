"""Modelos de planilha para importação (gerados sob demanda, sem depender de arquivos externos)."""
from tkinter import filedialog, messagebox

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.services.importacao_planilha import TIPOS, ROTULO_PARA_TIPO, LIMITE_CAMPO

NOMES_ARQUIVO = {
    "categorias": "Modelo_Importacao_Categorias.xlsx",
    "funcionarios": "Modelo_Importacao_Funcionarios.xlsx",
    "fornecedores": "Modelo_Importacao_Fornecedores.xlsx",
}
EXEMPLOS = {
    "categorias": [["EPI"], ["Fardamento"], ["Calçados"]],
    "funcionarios": [["Maria da Silva"], ["João Pereira"]],
    "fornecedores": [["Fornecedor Exemplo", "(71) 99999-9999"], ["Outra Empresa", "contato@empresa.com"]],
}


def gerar_modelo(destino: str, tipo: str) -> None:
    """Cria a planilha modelo. Aba 'Dados' = só cabeçalhos (pronta para preencher);
    aba 'Instruções' = regras e exemplos (não é lida na importação)."""
    cfg = TIPOS[tipo]
    wb = Workbook()
    ws = wb.active
    ws.title = "Dados"
    ws.append(cfg["colunas"])
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="17365D")
        cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 24
    for i, _ in enumerate(cfg["colunas"], start=1):
        ws.column_dimensions[get_column_letter(i)].width = 38
    ws["A1"].comment = Comment("Não altere os cabeçalhos. Preencha a partir da linha 2.", "Epi Control")

    ins = wb.create_sheet("Instruções")
    ins.column_dimensions["A"].width = 95
    linhas = [
        f"MODELO DE IMPORTAÇÃO - {cfg['rotulo'].upper()}",
        "",
        "1. Preencha apenas a aba 'Dados', a partir da linha 2. Não altere nem apague os cabeçalhos.",
        f"2. Colunas: {', '.join(cfg['colunas'])}" + (" (a coluna contato pode ficar vazia)." if tipo == "fornecedores" else "."),
        f"3. Cada campo aceita no máximo {LIMITE_CAMPO} caracteres.",
        "4. Nomes que já existem no sistema, ou repetidos na planilha, são ignorados. Nada é apagado nem alterado.",
        "5. No sistema: Cadastro e Configuração > Configurações do Sistema > Importar planilha.",
        "",
        "EXEMPLO (não será importado, pois esta aba é ignorada):",
        " | ".join(cfg["colunas"]),
    ] + [" | ".join(l) for l in EXEMPLOS[tipo]]
    for i, texto in enumerate(linhas, start=1):
        ins.cell(row=i, column=1, value=texto)
    ins["A1"].font = Font(bold=True, size=13)
    ins["A9"].font = Font(bold=True)
    wb.save(destino)


def baixar_modelo_importacao(parent):
    import tkinter as tk
    from tkinter import ttk
    escolha = {"valor": None}
    dialog = tk.Toplevel(parent)
    dialog.title("Baixar modelo de importação")
    dialog.transient(parent.winfo_toplevel())
    dialog.resizable(False, False)
    ttk.Label(dialog, text="Escolha o tipo de cadastro para o modelo:").pack(padx=18, pady=(16, 8), anchor="w")
    var = tk.StringVar(value="Categorias")
    ttk.Combobox(dialog, textvariable=var, values=list(ROTULO_PARA_TIPO.keys()), state="readonly", width=28).pack(padx=18, pady=5)

    def confirmar():
        escolha["valor"] = var.get()
        dialog.destroy()

    ttk.Button(dialog, text="Continuar", command=confirmar).pack(pady=(8, 16))
    dialog.grab_set()
    dialog.wait_window()
    rotulo = escolha["valor"]
    if not rotulo:
        return
    tipo = ROTULO_PARA_TIPO[rotulo]
    destino = filedialog.asksaveasfilename(
        parent=parent, title="Salvar modelo de importação", defaultextension=".xlsx",
        initialfile=NOMES_ARQUIVO[tipo], filetypes=[("Planilha Excel", "*.xlsx")],
    )
    if not destino:
        return
    try:
        gerar_modelo(destino, tipo)
        messagebox.showinfo("Modelo criado", f"Modelo de {rotulo.lower()} salvo em:\n{destino}\n\n"
                            "Preencha a aba 'Dados' e importe pelo sistema.", parent=parent)
    except Exception as e:
        messagebox.showerror("Erro ao salvar modelo", str(e), parent=parent)
