#!/usr/bin/env python
"""Script de manutenção - limpeza de cache e logs."""
import os, shutil

def clean():
    dirs = ['__pycache__', '.pytest_cache']
    for root, subdirs, files in os.walk('.'):
        for d in subdirs:
            if d in dirs:
                path = os.path.join(root, d)
                shutil.rmtree(path, ignore_errors=True)
                print(f"Removido: {path}")

if __name__ == '__main__':
    clean()
