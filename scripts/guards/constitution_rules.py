#!/usr/bin/env python
"""
Constitution Rules — regras da Constituição do Projeto.

Uso:
    from scripts.guards.constitution_rules import check_all, check_rule
"""

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def check_parent_none(files):
    """Regra 2: Não usar parent=None em widgets Qt."""
    violations = []
    for f in files:
        content = Path(PROJECT_ROOT / f).read_text(encoding="utf-8")
        for i, line in enumerate(content.split("\n"), 1):
            if "parent=None" in line:
                violations.append(f"{f}:{i}")
    return violations


def check_version_py_manual(files):
    """Regra 3: Não alterar version.py manualmente (só via bump_version.py)."""
    if "scripts/build/version.py" in files:
        msg = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout.strip()
        if "bump version" not in msg.lower():
            return [f"version.py alterado sem bump_version.py: {msg}"]
    return []


def check_build_logic_outside(files):
    """Regra 4: Lógica de build só em scripts/build/."""
    keywords = ["pyinstaller", "build.spec", "cleanup_dlls", "ISCC"]
    violations = []
    for f in files:
        if f.startswith("scripts/build/") or f.startswith(".github/"):
            continue
        content = Path(PROJECT_ROOT / f).read_text(encoding="utf-8")
        for kw in keywords:
            if kw.lower() in content.lower():
                violations.append(f"{f} contem '{kw}'")
                break
    return violations


def check_commit_classification(msg):
    """Regra 5: Commit precisa de classificação."""
    types = ["FIX", "FEATURE", "REFACTOR", "BUILD", "RISKY", "BREAKING", "docs", "chore", "feat", "fix"]
    for t in types:
        if msg.startswith(t):
            return []
    return [f"Commit sem classificacao: {msg}"]


def check_all(staged_files=None, commit_msg=None):
    """Executa todas as regras."""
    if staged_files is None:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        staged_files = [f for f in result.stdout.strip().split("\n") if f]

    if commit_msg is None:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        commit_msg = result.stdout.strip()

    violations = []
    violations.extend(check_parent_none(staged_files))
    violations.extend(check_version_py_manual(staged_files))
    violations.extend(check_build_logic_outside(staged_files))
    violations.extend(check_commit_classification(commit_msg))

    return violations
