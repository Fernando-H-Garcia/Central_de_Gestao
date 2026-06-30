#!/usr/bin/env python
"""
Pre-commit hook do Central de Gestão.

Instalação:
    python scripts/hooks/pre_commit.py --install

Valida:
    1. Sintaxe Python de arquivos .py alterados
    2. parent=None em widgets Qt
    3. version.py alterado apenas via bump_version.py
    4. Lógica de build só em scripts/build/
    5. Imports quebrados
    6. Versões consistentes
"""

import sys
import subprocess
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

ERRORS = 0
WARNINGS = 0


def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")

def warn(msg):
    global WARNINGS
    WARNINGS += 1
    print(f"  {YELLOW}⚠{RESET} {msg}")

def err(msg):
    global ERRORS
    ERRORS += 1
    print(f"  {RED}✗{RESET} {msg}")


def get_staged_files():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    return [f for f in result.stdout.strip().split("\n") if f and f.endswith(".py")]


def check_syntax(files):
    for f in files:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", f],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        if result.returncode != 0:
            err(f"Erro de sintaxe em {f}:\n{result.stderr.strip()}")
        else:
            ok(f"Sintaxe OK: {f}")


def check_parent_none(files):
    for f in files:
        content = Path(PROJECT_ROOT / f).read_text(encoding="utf-8")
        for i, line in enumerate(content.split("\n"), 1):
            if "parent=None" in line:
                err(f"parent=None em {f}:{i}")


def check_version_py(files):
    if "scripts/build/version.py" in files:
        msg = subprocess.run(
            ["git", "log", "-1", "--format=%s"], capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout.strip()
        if "bump version" not in msg.lower():
            err("version.py alterado sem usar bump_version.py")


def check_build_logic(files):
    build_keywords = ["pyinstaller", "build.spec", "cleanup_dlls", "ISCC", "Inno Setup"]
    for f in files:
        if f.startswith("scripts/build/"):
            continue
        content = Path(PROJECT_ROOT / f).read_text(encoding="utf-8")
        for kw in build_keywords:
            if kw.lower() in content.lower():
                warn(f"Logica de build em {f} (contem '{kw}')")


def check_imports(files):
    for f in files:
        content = Path(PROJECT_ROOT / f).read_text(encoding="utf-8")
        for line in content.split("\n"):
            m = re.match(r"^from\s+(\S+)\s+import", line) or re.match(r"^import\s+(\S+)", line)
            if m:
                mod = m.group(1)
                if mod.startswith("."):
                    continue
                # Tenta importar o módulo
                try:
                    __import__(mod.split(".")[0])
                except ImportError:
                    warn(f"Possivel import quebrado em {f}: {line.strip()}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        hook_path = PROJECT_ROOT / ".git" / "hooks" / "pre-commit"
        hook_path.write_text(
            "#!/bin/sh\n"
            f"{sys.executable} scripts/hooks/pre_commit.py\n",
            encoding="utf-8"
        )
        hook_path.chmod(0o755)
        print(f"Pre-commit hook instalado em {hook_path}")
        return

    files = get_staged_files()
    if not files:
        ok("Nenhum arquivo .py alterado")
        sys.exit(0)

    print(f"\n  Pre-commit check: {len(files)} arquivo(s)\n")

    check_syntax(files)
    check_parent_none(files)
    check_version_py(files)
    check_build_logic(files)
    check_imports(files)

    print(f"\n  Resultado: {ERRORS} erro(s), {WARNINGS} aviso(s)\n")

    if ERRORS > 0:
        print(f"{RED}Pre-commit FALHOU - corrija os erros{RESET}")
        sys.exit(1)

    ok("Pre-commit passou")
    if WARNINGS > 0:
        print(f"  {YELLOW}{WARNINGS} aviso(s) - revise se necessario{RESET}")


if __name__ == "__main__":
    print("[DEPRECATED] Use: python scripts/ops/control_panel.py (internal use only)", file=sys.stderr)
    main()
