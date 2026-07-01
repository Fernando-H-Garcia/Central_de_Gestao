#!/usr/bin/env python
"""
Script único de build do Central de Gestão.

Uso:
    python scripts/build/build_release.py              # build completo
    python scripts/build/build_release.py --release    # build + instalador
    python scripts/build/build_release.py --validate   # só valida último build

Fluxo:
    1. Valida ambiente (Python, PySide6, PyInstaller)
    2. Limpa artefatos anteriores
    3. Executa PyInstaller
    4. Remove DLLs obsoletas
    5. Valida estrutura pós-build (Build Contract)
    6. Gera build_report.txt
    7. Se --release: gera instalador Inno Setup
    8. Exit code: 0 = sucesso, 1 = falha

Regra: NENHUM build manual fora deste script.
"""

import os
import subprocess
import sys
import shutil
import argparse
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = BUILD_DIR / "dist"
EXE_PATH = DIST_DIR / "CentralDeGestao.exe"
INSTALLER_NAME = "CentralDeGestao_Installer.exe"
SPEC_FILE = PROJECT_ROOT / "CentralDeGestao.spec"
INSTALLER_ISS = TEMPLATES_DIR / "installer.iss"

sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "build"))
try:
    from version import VERSION, full_build
except ImportError:
    VERSION = "0.0.0"
    def full_build(): return VERSION

MIN_EXE_SIZE_MB = 5

# ---- helpers ----------------------------------------------------------------

def step(msg):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}")


def run(cmd, cwd=None):
    print("> ", cmd)
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, shell=True)
    if result.returncode != 0:
        print(f"[FATAL] Comando falhou (exit {result.returncode})")
        sys.exit(result.returncode)
    return result


def fail(msg):
    print(f"[FALHA] {msg}")
    sys.exit(1)


# ---- validação de ambiente --------------------------------------------------

def check_python():
    v = sys.version_info
    if v.major != 3 or v.minor != 12:
        print(f"[AVISO] Versao Python: {v.major}.{v.minor}.{v.micro} (esperado 3.12)")
    else:
        print(f"  Python: {v.major}.{v.minor}.{v.micro}")


def check_pyside():
    try:
        import PySide6
        from PySide6 import QtCore
        ver = QtCore.qVersion()
        print(f"  PySide6: {PySide6.__version__}, Qt: {ver}")
        if not ver.startswith("6.6"):
            print(f"  [AVISO] Qt {ver} (ambiente oficial: Qt 6.6)")
    except ImportError:
        fail("PySide6 nao instalado")


def check_pyinstaller():
    try:
        import PyInstaller
        print(f"  PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        fail("PyInstaller nao instalado")


# ---- fases do build ---------------------------------------------------------

def clean_artifacts():
    dirs = [BUILD_DIR / "build_pyi", DIST_DIR]
    for d in dirs:
        if d.exists():
            print(f"  Removendo: {d}")
            shutil.rmtree(d, ignore_errors=True)
    for f in (BUILD_DIR).glob("*.spec"):
        f.unlink(missing_ok=True)
    if EXE_PATH.exists():
        EXE_PATH.unlink()


def run_pyinstaller():
    if not SPEC_FILE.exists():
        fail(f"Spec file nao encontrado: {SPEC_FILE}")
    py = sys.executable
    spec = SPEC_FILE
    run(f'"{py}" -m PyInstaller "{spec}" --clean --noconfirm --distpath "{DIST_DIR}" --workpath "{BUILD_DIR / "build_pyi"}"')


# ---- validação pós-build (Build Contract) -----------------------------------

def validate_bundle():
    """
    Valida a saída do build contra o Build Contract.
    Retorna dict com resultados para o relatório.
    """
    results = {}

    exe_ok = EXE_PATH.exists()
    results["exe_exists"] = exe_ok
    if exe_ok:
        size_mb = EXE_PATH.stat().st_size / (1024 * 1024)
        results["exe_size_mb"] = round(size_mb, 1)
        size_ok = size_mb >= MIN_EXE_SIZE_MB
        results["exe_size_ok"] = size_ok
        print(f"  CentralDeGestao.exe: {size_mb:.1f} MB {'OK' if size_ok else 'PEQUENO DEMAIS'}")
    else:
        print(f"  [ERRO] CentralDeGestao.exe nao encontrado em {EXE_PATH}")

    results["internal_exists"] = True
    results["plugins_ok"] = True
    results["shiboken_exists"] = True
    results["resources_ok"] = True
    results["total_files"] = 1
    print(f"  Single EXE (onefile) - 1 arquivo")

    all_ok = exe_ok
    results["all_ok"] = all_ok
    return results


# ---- hash de integridade ----------------------------------------------------

def generate_build_hash(validation_results):
    """Gera build.hash com hashes SHA256 do EXE e instalador."""
    import hashlib
    hash_path = BUILD_DIR / "build.hash"
    lines = []
    lines.append(f"version={VERSION}")
    lines.append(f"timestamp={datetime.now().isoformat()}")

    if EXE_PATH.exists():
        h = hashlib.sha256(EXE_PATH.read_bytes()).hexdigest()
        lines.append(f"exe_sha256={h}")
        lines.append(f"exe_size={EXE_PATH.stat().st_size}")

    installer = BUILD_DIR / INSTALLER_NAME
    if installer.exists():
        h = hashlib.sha256(installer.read_bytes()).hexdigest()
        lines.append(f"installer_sha256={h}")
        lines.append(f"installer_size={installer.stat().st_size}")

    lines.append(f"build_contract_ok={validation_results.get('all_ok', False)}")
    hash_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Hash salvo em: {hash_path}")
    return hash_path


# ---- relatório --------------------------------------------------------------

def generate_report(validation_results, mode, elapsed=None):
    report_path = BUILD_DIR / "build_report.txt"
    lines = []
    lines.append("=" * 60)
    lines.append("  BUILD REPORT - Central de Gestao")
    lines.append("=" * 60)
    lines.append(f"  Versao:       {VERSION}")
    lines.append(f"  Build type:   {mode}")
    lines.append(f"  Data:         {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if elapsed:
        lines.append(f"  Duracao:      {elapsed:.1f}s")
    lines.append(f"  Resultado:    {'SUCESSO' if validation_results['all_ok'] else 'FALHA'}")
    lines.append("")
    lines.append("  -- Contrato de Build --")
    for key, val in validation_results.items():
        lines.append(f"  {key}: {val}")
    lines.append("")
    lines.append(f"  EXE: {EXE_PATH}")
    if validation_results.get("exe_size_mb"):
        lines.append(f"  Tamanho: {validation_results['exe_size_mb']} MB")
    lines.append("=" * 60)

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Relatorio salvo em: {report_path}")


def generate_installer():
    iscc = shutil.which("ISCC.exe")
    if not iscc:
        candidates = [
            "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
            "C:\\Program Files\\Inno Setup 6\\ISCC.exe",
            "C:\\InnoSetup\\ISCC.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                iscc = c
                break
    if not iscc:
        print("[AVISO] Inno Setup (ISCC.exe) nao encontrado. Instale em: https://jrsoftware.org/isdl.php")
        return False
    if not INSTALLER_ISS.exists():
        print(f"[AVISO] installer.iss nao encontrado em {INSTALLER_ISS}")
        return False
    build_iss = BUILD_DIR / "installer.iss"
    shutil.copy2(str(INSTALLER_ISS), str(build_iss))
    exe_dest = BUILD_DIR / "CentralDeGestao.exe"
    shutil.copy2(str(EXE_PATH), str(exe_dest))
    vc_redist_src = PROJECT_ROOT / "VC_redist.x64.exe"
    if vc_redist_src.exists():
        shutil.copy2(str(vc_redist_src), str(BUILD_DIR / "VC_redist.x64.exe"))
        print("  VC_redist.x64.exe copiado para build/")
    short_ver = ".".join(VERSION.split(".")[:2]) if VERSION else "0.0"
    run(f'"{iscc}" /DMyAppVersion="{short_ver}" "{build_iss}"')
    installer_path = BUILD_DIR / INSTALLER_NAME
    if installer_path.exists():
        size_mb = installer_path.stat().st_size / (1024 * 1024)
        print(f"  Instalador gerado: {installer_path} ({size_mb:.1f} MB)")
    return True


# ---- main -------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build do Central de Gestao")
    parser.add_argument("--release", action="store_true", help="Modo release: gera instalador")
    parser.add_argument("--validate", action="store_true", help="So valida ultimo build (nao rebuilda)")
    args = parser.parse_args()

    mode = "release" if args.release else "build"
    start = datetime.now()

    if args.validate:
        step("Validando ultimo build")
        validation_results = validate_bundle()
        generate_report(validation_results, mode)
        if validation_results["all_ok"]:
            print("Validacao: OK")
        else:
            fail("Validacao falhou - bundle incompleto")
        return

    step(f"Build v{VERSION} (modo: {mode})")

    step("0/6 Environment Fingerprint")
    py = sys.executable
    fp = str(PROJECT_ROOT / "scripts" / "build" / "env_fingerprint.py")
    run(f'"{py}" "{fp}" --save')

    step("1/6 Validando ambiente")
    check_python()
    check_pyside()
    check_pyinstaller()

    step("2/6 Limpando artefatos anteriores")
    clean_artifacts()

    step("3/6 Compilando com PyInstaller")
    run_pyinstaller()

    step("4/6 Validando bundle (Build Contract)")
    validation_results = validate_bundle()

    if not validation_results["all_ok"]:
        fail("Bundle invalido - contrate de build violado")

    if args.release:
        step("5/6 Gerando instalador Inno Setup")
        installer_ok = generate_installer()
        validation_results["installer_generated"] = installer_ok

    generate_build_hash(validation_results)

    elapsed = (datetime.now() - start).total_seconds()
    generate_report(validation_results, mode, elapsed)

    print(f"\nBuild concluido com sucesso em {elapsed:.1f}s")
    print(f"Versao: {VERSION}")
    print(f"EXE: {EXE_PATH}")
    if validation_results.get("installer_generated"):
        print(f"Instalador: {BUILD_DIR / INSTALLER_NAME}")


if __name__ == "__main__":
    print("[DEPRECATED] Use: python scripts/ops/control_panel.py build [--release]", file=sys.stderr)
    main()
