#!/usr/bin/env python
"""Pre-commit rules — validações para o hook pre-commit."""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def check_syntax(files):
    """Valida sintaxe Python."""
    errors = []
    for f in files:
        p = PROJECT_ROOT / f
        if not p.exists():
            continue
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(p)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            errors.append(f"Erro de sintaxe em {f}: {result.stderr.strip()[:200]}")
    return errors


def check_imports(files):
    """Verifica imports quebrados (básico)."""
    warnings = []
    for f in files:
        p = PROJECT_ROOT / f
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8")
        for line in content.split("\n"):
            m = __import__("re").match(r"^from\s+(\S+)\s+import", line)
            if not m:
                m = __import__("re").match(r"^import\s+(\S+)", line)
            if m:
                mod = m.group(1).split(".")[0]
                if not mod.startswith("."):
                    try:
                        __import__(mod)
                    except ImportError:
                        warnings.append(f"Possivel import quebrado em {f}: {line.strip()[:80]}")
    return warnings


def run_all(files):
    """Executa todas as validações."""
    errors = check_syntax(files)
    errors.extend(check_imports(files))
    return errors
