#!/usr/bin/env python
"""
Central de Gestão - Control Panel (CLI oficial)

Uso:
    python scripts/ops/control_panel.py <command> [options]

Comandos:
    build [--release]        Build ou build + instalador
    test [--module <name>]   Smoke test suite
    release [--publish]      Release (dry-run ou publish)
    rollback <tag> [reason]  Rollback de release
    rebuild                  Full rebuild from scratch
    health                   Health check
    score                    Release score
    diagnose                 Self-diagnostic completo
    fingerprint              Environment fingerprint
    bump <patch|minor|major> Bump versão

Exemplos:
    python scripts/ops/control_panel.py build --release
    python scripts/ops/control_panel.py test --module banco
    python scripts/ops/control_panel.py release --publish
    python scripts/ops/control_panel.py rollback v0.7.0 "motivo"
    python scripts/ops/control_panel.py diagnose
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.engine import Engine


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    engine = Engine()
    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "build":        lambda: engine.build(release="--release" in args),
        "test":         lambda: engine.test(module=_get_arg(args, "--module", "all")),
        "release":      lambda: engine.release(publish="--publish" in args),
        "rollback":     lambda: engine.rollback(args[0], " ".join(args[1:]) if len(args) > 1 else ""),
        "rebuild":      lambda: engine.rebuild(),
        "health":       lambda: engine.health(),
        "score":        lambda: engine.score(),
        "diagnose":     lambda: engine.diagnose(),
        "fingerprint":  lambda: engine.fingerprint(),
    }

    # Comandos que não passam pela engine
    direct = {
        "bump":         _script_path("build/bump_version.py"),
    }

    if command in commands:
        commands[command]()
    elif command in direct:
        import subprocess
        cmd = f"{sys.executable} {direct[command]}" + (" " + " ".join(args) if args else "")
        subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT)
    else:
        print(f"Comando desconhecido: {command}")
        print(__doc__)
        sys.exit(1)


def _get_arg(args, flag, default):
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
    return default


def _script_path(rel):
    return PROJECT_ROOT / "scripts" / rel


if __name__ == "__main__":
    main()
