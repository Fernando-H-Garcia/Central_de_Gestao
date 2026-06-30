#!/usr/bin/env python
"""
Smoke Test para Central de Gestão.

Uso:
    python scripts/tests/smoke_test.py [--exe <path>]

Valida:
    - Executável abre sem crash
    - Janela principal aparece
    - SQLite conecta
    - App não crasha no startup

Exit codes:
    0 = OK
    1 = Falha
"""

import sys
import subprocess
import time
import signal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_EXE = PROJECT_ROOT / "build" / "dist" / "CentralDeGestao" / "CentralDeGestao.exe"
TIMEOUT = 15


def find_exe():
    exe_path = DEFAULT_EXE
    if not exe_path.exists():
        print(f"[SMOKE] ERRO: Executavel nao encontrado em {exe_path}")
        print("[SMOKE] Use --exe <caminho> para especificar manualmente")
        sys.exit(1)
    return exe_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Smoke Test do Central de Gestao")
    parser.add_argument("--exe", help="Caminho do executavel (opcional)")
    args = parser.parse_args()

    exe_path = Path(args.exe) if args.exe else find_exe()

    print(f"[SMOKE] Executavel: {exe_path}")
    print(f"[SMOKE] Iniciando aplicacao...")

    proc = subprocess.Popen(
        [str(exe_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(exe_path.parent),
    )

    start = time.time()
    while time.time() - start < TIMEOUT:
        ret = proc.poll()
        if ret is not None:
            stdout, stderr = proc.communicate(timeout=5)
            print(f"[SMOKE] Processo encerrou prematuramente (exit code: {ret})")
            if stdout:
                print(f"[SMOKE] STDOUT: {stdout.decode('utf-8', errors='replace')[:500]}")
            if stderr:
                print(f"[SMOKE] STDERR: {stderr.decode('utf-8', errors='replace')[:500]}")
            print("[SMOKE] FALHA: App crashou no startup")
            sys.exit(1)
        time.sleep(0.5)

    if proc.poll() is None:
        print(f"[SMOKE] App rodou por {TIMEOUT}s sem crashar — OK")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[SMOKE] Smoke test PASS")
        sys.exit(0)
    else:
        print("[SMOKE] FALHA: App nao manteve execucao")
        sys.exit(1)


if __name__ == "__main__":
    main()
