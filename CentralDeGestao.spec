# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# Determinado pelo script de build via --distpath/--workpath
PROJECT_ROOT = os.getcwd()

MAIN = os.path.join(PROJECT_ROOT, "main.py")


a = Analysis(
    [MAIN],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        ("database", "database"),
        ("config", "config"),
        ("attachments", "attachments"),
    ],
    hiddenimports=[
        "PySide6",
        "PySide6.QtWidgets",
        "PySide6.QtCore",
        "PySide6.QtGui",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CentralDeGestao",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="CentralDeGestao",
)
