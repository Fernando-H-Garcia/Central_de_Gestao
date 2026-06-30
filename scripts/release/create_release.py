#!/usr/bin/env python
"""
Release Automation Script — comando único para gerar e publicar release.

Uso:
    python scripts/release/create_release.py                 # build + validação local
    python scripts/release/create_release.py --publish       # build + tag + release no GitHub
    python scripts/release/create_release.py --dry-run       # build + testes, NÃO publica

Fluxo:
    1. Lê versão de scripts/build/version.py
    2. Valida ambiente
    3. Executa build_release.py --release
    4. Executa smoke_test.py
    5. Executa validate_installer.py
    6. Se --publish: cria tag git + release no GitHub
    7. Se --dry-run: faz tudo menos publicar
"""

import sys
import subprocess
import argparse
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
    return result


def run_py(cmd):
    return run(f"python {cmd}")


def get_version():
    sys.path.insert(0, str(SCRIPTS_DIR / "build"))
    try:
        from version import VERSION, full_build
        print(f"  Versao: {VERSION}")
        return VERSION
    except ImportError:
        print("[ERRO] Nao foi possivel ler scripts/build/version.py")
        sys.exit(1)


def validate_deps():
    """Verifica dependências necessárias."""
    result = subprocess.run(["gh", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        print("[AVISO] gh CLI nao encontrado. '--publish' nao funcionara.")
        print("  Instale: winget install GitHub.cli && gh auth login")
        return False
    print(f"  gh: {result.stdout.split(chr(10))[0].strip()}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Release Automation do Central de Gestao")
    parser.add_argument("--publish", action="store_true", help="Publica release no GitHub (cria tag + release)")
    parser.add_argument("--dry-run", action="store_true", help="Simula release: build + testes, NAO publica")
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"  CENTRAL DE GESTAO - RELEASE AUTOMATION")
    print(f"{'=' * 60}")

    version = get_version()
    has_gh = validate_deps()

    if args.dry_run:
        print("\n  >>> DRY RUN: build + testes sem publicacao <<<\n")

    step("1/6 Build + Instalador")
    run_py(f"{SCRIPTS_DIR / 'build' / 'build_release.py'} --release")

    step("2/6 Smoke Test Suite")
    run_py(f"{SCRIPTS_DIR / 'tests' / 'smoke_test.py'}")

    step("3/6 Validacao do Instalador")
    run_py(f"{SCRIPTS_DIR / 'tests' / 'validate_installer.py'}")

    if args.dry_run:
        print(f"\n  >>> DRY RUN CONCLUIDO <<<")
        print(f"  Versao:  v{version}")
        print(f"  Bundle:  build/dist/CentralDeGestao/")
        print(f"  Install: build/CentralDeGestao_Installer.exe")
        print(f"  Para publicar: python scripts/release/create_release.py --publish")
        sys.exit(0)

    if not args.publish:
        step("4/6 Publicacao (PULAR — use --publish para publicar)")
        print("  Release construida e validada localmente.")
        print(f"  Para publicar: python scripts/release/create_release.py --publish")
        print(f"\nResumo:")
        print(f"  Versao:  v{version}")
        print(f"  Bundle:  build/dist/CentralDeGestao/")
        print(f"  Install: build/CentralDeGestao_Installer.exe")
        sys.exit(0)

    if not has_gh:
        print("[ERRO] gh CLI necessario para publicar. Instale e tente novamente.")
        sys.exit(1)

    step("4/6 Tag Git")
    tag = f"v{version}"
    run(f"git tag -a {tag} -m 'Release {tag}'")
    run(f"git push origin {tag}")

    step("5/6 GitHub Release")
    installer = PROJECT_ROOT / "build" / "CentralDeGestao_Installer.exe"
    if installer.exists():
        run(f'gh release create {tag} "{installer}" --title "Central de Gestao {tag}" --notes "Release {tag}"')
    else:
        run(f'gh release create {tag} --title "Central de Gestao {tag}" --notes "Release {tag}"')

    step("6/6 Push main")
    run("git push origin main")

    print(f"\n{'=' * 60}")
    print(f"  RELEASE v{version} PUBLICADA COM SUCESSO!")
    print(f"{'=' * 60}")
    print(f"  Tag:  {tag}")
    print(f"  URL:  https://github.com/Fernando-H-Garcia/Central_de_Gestao/releases/tag/{tag}")


if __name__ == "__main__":
    main()
