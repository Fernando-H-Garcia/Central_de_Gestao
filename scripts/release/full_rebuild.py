#!/usr/bin/env python
"""
Full Rebuild — limpa tudo e reconstrói do zero.

Uso:
    python scripts/release/full_rebuild.py

Fluxo:
    1. Limpa artefatos (dist, build_pyi, __pycache__)
    2. Valida ambiente
    3. Build completo (PyInstaller)
    4. Valida bundle (Build Contract)
    5. Gera instalador
    6. Smoke test
    7. Valida instalador
    8. Health check
    9. Relatório final
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def step(msg):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}")


def run(cmd, cwd=None):
    print(f"> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or PROJECT_ROOT)
    if result.returncode != 0:
        print(f"[FATAL] Comando falhou (exit {result.returncode}): {cmd}")
        sys.exit(result.returncode)


def run_py(path):
    run(f"python {path}")


def clean_deep():
    """Limpeza profunda: cache, pycache, artefatos."""
    step("Limpando artefatos")
    dirs_to_remove = [
        PROJECT_ROOT / "build" / "dist",
        PROJECT_ROOT / "build" / "build_pyi",
    ]
    for d in dirs_to_remove:
        if d.exists():
            import shutil
            shutil.rmtree(d, ignore_errors=True)
            print(f"  Removido: {d}")

    # __pycache__ em toda a árvore
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        import shutil
        shutil.rmtree(pycache, ignore_errors=True)
        print(f"  Removido: {pycache}")

    # *.spec na raiz
    for f in PROJECT_ROOT.glob("*.spec"):
        f.unlink(missing_ok=True)
        print(f"  Removido: {f}")


def main():
    print(f"{'=' * 60}")
    print(f"  FULL REBUILD - Central de Gestao")
    print(f"{'=' * 60}")

    clean_deep()

    step("Build + Instalador")
    run_py(f"{SCRIPTS_DIR / 'build' / 'build_release.py'} --release")

    step("Smoke Test")
    run_py(f"{SCRIPTS_DIR / 'tests' / 'smoke_test.py'}")

    step("Validacao do Instalador")
    run_py(f"{SCRIPTS_DIR / 'tests' / 'validate_installer.py'}")

    step("Health Check")
    run_py(f"{SCRIPTS_DIR / 'tests' / 'release_health_check.py'}")

    print(f"\n{'=' * 60}")
    print(f"  FULL REBUILD CONCLUIDO")
    print(f"{'=' * 60}")
    print(f"  Bundle:  build/dist/CentralDeGestao/")
    print(f"  Install: build/CentralDeGestao_Installer.exe")
    print(f"  Report:  build/build_report.txt")


if __name__ == "__main__":
    main()
