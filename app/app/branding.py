import sys
from pathlib import Path

APP_VERSION = "1.0.1"
APP_OWNER = "Rafael Oliveira de Jesus"
APP_CONTACT_EMAIL = "rafaelentele@gmail.com"

def asset_path(nome: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / "assets" / nome
