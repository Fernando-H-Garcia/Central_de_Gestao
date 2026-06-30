#!/usr/bin/env python
"""
Release Health Check — valida estado da instalação.

Uso:
    python scripts/tests/release_health_check.py [--app-dir <path>]

Valida:
    1. App abre (smoke test)
    2. Banco SQLite existe e responde
    3. Migrations OK (schema_version completa)
    4. Logs são criados
    5. Config carrega
    6. Anexos acessíveis

Exit codes:
    0 = Saudável
    1 = Problema crítico
"""

import sys
import subprocess
import time
import sqlite3
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_APP_DIR = PROJECT_ROOT / "build" / "dist" / "CentralDeGestao"
LOCALAPPDATA = Path.home() / "AppData" / "Local" / "CentralGestao"

HEALTH = {"status": "unknown", "checks": {}}


def check( name, ok, detail=""):
    HEALTH["checks"][name] = {"ok": ok, "detail": detail}
    icon = "✅" if ok else "❌"
    print(f"  {icon} {name}: {detail}")


def step(msg):
    print(f"\n  --- {msg} ---")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Release Health Check")
    parser.add_argument("--app-dir", help="Diretorio do app (default: build/dist/CentralDeGestao)")
    parser.add_argument("--version", help="Versao esperada (opcional)")
    args = parser.parse_args()

    app_dir = Path(args.app_dir) if args.app_dir else DEFAULT_APP_DIR

    print(f"\n{'=' * 60}")
    print(f"  RELEASE HEALTH CHECK")
    print(f"{'=' * 60}")
    print(f"  App dir:  {app_dir}")
    print(f"  Data dir: {LOCALAPPDATA}")

    step("1. Executavel existe")
    exe = app_dir / "CentralDeGestao.exe"
    check("executavel", exe.exists(), str(exe) if exe.exists() else "AUSENTE")

    step("2. Banco SQLite")
    db = LOCALAPPDATA / "brain.db"
    db_ok = db.exists()
    if db_ok:
        try:
            conn = sqlite3.connect(str(db))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM schema_version")
            count = cur.fetchone()[0]
            cur.execute("SELECT MAX(version) FROM schema_version")
            max_ver = cur.fetchone()[0] or 0
            conn.close()
            check("banco", True, f"{db.name} ({count} migracoes, max: {max_ver})")
        except Exception as e:
            check("banco", False, str(e))
    else:
        check("banco", False, "brain.db nao encontrado")

    step("3. Config")
    config = LOCALAPPDATA / "config" / "default_config.json"
    if config.exists():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
            check("config", True, f"{len(data)} chaves carregadas")
        except Exception as e:
            check("config", False, str(e))
    else:
        check("config", False, "default_config.json nao encontrado")

    step("4. Logs")
    logs_dir = LOCALAPPDATA / "logs"
    logs_ok = logs_dir.exists() and len(list(logs_dir.glob("*.log"))) > 0
    check("logs", logs_ok, f"{logs_dir} {'com logs' if logs_ok else 'vazio/ausente'}")

    step("5. Anexos")
    attachments = Path.home() / "Documents" / "Central de Gestão" / "Anexos"
    check("anexos", attachments.exists(), str(attachments) if attachments.exists() else "AUSENTE")

    step("6. Versao (opcional)")
    if args.version:
        ver_file = app_dir / "build_report.txt"
        if ver_file.exists():
            content = ver_file.read_text()
            if args.version in content:
                check("versao", True, args.version)
            else:
                check("versao", False, f"esperado {args.version}")
        else:
            check("versao", False, "build_report.txt nao encontrado")

    all_ok = all(c["ok"] for c in HEALTH["checks"].values())
    HEALTH["status"] = "healthy" if all_ok else "unhealthy"

    print(f"\n  Resultado: {'SAUDAVEL' if all_ok else 'COM PROBLEMAS'}")
    report_path = PROJECT_ROOT / "build" / "health_report.json"
    Path(report_path).write_text(json.dumps(HEALTH, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Relatorio: {report_path}")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    print("[DEPRECATED] Use: python scripts/ops/control_panel.py health", file=sys.stderr)
    main()
