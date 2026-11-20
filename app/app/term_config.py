"""Configurações dos modelos de termo de responsabilidade."""
import json
import sys
from pathlib import Path


def data_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def settings_path():
    return data_dir() / "configuracoes_sistema.json"


def _modelo_padrao():
    return {
        "id": "termo_padrao",
        "nome": "Termo Padrão - EPI e Fardamento",
        "nome_empresa": "Empresa",
        "titulo": "TERMO DE RESPONSABILIDADE",
        "texto_abertura": "Recebi da empresa {empresa}, gratuitamente, para uso exclusivo no desempenho de minhas atividades na empresa, conforme determinado em lei, os equipamentos relacionados neste termo de responsabilidade.",
        "texto_compromisso": "Comprometo-me a usar e mantê-lo em perfeito estado de conservação, ficando ainda ciente de:",
        "clausulas": [],
        "ativo": True,
    }


def _normalizar_modelo(modelo, indice=0):
    base = _modelo_padrao()
    base.update(modelo or {})
    if not base.get("id"):
        base["id"] = f"modelo_{indice + 1}"
    if not base.get("nome"):
        base["nome"] = f"Modelo {indice + 1}"
    if not base.get("titulo"):
        base["titulo"] = "TERMO DE RESPONSABILIDADE"
    if not isinstance(base.get("clausulas"), list):
        base["clausulas"] = []
    base["ativo"] = bool(base.get("ativo", True))
    if not base.get("nome_empresa"):
        base["nome_empresa"] = "Empresa"
    return base


def _migrar_configuracao_antiga(dados):
    """Converte a configuração antiga (um único termo) para o novo formato."""
    modelo = _modelo_padrao()
    modelo.update({
        "nome": "Termo Padrão - EPI e Fardamento",
        "nome_empresa": dados.get("nome_empresa") or "Empresa",
        "titulo": dados.get("titulo_termo") or "TERMO DE RESPONSABILIDADE",
        "texto_abertura": dados.get("texto_abertura") or modelo["texto_abertura"],
        "texto_compromisso": dados.get("texto_compromisso") or modelo["texto_compromisso"],
        "clausulas": dados.get("clausulas") or [],
        "ativo": True,
    })
    return {
        "nome_empresa": dados.get("nome_empresa") or "Empresa",
        "logo_empresa": dados.get("logo_empresa") or "",
        "modelo_padrao_id": modelo["id"],
        "modelos_termo": [modelo],
    }


def carregar_configuracoes():
    padrao_antigo = {
        "nome_empresa": "Empresa",
        "texto_abertura": "Recebi da empresa {empresa}, gratuitamente, para uso exclusivo no desempenho de minhas atividades na empresa, conforme determinado em lei, os equipamentos relacionados neste termo de responsabilidade.",
        "texto_compromisso": "Comprometo-me a usar e mantê-lo em perfeito estado de conservação, ficando ainda ciente de:",
        "clausulas": [],
        "logo_empresa": "",
    }
    try:
        dados = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        dados = padrao_antigo

    # Compatibilidade com configurações antigas.
    if not isinstance(dados.get("modelos_termo"), list) or not dados.get("modelos_termo"):
        dados = _migrar_configuracao_antiga({**padrao_antigo, **dados})

    dados["modelos_termo"] = [
        _normalizar_modelo(modelo, i) for i, modelo in enumerate(dados.get("modelos_termo", []))
    ]

    ids = {m["id"] for m in dados["modelos_termo"]}
    if dados.get("modelo_padrao_id") not in ids:
        dados["modelo_padrao_id"] = dados["modelos_termo"][0]["id"]

    # Campos antigos ficam disponíveis para compatibilidade com versões anteriores.
    modelo_padrao = obter_modelo(dados, dados["modelo_padrao_id"])
    dados["texto_abertura"] = modelo_padrao.get("texto_abertura", "")
    dados["texto_compromisso"] = modelo_padrao.get("texto_compromisso", "")
    dados["clausulas"] = modelo_padrao.get("clausulas", [])
    dados["titulo_termo"] = modelo_padrao.get("titulo", "TERMO DE RESPONSABILIDADE")
    return dados


def salvar_configuracoes(dados):
    settings_path().write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def obter_modelo(dados, modelo_id=None):
    modelos = dados.get("modelos_termo") or []
    if modelo_id:
        for modelo in modelos:
            if modelo.get("id") == modelo_id:
                return modelo
    for modelo in modelos:
        if modelo.get("id") == dados.get("modelo_padrao_id") and modelo.get("ativo", True):
            return modelo
    for modelo in modelos:
        if modelo.get("ativo", True):
            return modelo
    return modelos[0] if modelos else _modelo_padrao()


def modelos_ativos(dados):
    return [m for m in dados.get("modelos_termo", []) if m.get("ativo", True)]


def novo_id_modelo(modelos):
    usados = {str(m.get("id")) for m in modelos}
    numero = 1
    while f"modelo_{numero}" in usados:
        numero += 1
    return f"modelo_{numero}"
