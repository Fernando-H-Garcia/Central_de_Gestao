#!/usr/bin/env python
"""
Rollback de release do Central de Gestão.

Uso:
    python scripts/release/rollback_release.py v0.7.0 "motivo do rollback"

Fluxo:
    1. Valida que a tag existe
    2. Deleta a tag no GitHub
    3. Invalida a release (adiciona nota de rollback)
    4. Restaura versão anterior da tag
    5. Loga o motivo
"""

import sys
import subprocess
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REPO = "Fernando-H-Garcia/Central_de_Gestao"


def run(cmd, capture=False):
    print(f"> {cmd}")
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    else:
        result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"[ERRO] Comando falhou: {cmd}")
        if capture:
            print(f"  stderr: {result.stderr}")
        sys.exit(result.returncode)
    return result


def get_previous_tag(current_tag):
    result = run("git tag --sort=-creatordate", capture=True)
    tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
    try:
        idx = tags.index(current_tag)
        if idx + 1 < len(tags):
            return tags[idx + 1]
    except ValueError:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="Rollback de release do Central de Gestao")
    parser.add_argument("tag", help="Tag a ser revertida (ex: v0.7.0)")
    parser.add_argument("reason", nargs="?", default="Nao informado", help="Motivo do rollback")
    args = parser.parse_args()

    tag = args.tag if args.tag.startswith("v") else f"v{args.tag}"
    reason = args.reason

    print(f"{'=' * 60}")
    print(f"  ROLLBACK RELEASE")
    print(f"{'=' * 60}")
    print(f"  Tag:    {tag}")
    print(f"  Motivo: {reason}")
    print(f"{'=' * 60}")

    # 1. Validar que a tag existe
    result = run(f"git tag -l {tag}", capture=True)
    if not result.stdout.strip():
        print(f"[ERRO] Tag {tag} nao encontrada localmente")
        print("  Execute: git fetch --tags")
        sys.exit(1)
    print(f"  Tag {tag} encontrada")

    # 2. Encontrar tag anterior
    prev_tag = get_previous_tag(tag)
    if prev_tag:
        print(f"  Tag anterior: {prev_tag}")
    else:
        print(f"  [AVISO] Nenhuma tag anterior encontrada")

    # 3. Deletar release no GitHub
    print(f"\n  Deletando release {tag} no GitHub...")
    run(f'gh release delete {tag} --yes --cleanup-tag')

    # 4. Criar nota de rollback
    print(f"\n  Criando nota de rollback...")
    notes = f"## ROLLBACK da release {tag}\n\n**Motivo**: {reason}\n\n**Data**: TODO\n\nEsta release foi revertida."
    run(f'gh release create {tag} --title "ROLLBACK {tag}" --notes "{notes}" --prerelease')

    print(f"\n  Rollback concluido para {tag}")
    if prev_tag:
        print(f"  Versao anterior disponivel: {prev_tag}")
    print(f"  URL: https://github.com/{REPO}/releases/tag/{tag}")


if __name__ == "__main__":
    main()
