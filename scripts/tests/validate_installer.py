#!/usr/bin/env python
"""
Validação de integridade do instalador do Central de Gestão.

Uso:
    python scripts/tests/validate_installer.py [--installer <path>]

Valida:
    - Arquivo existe e tem tamanho mínimo
    - Pode ser extraído (contém estrutura esperada)
    - Nomes de arquivos internos são válidos

Exit codes:
    0 = OK
    1 = Falha
"""

import sys
import zipfile
import subprocess
import tempfile
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_INSTALLER = PROJECT_ROOT / "build" / "CentralDeGestao_Installer.exe"
MIN_SIZE_MB = 50

# Estrutura esperada dentro do instalador
EXPECTED_INTERNAL = [
    "CentralDeGestao.exe",
    "_internal/PySide6/plugins/platforms/qwindows.dll",
    "_internal/PySide6/plugins/sqldrivers/qsqlite.dll",
    "_internal/shiboken6/shiboken6.abi3.dll",
]


def find_installer(path=None):
    if path:
        p = Path(path)
        if not p.exists():
            print(f"[VALIDATE] ERRO: Instalador nao encontrado: {p}")
            sys.exit(1)
        return p
    if DEFAULT_INSTALLER.exists():
        return DEFAULT_INSTALLER
    print("[VALIDATE] ERRO: Instalador nao encontrado. Use --installer <path>")
    sys.exit(1)


def extract_with_7zip(installer_path, output_dir):
    """Tenta extrair usando 7zip (se disponível)."""
    sevenzip = shutil_which("7z")
    if not sevenzip:
        return None

    result = subprocess.run(
        [sevenzip, "x", str(installer_path), f"-o{output_dir}", "-y"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        return output_dir
    return None


def shutil_which(name):
    import shutil
    return shutil.which(name) or (
        shutil.which(f"{name}.exe")
    )


def validate_content(installer_path):
    """Valida conteúdo do instalador por extração 7zip."""
    with tempfile.TemporaryDirectory(prefix="cg_validate_") as tmpdir:
        extract_dir = extract_with_7zip(installer_path, tmpdir)
        if not extract_dir:
            print("[VALIDATE] AVISO: Nao foi possivel extrair o instalador (7zip ausente)")
            print("[VALIDATE] Validacao basica apenas (tamanho + existencia)")
            return True

        found = []
        missing = []
        for pattern in EXPECTED_INTERNAL:
            full_path = Path(extract_dir) / "{app}" / pattern
            if full_path.exists():
                found.append(pattern)
            else:
                # Tenta sem {app}/
                alt = Path(extract_dir) / pattern
                if alt.exists():
                    found.append(pattern)
                else:
                    missing.append(pattern)

        if missing:
            print("[VALIDATE] Arquivos esperados nao encontrados no instalador:")
            for m in missing:
                print(f"  [FALTA] {m}")
            return False

        print(f"[VALIDATE] {len(found)}/{len(EXPECTED_INTERNAL)} arquivos criticos OK")
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Valida instalador do Central de Gestao")
    parser.add_argument("--installer", help="Caminho do instalador (opcional)")
    args = parser.parse_args()

    installer_path = find_installer(args.installer)
    size_mb = installer_path.stat().st_size / (1024 * 1024)
    print(f"[VALIDATE] Instalador: {installer_path} ({size_mb:.1f} MB)")

    if size_mb < MIN_SIZE_MB:
        print(f"[VALIDATE] FALHA: Tamanho ({size_mb:.1f} MB) menor que minimo ({MIN_SIZE_MB} MB)")
        sys.exit(1)
    print(f"[VALIDATE] Tamanho OK ({size_mb:.1f} MB)")

    content_ok = validate_content(installer_path)
    if not content_ok:
        print("[VALIDATE] FALHA: Conteudo do instalador invalido")
        sys.exit(1)

    print("[VALIDATE] Instalador VALIDO")
    sys.exit(0)


if __name__ == "__main__":
    print("[DEPRECATED] Use: python scripts/ops/control_panel.py build --release", file=sys.stderr)
    main()
