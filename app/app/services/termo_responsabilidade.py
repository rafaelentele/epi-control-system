"""
Gera o "Termo de Responsabilidade" em PDF a partir de um pedido de
saída - reproduz o modelo em Excel que a empresa já usava
(termo_de_responsabilidade.xlsx), preenchendo automaticamente:

- Os itens entregues (produto, categoria, tamanho, quantidade),
  vindos do pedido de saída informado.
- O nome do funcionário, na linha de assinatura.

A data do documento é passada como parâmetro (editável na tela),
não vem fixa do pedido - assim dá pra emitir o termo numa data
diferente da data do pedido, se precisar.
"""

from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from app.repositories.crud_saida import buscar_pedido_saida
from app.repositories.crud_produtos import categoria_e_epi
from app.term_config import carregar_configuracoes, obter_modelo

CLAUSULAS = [
    "1. Se o equipamento for danificado ou inutilizado por emprego inadequado, mau uso, a empresa me "
    "fornecerá novo equipamento e cobrará valor de um equipamento da mesma marca ou equivalente ao da praça.",
    "2. Em caso de dano, inutilização ou extravio do equipamento deverei comunicar imediatamente ao setor competente.",
    "3. Terminando os serviços ou no caso de rescisão do contrato de trabalho, devolverei ao setor competente "
    "o equipamento completo e em perfeito estado de conservação, considerando-se o tempo do uso do mesmo (tempo de vida útil).",
    "4. Estando os equipamentos em minha posse, estarei sujeito a inspeções sem aviso prévio.",
    "5. Em casos de roubo/assalto durante o trajeto para o trabalho ou retorno do mesmo, deverei comunicar a "
    "empresa e apresentar o boletim de ocorrência o mais breve possível, sem nenhum tipo de punição ou desconto.",
    "6. Declaro ainda, que estou ciente de que a não utilização dos EPI’s (Equipamento de Proteção Individual), "
    "constituirá em falta grave sujeita a punições disciplinares de acordo com a legislação trabalhista vigente.",
]

NOME_EMPRESA = "Empresa"
LINHAS_EXTRAS_EM_BRANCO = 3  # linhas vazias no fim da tabela, pra anotação futura à mão


def gerar_termo_responsabilidade_pdf(id_pedido_saida: int, data_documento: date, caminho_saida: str, modelo_id: str = None) -> None:
    pedido = buscar_pedido_saida(id_pedido_saida)
    if pedido is None:
        raise ValueError(f"Pedido de saída com número {id_pedido_saida} não existe.")
    if not pedido.itens:
        raise ValueError(f"Pedido #{id_pedido_saida} não tem nenhum item — não há o que gerar no termo.")

    for item in pedido.itens:
        categoria = item.produto.categoria if item.produto else None
        if categoria_e_epi(categoria) and not (item.produto.ca if item.produto else ""):
            raise ValueError(
                f"O produto '{item.produto.nome if item.produto else '-'}' é EPI e está sem CA cadastrado. "
                "Cadastre o CA do produto antes de gerar o termo."
            )

    data_formatada = data_documento.strftime("%d/%m/%Y") if data_documento else "___/___/______"

    doc = SimpleDocTemplate(
        caminho_saida, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    justificado = ParagraphStyle("justificado", parent=styles["Normal"], alignment=TA_JUSTIFY, fontSize=9, leading=12)
    centralizado = ParagraphStyle("centralizado", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10)
    centralizado_negrito = ParagraphStyle("centralizado_negrito", parent=centralizado, fontName="Helvetica-Bold")
    titulo = ParagraphStyle(
        "titulo", parent=styles["Normal"], alignment=TA_CENTER,
        fontName="Helvetica-Bold", fontSize=18, spaceAfter=16,
    )

    funcionario = pedido.funcionario
    empresa_funcionario = funcionario.empresa if funcionario else None
    if not empresa_funcionario:
        raise ValueError(
            "O funcionário deste pedido não possui empresa vinculada. "
            "Acesse Cadastros > Funcionários, selecione o funcionário e informe a empresa antes de gerar o termo."
        )

    cfg = carregar_configuracoes()
    modelo = obter_modelo(cfg, modelo_id)
    # A empresa do termo sempre vem do funcionário; configurações antigas não sobrescrevem o vínculo.
    nome_empresa = empresa_funcionario.razao_social
    story = []
    logo = cfg.get("logo_empresa")
    if logo and __import__("os").path.isfile(logo):
        try:
            from reportlab.platypus import Image as ReportImage
            img = ReportImage(logo, width=4*cm, height=2*cm, kind="proportional")
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 6))
        except Exception: pass
    titulo_termo = modelo.get("titulo") or "TERMO DE RESPONSABILIDADE"
    story.append(Paragraph(titulo_termo, titulo))
    dados_substituicao = {
        "{empresa}": nome_empresa,
        "{funcionario}": pedido.funcionario.nome if pedido.funcionario else "",
        "{setor}": pedido.setor_loja.nome if pedido.setor_loja else "",
        "{pedido}": str(pedido.id_pedido_saida),
        "{data}": data_formatada,
    }
    def aplicar_variaveis(texto):
        texto = str(texto or "")
        for chave, valor in dados_substituicao.items():
            texto = texto.replace(chave, escape(str(valor)))
        return texto

    texto_abertura_modelo = modelo.get("texto_abertura") or "Recebi da empresa {empresa}, gratuitamente, para uso exclusivo no desempenho de minhas atividades na empresa, conforme determinado em lei, os equipamentos relacionados neste termo de responsabilidade."
    texto_compromisso_modelo = modelo.get("texto_compromisso") or "Comprometo-me a usar e mantê-lo em perfeito estado de conservação, ficando ainda ciente de:"
    clausulas = modelo.get("clausulas") or CLAUSULAS
    textos_modelo = [texto_abertura_modelo, texto_compromisso_modelo, *clausulas]
    if not any("{empresa}" in str(texto) for texto in textos_modelo):
        story.append(Paragraph(f"<b>Empresa do funcionário:</b> {escape(str(nome_empresa))}", justificado))
        story.append(Spacer(1, 4))

    texto_abertura = aplicar_variaveis(texto_abertura_modelo)
    story.append(Paragraph(texto_abertura, justificado))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        aplicar_variaveis(texto_compromisso_modelo), justificado,
    ))
    story.append(Spacer(1, 8))

    for clausula in clausulas:
        if str(clausula).strip():
            story.append(Paragraph(aplicar_variaveis(clausula), justificado))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Pedido de Entrega: {pedido.id_pedido_saida}</b>", styles["Normal"]))
    story.append(Paragraph("<b>FARDAMENTO, ACESSÓRIOS e E.P.I.s</b>", styles["Normal"]))
    story.append(Spacer(1, 6))

    cabecalho = ["DATA", "ITEM", "CA", "TIPO", "TAMANHO", "QUANT", "RECEBI/ASSINATURA"]
    linhas = [cabecalho]
    estilo_celula = ParagraphStyle("celula_termo", parent=styles["Normal"], fontSize=8, leading=9, alignment=TA_CENTER)
    estilo_item = ParagraphStyle("item_termo", parent=estilo_celula, alignment=0)
    for item in pedido.itens:
        tipo = item.produto.categoria.nome if item.produto and item.produto.categoria else "-"
        valores = [
            data_formatada,
            item.produto.nome if item.produto else "-",
            (item.produto.ca if item.produto and item.produto.ca else "-"),
            tipo,
            item.tamanho.nome if item.tamanho else "-",
            str(item.quantidade),
            "",
        ]
        linhas.append([
            Paragraph(escape(str(valor)), estilo_item if indice == 1 else estilo_celula)
            for indice, valor in enumerate(valores)
        ])
    for _ in range(LINHAS_EXTRAS_EM_BRANCO):
        linhas.append(["", "", "", "", "", "", ""])

    tabela = Table(linhas, colWidths=[2.0 * cm, 4.0 * cm, 3.0 * cm, 1.8 * cm, 1.7 * cm, 1.3 * cm, 3.4 * cm], repeatRows=1)
    tabela.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9D9D9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
    ]))
    story.append(tabela)

    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Data: {data_formatada}", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Declaro ciente:", styles["Normal"]))
    story.append(Spacer(1, 34))
    story.append(Paragraph("_" * 45, centralizado))
    story.append(Paragraph("Assinatura de colaborador", centralizado))
    nome_funcionario = pedido.funcionario.nome.upper() if pedido.funcionario else ""
    cpf_funcionario = (pedido.funcionario.cpf or "").strip() if pedido.funcionario else ""
    if not cpf_funcionario:
        raise ValueError(
            "O funcionário selecionado não possui CPF cadastrado. "
            "Acesse Cadastros > Funcionários, informe um CPF válido e gere o termo novamente."
        )
    story.append(Paragraph(nome_funcionario, centralizado_negrito))
    story.append(Paragraph(f"CPF: {cpf_funcionario}", centralizado))

    doc.build(story)
