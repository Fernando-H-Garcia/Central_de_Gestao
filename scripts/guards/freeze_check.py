#!/usr/bin/env python
"""Feature Freeze Mode — bloqueia novas features quando ativo."""

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

ALLOWED_IN_FREEZE = ["FIX", "BUILD", "chore", "docs", "fix"]


def is_frozen():
    """Verifica se FREEZE_MODE está ativo (variável de ambiente ou arquivo)."""
    import os
    return os.environ.get("FREEZE_MODE", "").lower() == "true"


def check_commit(msg=None):
    """Valida se o commit é permitido durante freeze."""
    if not is_frozen():
        return []

    if msg is None:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        msg = result.stdout.strip()

    for prefix in ALLOWED_IN_FREEZE:
        if msg.startswith(prefix):
            return []

    return [f"FREEZE MODE: commit bloqueado: {msg}"]
