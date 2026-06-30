#!/usr/bin/env python
"""
Bump de versão do Central de Gestão.

Uso:
    python scripts/build/bump_version.py patch   # 0.8.0 → 0.8.1
    python scripts/build/bump_version.py minor   # 0.8.0 → 0.9.0
    python scripts/build/bump_version.py major   # 0.8.0 → 1.0.0
"""

import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VERSION_FILE = PROJECT_ROOT / "scripts" / "build" / "version.py"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"


def read_version():
    ns = {}
    exec(VERSION_FILE.read_text(encoding="utf-8"), ns)
    return ns["VERSION"]


def write_version(new_version):
    content = VERSION_FILE.read_text(encoding="utf-8")
    short = ".".join(new_version.split(".")[:2])
    content = re.sub(r'^VERSION = ".*"', f'VERSION = "{new_version}"', content, flags=re.MULTILINE)
    content = re.sub(r'^VERSION_SHORT = ".*"', f'VERSION_SHORT = "{short}"', content, flags=re.MULTILINE)
    VERSION_FILE.write_text(content, encoding="utf-8")
    print(f"  version.py: {new_version}")


def update_changelog(version):
    if not CHANGELOG_FILE.exists():
        print("  CHANGELOG.md nao encontrado, pulando")
        return
    from datetime import date
    entry = f"\n## [{version}] - {date.today().isoformat()}\n\n### Added\n- \n\n### Fixed\n- \n"
    content = CHANGELOG_FILE.read_text(encoding="utf-8")
    # Insere após o cabeçalho
    lines = content.split("\n")
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("# ") or line.startswith("<!--"):
            continue
        if line.strip() == "":
            insert_at = i + 1
            break
    lines.insert(insert_at, entry)
    CHANGELOG_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"  CHANGELOG.md: entrada para {version} adicionada")


def bump(part):
    parts = [int(x) for x in read_version().split(".")]
    if part == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif part == "minor":
        parts[1] += 1
        parts[2] = 0
    elif part == "patch":
        parts[2] += 1
    else:
        print(f"Parte invalida: {part}. Use: patch, minor, major")
        sys.exit(1)
    new_version = ".".join(str(p) for p in parts)
    return new_version


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("patch", "minor", "major"):
        print("Uso: python scripts/build/bump_version.py {patch|minor|major}")
        sys.exit(1)

    old_ver = read_version()
    new_ver = bump(sys.argv[1])
    print(f"  {old_ver} → {new_ver}")

    write_version(new_ver)
    update_changelog(new_ver)

    print(f"\nVersao atualizada: {new_ver}")
    print(f"Commit sugestao: git commit -m 'chore: bump version to {new_ver}'")
    print(f"Tag sugestao:    git tag -a v{new_ver} -m 'Release v{new_ver}'")


if __name__ == "__main__":
    print("[DEPRECATED] Use: python scripts/ops/control_panel.py bump <patch|minor|major>", file=sys.stderr)
    main()
