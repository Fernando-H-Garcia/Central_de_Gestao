#!/usr/bin/env python
"""Script para criar tag de release."""
import subprocess, sys

def main(version):
    tag = f"v{version}"
    subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {tag}"], check=True)
    subprocess.run(["git", "push", "origin", tag], check=True)
    print(f"Tag {tag} criada e enviada.")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python create_tag.py <version>")
        sys.exit(1)
    main(sys.argv[1])
