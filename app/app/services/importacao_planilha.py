"""Importação de cadastros por planilha (Excel .xlsx ou CSV).

Tipos aceitos: categorias, funcionarios, fornecedores.
Regras:
- Só ADICIONA registros; nunca altera nem apaga os existentes.
- Nomes já existentes (ignorando maiúsculas/minúsculas e espaços extras) e nomes
  repetidos dentro da própria planilha são ignorados.
- Linhas com nome vazio ou acima do limite de caracteres da coluna são rejeitadas
  e listadas com o número da linha; as demais são importadas.
- Tudo é gravado em uma única transação e registrado na auditoria.

Fluxo: analisar_planilha() (não grava nada, serve para a pré-visualização)
e importar_planilha() (grava).
"""
import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field

from app.config.database import get_session
from app.models.models import Categoria, Fornecedor, Funcionario
from app.auth import tem_permissao
from app.repositories.crud_auditoria import registrar_auditoria

LIMITE_CAMPO = 45  # tamanho das colunas nome/contato no banco

TIPOS = {
    "categorias": {
        "rotulo": "Categorias", "modelo": Categoria, "colunas": ["nome"],
        "obrigatorias": ["nome"], "permissao": "cadastrar_produtos",
    },
    "funcionarios": {
        "rotulo": "Funcionários", "modelo": Funcionario, "colunas": ["nome"],
        "obrigatorias": ["nome"], "permissao": "cadastrar_funcionarios",
    },
    "fornecedores": {
        "rotulo": "Fornecedores", "modelo": Fornecedor, "colunas": ["nome", "contato"],
        "obrigatorias": ["nome", "contato"], "permissao": "cadastrar_fornecedores",
    },
}
ROTULO_PARA_TIPO = {v["rotulo"]: k for k, v in TIPOS.items()}


class ErroImportacao(Exception):
    """Erro de leitura/validação da planilha (mensagem pronta para o usuário)."""


@dataclass
class Analise:
    tipo: str
    novos: list = field(default_factory=list)        # [(linha, {coluna: valor})]
    duplicados: list = field(default_factory=list)   # [(linha, nome, motivo)]
    rejeitados: list = field(default_factory=list)   # [(linha, motivo)]


def _normalizar(texto) -> str:
    """Chave de comparação: sem acento, minúscula, espaços únicos."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().casefold()


def _limpar(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"\s+", " ", str(valor)).strip()


def _ler_xlsx(caminho):
    from openpyxl import load_workbook
    wb = load_workbook(caminho, read_only=True, data_only=True)
    try:
        ws = wb["Dados"] if "Dados" in wb.sheetnames else wb[wb.sheetnames[0]]
        return [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def _ler_csv(caminho):
    dados = None
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            with open(caminho, "r", encoding=codificacao, newline="") as f:
                dados = f.read()
            break
        except UnicodeDecodeError:
            continue
    if dados is None:
        raise ErroImportacao("Não foi possível ler o arquivo CSV (codificação desconhecida).")
    amostra = dados[:4096]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t")
    except csv.Error:
        class dialeto(csv.excel):
            delimiter = ";" if amostra.count(";") > amostra.count(",") else ","
    return [row for row in csv.reader(io.StringIO(dados), dialeto)]


def ler_planilha(caminho: str):
    """Devolve (cabecalhos_normalizados, linhas) onde linhas = [(nº_linha, {col: valor})]."""
    caminho_min = caminho.lower()
    try:
        if caminho_min.endswith((".xlsx", ".xlsm")):
            linhas_brutas = _ler_xlsx(caminho)
        elif caminho_min.endswith(".csv"):
            linhas_brutas = _ler_csv(caminho)
        else:
            raise ErroImportacao("Formato não suportado. Use .xlsx ou .csv.")
    except ErroImportacao:
        raise
    except Exception as e:
        raise ErroImportacao(f"Não foi possível abrir a planilha: {e}")

    # primeira linha não vazia = cabeçalho
    inicio = next((i for i, r in enumerate(linhas_brutas) if any(_limpar(c) for c in r)), None)
    if inicio is None:
        raise ErroImportacao("A planilha está vazia.")
    cabecalhos = [_normalizar(c) for c in linhas_brutas[inicio]]
    linhas = []
    for i, r in enumerate(linhas_brutas[inicio + 1:], start=inicio + 2):
        if not any(_limpar(c) for c in r):
            continue
        linhas.append((i, {cabecalhos[j]: _limpar(r[j]) for j in range(min(len(cabecalhos), len(r))) if cabecalhos[j]}))
    return cabecalhos, linhas


def analisar_planilha(caminho: str, tipo: str) -> Analise:
    """Lê e valida a planilha SEM gravar nada no banco."""
    if tipo not in TIPOS:
        raise ErroImportacao("Tipo de cadastro inválido.")
    cfg = TIPOS[tipo]
    cabecalhos, linhas = ler_planilha(caminho)
    faltando = [c for c in cfg["obrigatorias"] if c not in cabecalhos]
    if faltando:
        raise ErroImportacao(
            f"A planilha não tem a(s) coluna(s) obrigatória(s): {', '.join(faltando)}.\n"
            f"Cabeçalhos encontrados: {', '.join(c for c in cabecalhos if c) or '(nenhum)'}.\n"
            f"Para {cfg['rotulo'].lower()}, use exatamente: {', '.join(cfg['colunas'])}.\n"
            "Nenhum dado foi importado."
        )
    if not linhas:
        raise ErroImportacao("A planilha tem o cabeçalho, mas nenhuma linha de dados.")

    session = get_session()
    try:
        existentes = {_normalizar(n) for (n,) in session.query(cfg["modelo"].nome).all()}
    finally:
        session.close()

    analise = Analise(tipo=tipo)
    vistos = set()
    for numero, dados in linhas:
        nome = dados.get("nome", "")
        if not nome:
            analise.rejeitados.append((numero, "nome vazio"))
            continue
        invalido = next((f"{c} com {len(dados.get(c, ''))} caracteres (máximo {LIMITE_CAMPO})"
                         for c in cfg["colunas"] if len(dados.get(c, "")) > LIMITE_CAMPO), None)
        if invalido:
            analise.rejeitados.append((numero, invalido))
            continue
        chave = _normalizar(nome)
        if chave in existentes:
            analise.duplicados.append((numero, nome, "já cadastrado"))
            continue
        if chave in vistos:
            analise.duplicados.append((numero, nome, "repetido na planilha"))
            continue
        vistos.add(chave)
        analise.novos.append((numero, {c: dados.get(c, "") for c in cfg["colunas"]}))
    return analise


def importar_planilha(caminho: str, tipo: str) -> Analise:
    """Importa os registros novos. Retorna a análise (novos = o que foi gravado)."""
    if tipo not in TIPOS:
        raise ErroImportacao("Tipo de cadastro inválido.")
    cfg = TIPOS[tipo]
    if not tem_permissao(cfg["permissao"]):
        raise ErroImportacao(f"Você não tem permissão para importar {cfg['rotulo'].lower()}.")
    analise = analisar_planilha(caminho, tipo)
    if not analise.novos:
        return analise

    session = get_session()
    try:
        for _, dados in analise.novos:
            registro = {"nome": dados["nome"]}
            if tipo == "fornecedores":
                registro["contato"] = dados.get("contato") or None
            session.add(cfg["modelo"](**registro))
        registrar_auditoria(
            session, "IMPORTAÇÃO", tipo,
            f"Importação de planilha ({cfg['rotulo']}): {len(analise.novos)} adicionado(s), "
            f"{len(analise.duplicados)} duplicado(s) ignorado(s), {len(analise.rejeitados)} rejeitado(s).",
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return analise
