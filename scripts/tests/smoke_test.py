#!/usr/bin/env python
"""
Smoke Test Suite para Central de Gestão.

Uso:
    python scripts/tests/smoke_test.py                      # todos os módulos
    python scripts/tests/smoke_test.py --module core        # apenas core
    python scripts/tests/smoke_test.py --module banco       # apenas banco

Módulos:
    - core:     executável abre sem crash
    - banco:    SQLite conecta, migrations executam
    - config:   configurações carregam
    - anexos:   diretório de anexos acessível

Exit codes:
    0 = todos os módulos OK
    1 = algum módulo falhou
"""

import sys
import subprocess
import time
import sqlite3
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_EXE = PROJECT_ROOT / "build" / "dist" / "CentralDeGestao.exe"
TIMEOUT = 15
LOCALAPPDATA = Path.home() / "AppData" / "Local" / "CentralGestao"

RESULTS = []


def test(name, ok, detail=""):
    RESULTS.append({"module": name, "ok": ok, "detail": detail})
    icon = "✅" if ok else "❌"
    print(f"  {icon} [{name}] {detail}")


def module_core():
    """Executável abre sem crash."""
    exe = DEFAULT_EXE
    if not exe.exists():
        test("core", False, f"Executavel nao encontrado: {exe}")
        return

    proc = subprocess.Popen(
        [str(exe)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(exe.parent),
    )

    start = time.time()
    while time.time() - start < TIMEOUT:
        ret = proc.poll()
        if ret is not None:
            stdout, stderr = proc.communicate(timeout=5)
            detail = f"Crashou (exit {ret})"
            if stderr:
                detail += f" | stderr: {stderr.decode('utf-8', errors='replace')[:200]}"
            test("core", False, detail)
            return
        time.sleep(0.5)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    test("core", True, f"App rodou {TIMEOUT}s sem crash")


def module_banco():
    """SQLite conecta e migrations existem."""
    db = LOCALAPPDATA / "database" / "novo_cerebro.db"
    if not db.exists():
        # Tenta o seed DB
        db = PROJECT_ROOT / "database" / "novo_cerebro.db"
    if db.exists():
        try:
            conn = sqlite3.connect(str(db))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM schema_version")
            count = cur.fetchone()[0]
            cur.execute("SELECT MAX(version) FROM schema_version")
            max_ver = cur.fetchone()[0]
            conn.close()
            test("banco", True, f"{db.name}: {count} migracoes, max version {max_ver}")
        except Exception as e:
            test("banco", False, str(e))
    else:
        test("banco", False, "Nenhum banco encontrado")


def module_config():
    """Configurações carregam."""
    config = LOCALAPPDATA / "config" / "default_config.json"
    if not config.exists():
        config = PROJECT_ROOT / "config" / "default_config.json"
    if config.exists():
        try:
            import json
            data = json.loads(config.read_text(encoding="utf-8"))
            test("config", True, f"{len(data)} chaves em {config.name}")
        except Exception as e:
            test("config", False, str(e))
    else:
        test("config", False, "default_config.json nao encontrado")


def module_anexos():
    """Diretório de anexos acessível."""
    attachments = Path.home() / "Documents" / "Central de Gestão" / "Anexos"
    src_attachments = PROJECT_ROOT / "attachments"
    if attachments.exists():
        count = len(list(attachments.iterdir()))
        test("anexos", True, f"{attachments.name} ({count} arquivos)")
    elif src_attachments.exists():
        count = len(list(src_attachments.iterdir()))
        test("anexos", True, f"{src_attachments.name} (src, {count} arquivos)")
    else:
        test("anexos", False, "Nenhum diretorio de anexos encontrado")


MODULES = {
    "core": module_core,
    "banco": module_banco,
    "config": module_config,
    "anexos": module_anexos,
}


def main():
    parser = argparse.ArgumentParser(description="Smoke Test Suite")
    parser.add_argument("--module", choices=list(MODULES.keys()) + ["all"], default="all",
                       help="Modulo a testar (default: all)")
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"  SMOKE TEST SUITE - Central de Gestao")
    print(f"{'=' * 60}")

    modules_to_run = list(MODULES.keys()) if args.module == "all" else [args.module]

    for mod_name in modules_to_run:
        print(f"\n  --- [{mod_name}] ---")
        MODULES[mod_name]()

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["ok"])
    failed = total - passed

    print(f"\n  Resultado: {passed}/{total} passaram")
    if failed > 0:
        print(f"  Modulos com falha: {[r['module'] for r in RESULTS if not r['ok']]}")
        sys.exit(1)
    else:
        print(f"  Todos os modulos OK")
        sys.exit(0)


if __name__ == "__main__":
    print("[DEPRECATED] Use: python scripts/ops/control_panel.py test [--module <name>]", file=sys.stderr)
    main()
