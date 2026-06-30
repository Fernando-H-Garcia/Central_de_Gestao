#!/usr/bin/env python
"""
Central de Gestão - Control Panel

Uso:
    python scripts/ops/control_panel.py <command> [options]

Comandos:
    build              Executa build completo
    build --release    Build + instalador
    test               Smoke test suite
    test --module X    Testa módulo específico
    release            Cria release (dry-run)
    release --publish  Publica release
    rollback <tag>     Reverte release
    rebuild            Full rebuild from scratch
    health             Health check da instalação
    score              Calcula release score
    bump <part>        Bump versão (patch|minor|major)
    fingerprint        Gera environment fingerprint
"""

import sys
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def run(cmd):
    print(f"> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def run_script(path, *args):
    cmd = f"{sys.executable} {path}"
    if args:
        cmd += " " + " ".join(args)
    run(cmd)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "build":         (SCRIPTS_DIR / "build" / "build_release.py", args or []),
        "test":          (SCRIPTS_DIR / "tests" / "smoke_test.py", args or []),
        "release":       (SCRIPTS_DIR / "release" / "create_release.py", args or []),
        "rollback":      (SCRIPTS_DIR / "release" / "rollback_release.py", args or []),
        "rebuild":       (SCRIPTS_DIR / "release" / "full_rebuild.py", args or []),
        "health":        (SCRIPTS_DIR / "tests" / "release_health_check.py", args or []),
        "score":         (SCRIPTS_DIR / "release" / "release_score.py", args or []),
        "bump":          (SCRIPTS_DIR / "build" / "bump_version.py", args or []),
        "fingerprint":   (SCRIPTS_DIR / "build" / "env_fingerprint.py", args or []),
    }

    if command not in commands:
        print(f"Comando desconhecido: {command}")
        print(__doc__)
        sys.exit(1)

    script_path, script_args = commands[command]
    run_script(script_path, *script_args)


if __name__ == "__main__":
    main()
