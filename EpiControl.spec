# -*- mode: python ; coding: utf-8 -*-
# Build standalone do Epi Control. Gera EpiControl.exe sem dados empresariais.
import os

APP = os.path.join(SPECPATH, "app")

hiddenimports = ["reportlab"]

a = Analysis(
    [os.path.join(APP, "app_gui.py")],
    pathex=[APP],
    binaries=[],
    datas=[
        (os.path.join(APP, "assets"), "assets"),
        (os.path.join(APP, "MANUAL_DE_INSTRUCOES.md"), "assets"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EpiControl",
    icon=os.path.join(APP, "assets", "icone_sistema.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
