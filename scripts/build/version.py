#!/usr/bin/env python
"""Versão única do Central de Gestão — fonte da verdade para build, installer e release."""

VERSION = "0.8.0"
VERSION_SHORT = "0.8"
BUILD = "1"

def version():
    return VERSION

def version_short():
    return VERSION_SHORT

def full_build():
    return f"{VERSION}+build.{BUILD}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        flag = sys.argv[1]
        if flag == "--full":
            print(full_build())
        elif flag == "--short":
            print(version_short())
        else:
            print(version())
    else:
        print(version())
