#!/usr/bin/env python
"""
Remove DLLs obsoletas do bundle PyInstaller (_internal/).

Essas DLLs são stubs da Microsoft que não têm função em runtime,
mas o PyInstaller as inclui por excesso de cautela.
"""

import os
from pathlib import Path

INTERNAL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "build" / "dist" / "CentralDeGestao" / "_internal"

STUB_PREFIXES = [
    "api-ms-win-",
    "ext-ms-win-",
]


def main():
    if not INTERNAL_DIR.exists():
        print(f"  Diretorio _internal nao encontrado: {INTERNAL_DIR}")
        return

    removed = 0
    total_size = 0

    for dll in INTERNAL_DIR.glob("*.dll"):
        name = dll.name.lower()
        if any(name.startswith(prefix) for prefix in STUB_PREFIXES):
            size = dll.stat().st_size
            dll.unlink()
            removed += 1
            total_size += size
            print(f"  Removido: {dll.name} ({size // 1024} KB)")

    if removed:
        print(f"  Total: {removed} DLLs removidas ({total_size // 1024} KB)")
    else:
        print(f"  Nenhuma DLL obsoleta encontrada")


if __name__ == "__main__":
    main()
