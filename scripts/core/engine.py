#!/usr/bin/env python
"""
Engine Layer — camada única de lógica para build, teste e release.

Uso:
    from scripts.core.engine import Engine
    engine = Engine()
    engine.build(release=True)
    engine.test()
    engine.release(publish=True)

Comandos disponíveis:
    engine.build(release=False)     # build ou build+installer
    engine.test(module="all")       # smoke test
    engine.release(publish=False)   # release (dry-run ou publish)
    engine.rollback(tag, reason)    # rollback
    engine.rebuild()                # full rebuild
    engine.health()                 # health check
    engine.score()                  # release score
    engine.diagnose()               # self-diagnostic
    engine.fingerprint()            # env fingerprint
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

from scripts.core.config_release import PATHS, THRESHOLDS, get_version


class EngineError(Exception):
    """Erro base da engine."""
    def __init__(self, message, category="UNKNOWN"):
        super().__init__(message)
        self.category = category


def _run(cmd, cwd=None, capture=False):
    print(f"> {cmd}")
    kwargs = {"shell": True, "cwd": cwd or PROJECT_ROOT}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        from scripts.core.error_classifier import classify_error
        category = classify_error(cmd, "BUILD")
        raise EngineError(f"Comando falhou (exit {result.returncode}): {cmd}", category)
    return result


def _run_py(script_path, *args):
    cmd = f"{sys.executable} {script_path}"
    if args:
        cmd += " " + " ".join(str(a) for a in args)
    return _run(cmd)


class Engine:
    """Engine central do Central de Gestão."""

    def build(self, release=False):
        """Build completo. Se release=True, gera instalador."""
        flag = "--release" if release else ""
        _run_py(SCRIPTS_DIR / "build" / "build_release.py", flag)

    def test(self, module="all"):
        """Smoke test suite."""
        flag = f"--module {module}" if module != "all" else ""
        _run_py(SCRIPTS_DIR / "tests" / "smoke_test.py", flag)

    def release(self, publish=False):
        """Release automation."""
        if publish:
            _run_py(SCRIPTS_DIR / "release" / "create_release.py", "--publish")
        else:
            _run_py(SCRIPTS_DIR / "release" / "create_release.py")

    def rollback(self, tag, reason=""):
        """Rollback de release."""
        _run_py(SCRIPTS_DIR / "release" / "rollback_release.py", tag, reason)

    def rebuild(self):
        """Full rebuild from scratch."""
        _run_py(SCRIPTS_DIR / "release" / "full_rebuild.py")

    def health(self):
        """Health check."""
        _run_py(SCRIPTS_DIR / "tests" / "release_health_check.py")

    def score(self):
        """Release score."""
        _run_py(SCRIPTS_DIR / "release" / "release_score.py")

    def fingerprint(self):
        """Environment fingerprint."""
        _run_py(SCRIPTS_DIR / "build" / "env_fingerprint.py", "--save")

    def diagnose(self):
        """Self-diagnostic completo."""
        print(f"\n{'=' * 60}")
        print(f"  DIAGNOSE - Central de Gestao")
        print(f"{'=' * 60}")

        checks = []

        # 1. Versão
        try:
            v = get_version()
            checks.append(("versao", True, v))
        except Exception as e:
            checks.append(("versao", False, str(e)))

        # 2. Scripts existem
        required_scripts = [
            "scripts/build/build_release.py",
            "scripts/build/version.py",
            "scripts/build/env_fingerprint.py",
            "scripts/build/bump_version.py",
            "scripts/tests/smoke_test.py",
            "scripts/tests/validate_installer.py",
            "scripts/tests/release_health_check.py",
            "scripts/release/create_release.py",
            "scripts/release/rollback_release.py",
            "scripts/release/full_rebuild.py",
            "scripts/release/replay_release.py",
            "scripts/release/release_score.py",
            "scripts/ops/control_panel.py",
            "scripts/core/engine.py",
            "scripts/core/config_release.py",
            "scripts/core/error_classifier.py",
            "scripts/guards/constitution_rules.py",
            "scripts/guards/pre_commit_rules.py",
        ]
        scripts_ok = True
        for s in required_scripts:
            if not (PROJECT_ROOT / s).exists():
                checks.append((f"script:{s}", False, "AUSENTE"))
                scripts_ok = False
        if scripts_ok:
            checks.append(("scripts", True, f"{len(required_scripts)} scripts OK"))

        # 3. Dependências
        try:
            import PySide6
            from PySide6 import QtCore
            checks.append(("pyside6", True, f"{PySide6.__version__} / Qt {QtCore.qVersion()}"))
        except Exception as e:
            checks.append(("pyside6", False, str(e)))

        # 4. CI workflows
        ci_files = list((PROJECT_ROOT / ".github" / "workflows").glob("*.yml"))
        checks.append(("ci", True, f"{len(ci_files)} workflow(s)"))

        # 5. Docs
        doc_files = list((PROJECT_ROOT / "docs").rglob("*.md"))
        checks.append(("docs", True, f"{len(doc_files)} documento(s)"))

        # 6. Build artifacts (se existirem)
        if PATHS["bundle_dir"].exists():
            checks.append(("bundle", True, "presente"))
        else:
            checks.append(("bundle", True, "ausente (normal se nunca buildou)"))

        if PATHS["installer_path"].exists():
            size = PATHS["installer_path"].stat().st_size / (1024 * 1024)
            checks.append(("instalador", True, f"{size:.0f} MB"))
        else:
            checks.append(("instalador", True, "ausente (normal)"))

        for name, ok, detail in checks:
            icon = "[OK]" if ok else "[ERRO]"
            print(f"  {icon} {name}: {detail}")

        all_ok = all(ok for _, ok, _ in checks)
        status = "OK" if all_ok else "COM PROBLEMAS"
        print(f"\n  Diagnostico: {status}")
        return all_ok
