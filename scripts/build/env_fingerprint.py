#!/usr/bin/env python
"""
Environment Fingerprint — registra ambiente exato do build.

Uso:
    python scripts/build/env_fingerprint.py
    python scripts/build/env_fingerprint.py --save  # salva em build/env_fingerprint.json
"""

import sys
import platform
import subprocess
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_pip_freeze():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def fingerprint(save=False):
    fp = {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "os": platform.platform(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
    }

    # PySide6
    try:
        import PySide6
        from PySide6 import QtCore
        fp["pyside6_version"] = PySide6.__version__
        fp["qt_version"] = QtCore.qVersion()
    except ImportError:
        fp["pyside6_version"] = "N/A"
        fp["qt_version"] = "N/A"

    # PyInstaller
    try:
        import PyInstaller
        fp["pyinstaller_version"] = PyInstaller.__version__
    except ImportError:
        fp["pyinstaller_version"] = "N/A"

    # Pip freeze (hash)
    freeze = get_pip_freeze()
    import hashlib
    fp["pip_freeze_hash"] = hashlib.sha256(freeze.encode()).hexdigest()[:16]

    if save:
        out_path = PROJECT_ROOT / "build" / "env_fingerprint.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(fp, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Fingerprint salvo em: {out_path}")
    else:
        print(json.dumps(fp, indent=2, ensure_ascii=False))

    return fp


def main():
    save = "--save" in sys.argv
    fingerprint(save)


if __name__ == "__main__":
    main()
