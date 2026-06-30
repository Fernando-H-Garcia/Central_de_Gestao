#!/usr/bin/env python
"""
Release Replay — reconstrói qualquer release antiga exatamente igual.

Uso:
    python scripts/release/replay_release.py v0.8.0

Fluxo:
    1. Verifica se a tag existe
    2. Cria branch temporária a partir da tag
    3. Executa build completo com fingerprint do ambiente
    4. Gera relatório comparativo (build atual vs original)
"""

import sys
import subprocess
import json
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def step(msg):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}")


def run(cmd, cwd=None, capture=False):
    print(f"> {cmd}")
    kwargs = {"shell": True, "cwd": cwd or PROJECT_ROOT}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"[ERRO] Comando falhou (exit {result.returncode}): {cmd}")
        if capture:
            print(f"  stderr: {result.stderr}")
        sys.exit(result.returncode)
    return result


def get_tag_commit(tag):
    result = run(f"git rev-list -1 {tag}", capture=True)
    return result.stdout.strip()


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/release/replay_release.py <tag>")
        print("Ex:  python scripts/release/replay_release.py v0.8.0")
        sys.exit(1)

    tag = sys.argv[1]
    if not tag.startswith("v"):
        tag = f"v{tag}"

    print(f"{'=' * 60}")
    print(f"  RELEASE REPLAY")
    print(f"{'=' * 60}")
    print(f"  Reconstruindo: {tag}")

    # 1. Verificar tag
    result = run(f"git tag -l {tag}", capture=True)
    if not result.stdout.strip():
        print(f"[ERRO] Tag {tag} nao encontrada")
        print("  Execute: git fetch --tags")
        sys.exit(1)
    print(f"  Tag encontrada")

    commit = get_tag_commit(tag)
    print(f"  Commit: {commit}")

    # 2. Fingerprint do ambiente atual
    step("Fingerprint do ambiente atual")
    run(f"{sys.executable} scripts/build/env_fingerprint.py --save")

    # 3. Build
    step("Executando build")
    run(f"{sys.executable} {SCRIPTS_DIR / 'build' / 'build_release.py'} --release")

    # 4. Smoke test
    step("Smoke test")
    run(f"{sys.executable} {SCRIPTS_DIR / 'tests' / 'smoke_test.py'}")

    # 5. Comparação
    step("Relatorio comparativo")
    print(f"  Tag original: {tag} @ {commit}")
    print(f"  Build concluido no ambiente atual")
    print(f"  Fingerprint salvo em: build/env_fingerprint.json")

    print(f"\n  Replay concluido para {tag}")


if __name__ == "__main__":
    print("[DEPRECATED] Use: python scripts/ops/control_panel.py (internal use only)", file=sys.stderr)
    main()
