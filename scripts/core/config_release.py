#!/usr/bin/env python
"""Configuração centralizada de release do Central de Gestão."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ---- Paths absolutos --------------------------------------------------------
PATHS = {
    "build_dir": PROJECT_ROOT / "build",
    "dist_dir": PROJECT_ROOT / "build" / "dist",
    "bundle_dir": PROJECT_ROOT / "build" / "dist" / "CentralDeGestao",
    "internal_dir": PROJECT_ROOT / "build" / "dist" / "CentralDeGestao" / "_internal",
    "installer_path": PROJECT_ROOT / "build" / "CentralDeGestao_Installer.exe",
    "build_report": PROJECT_ROOT / "build" / "build_report.txt",
    "build_hash": PROJECT_ROOT / "build" / "build.hash",
    "health_report": PROJECT_ROOT / "build" / "health_report.json",
    "fingerprint": PROJECT_ROOT / "build" / "env_fingerprint.json",
}

# ---- Thresholds -------------------------------------------------------------
THRESHOLDS = {
    "min_exe_size_mb": 30,
    "min_installer_size_mb": 50,
    "smoke_timeout_seconds": 15,
    "release_score_min": 50,
    "health_score_min": 80,
}

# ---- Plugins Qt obrigatórios ------------------------------------------------
QT_PLUGINS = ["platforms", "sqldrivers", "styles", "imageformats"]

# ---- Recursos obrigatórios no bundle ----------------------------------------
BUNDLE_RESOURCES = ["database/migrations", "config", "attachments"]

# ---- Versão (delegate para version.py) --------------------------------------
def get_version():
    import sys
    sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "build"))
    from version import VERSION
    return VERSION

def get_version_short():
    return ".".join(get_version().split(".")[:2])
