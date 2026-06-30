#!/usr/bin/env python
"""
Release Automation Script — entry point oficial #2.

Delega para engine.py internamente.

Uso:
    python scripts/release/create_release.py                 # build + validação local
    python scripts/release/create_release.py --publish       # build + tag + release no GitHub
    python scripts/release/create_release.py --dry-run       # build + testes, NÃO publica
"""

import sys
import subprocess
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.engine import Engine, _run_py


def get_version():
    from scripts.core.config_release import get_version
    v = get_version()
    print(f"  Versao: {v}")
    return v


def validate_deps():
    result = subprocess.run(["gh", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        print("[AVISO] gh CLI nao encontrado. '--publish' nao funcionara.")
        print("  Instale: winget install GitHub.cli && gh auth login")
        return False
    print(f"  gh: {result.stdout.split(chr(10))[0].strip()}")
    return True


def step(msg):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="Release Automation do Central de Gestao")
    parser.add_argument("--publish", action="store_true", help="Publica release no GitHub")
    parser.add_argument("--dry-run", action="store_true", help="Simula release")
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"  CENTRAL DE GESTAO - RELEASE AUTOMATION")
    print(f"{'=' * 60}")

    version = get_version()
    has_gh = validate_deps()
    engine = Engine()

    if args.dry_run:
        print("\n  >>> DRY RUN: build + testes sem publicacao <<<\n")

    step("1/6 Build + Instalador")
    engine.build(release=True)

    step("2/6 Smoke Test Suite")
    engine.test()

    step("3/6 Validacao do Instalador")
    _run_py(PROJECT_ROOT / "scripts" / "tests" / "validate_installer.py")

    if args.dry_run:
        print(f"\n  >>> DRY RUN CONCLUIDO <<<")
        print(f"  Versao:  v{version}")
        print(f"  Bundle:  build/dist/CentralDeGestao/")
        print(f"  Install: build/CentralDeGestao_Installer.exe")
        print(f"  Para publicar: python scripts/release/create_release.py --publish")
        sys.exit(0)

    if not args.publish:
        step("4/6 Publicacao (PULAR)")
        print("  Release construida e validada localmente.")
        print(f"  Para publicar: python scripts/release/create_release.py --publish")
        print(f"\nResumo:")
        print(f"  Versao:  v{version}")
        print(f"  Bundle:  build/dist/CentralDeGestao/")
        print(f"  Install: build/CentralDeGestao_Installer.exe")
        sys.exit(0)

    if not has_gh:
        print("[ERRO] gh CLI necessario para publicar.")
        sys.exit(1)

    step("4/6 Tag Git")
    tag = f"v{version}"
    subprocess.run(f"git tag -a {tag} -m 'Release {tag}'", shell=True, cwd=PROJECT_ROOT).check_returncode()
    subprocess.run(f"git push origin {tag}", shell=True, cwd=PROJECT_ROOT).check_returncode()

    step("5/6 GitHub Release")
    installer = PROJECT_ROOT / "build" / "CentralDeGestao_Installer.exe"
    if installer.exists():
        subprocess.run(f'gh release create {tag} "{installer}" --title "Central de Gestao {tag}" --notes "Release {tag}"', shell=True, cwd=PROJECT_ROOT).check_returncode()
    else:
        subprocess.run(f'gh release create {tag} --title "Central de Gestao {tag}" --notes "Release {tag}"', shell=True, cwd=PROJECT_ROOT).check_returncode()

    step("6/6 Push main")
    subprocess.run("git push origin main", shell=True, cwd=PROJECT_ROOT).check_returncode()

    print(f"\n{'=' * 60}")
    print(f"  RELEASE v{version} PUBLICADA COM SUCESSO!")
    print(f"{'=' * 60}")
    print(f"  Tag:  {tag}")
    print(f"  URL:  https://github.com/Fernando-H-Garcia/Central_de_Gestao/releases/tag/{tag}")


if __name__ == "__main__":
    main()
