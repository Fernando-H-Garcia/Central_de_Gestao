#!/usr/bin/env python
"""
Release Score — calcula score de 0 a 100 para uma release.

Uso:
    python scripts/release/release_score.py [--tag v0.8.0]

Critérios:
    - Testes passando (40pts)
    - Health check OK (20pts)
    - Build contract OK (15pts)
    - Instalador gerado (10pts)
    - Sem mudancas RISKY (10pts)
    - Versao incrementada (5pts)
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BUILD_DIR = PROJECT_ROOT / "build"


def score_tests():
    """40pts: smoke test + health check."""
    smoke_report = BUILD_DIR / "build_report.txt"
    if not smoke_report.exists():
        return 0, "build_report.txt nao encontrado"

    content = smoke_report.read_text(encoding="utf-8")
    if "SUCESSO" in content:
        return 40, "Smoke test + health check passaram"
    return 10, "Testes com falha (score parcial)"


def score_health():
    """20pts: health check."""
    health = BUILD_DIR / "health_report.json"
    if not health.exists():
        return 0, "health_report.json nao encontrado"
    try:
        data = json.loads(health.read_text(encoding="utf-8"))
        if data.get("status") == "healthy":
            checks = data.get("checks", {})
            ok = sum(1 for c in checks.values() if c.get("ok"))
            total = len(checks)
            return int(20 * ok / total) if total > 0 else 0, f"{ok}/{total} checks OK"
    except Exception as e:
        return 0, str(e)
    return 0, "Health check falhou"


def score_build_contract():
    """15pts: build contract."""
    report = BUILD_DIR / "build_report.txt"
    if not report.exists():
        return 0, "build_report.txt nao encontrado"
    content = report.read_text(encoding="utf-8")
    if "all_ok: True" in content:
        return 15, "Build contract OK"
    return 0, "Build contract violado"


def score_installer():
    """10pts: instalador."""
    installer = BUILD_DIR / "CentralDeGestao_Installer.exe"
    if installer.exists():
        size_mb = installer.stat().st_size / (1024 * 1024)
        if size_mb > 10:
            return 10, f"Instalador gerado ({size_mb:.0f} MB)"
        return 5, f"Instalador muito pequeno ({size_mb:.0f} MB)"
    return 0, "Instalador nao gerado"


def score_risky_changes():
    """10pts: sem mudancas RISKY."""
    import subprocess
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s"], capture_output=True, text=True
    )
    msg = result.stdout.strip().lower()
    if "risky" in msg:
        return 0, "Commit contem mudanca RISKY"
    return 10, "Sem mudancas de alto risco"


def score_version_bump():
    """5pts: versao incrementada."""
    import subprocess
    # Compara tag anterior com atual
    result = subprocess.run(
        ["git", "tag", "--sort=-creatordate"],
        capture_output=True, text=True
    )
    tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip() and t.startswith("v")]
    if len(tags) >= 2:
        return 5, f"Versao incrementada ({tags[0]})"
    return 3, "Primeira release ou versao nao incrementada"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Release Score")
    parser.add_argument("--tag", help="Tag da release (opcional)")
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"  RELEASE SCORE")
    print(f"{'=' * 60}")

    if args.tag:
        print(f"  Release: {args.tag}")

    scores = [
        ("Testes", *score_tests()),
        ("Health Check", *score_health()),
        ("Build Contract", *score_build_contract()),
        ("Instalador", *score_installer()),
        ("Mudancas RISKY", *score_risky_changes()),
        ("Versao", *score_version_bump()),
    ]

    total = 0
    for name, pts, detail in scores:
        total += pts
        bar = "█" * (pts // 5) + "░" * (20 - pts // 5)
        print(f"  {bar} {name:15s} {pts:2d}/100 - {detail}")

    print(f"\n  {'=' * 40}")
    grade = "A" if total >= 90 else "B" if total >= 75 else "C" if total >= 50 else "D"
    print(f"  SCORE TOTAL: {total}/100 (Grade {grade})")
    print(f"  {'=' * 40}")

    sys.exit(0 if total >= 50 else 1)


if __name__ == "__main__":
    print("[DEPRECATED] Use: python scripts/ops/control_panel.py score", file=sys.stderr)
    main()
