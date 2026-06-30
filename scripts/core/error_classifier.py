#!/usr/bin/env python
"""
Failure Isolation System — classifica erros automaticamente.

Uso:
    from scripts.core.error_classifier import classify_error
    category = classify_error(exception_or_message)
"""

import re

ERROR_PATTERNS = {
    "QT": [
        r"PySide6",
        r"Qt.*error",
        r"segfault",
        r"dangling",
        r"shiboken",
        r"parent=None",
        r"QWidget",
        r"QApplication",
        r"BadgeDelegate",
        r"QTextBrowser",
        r"QStackedWidget",
        r"calendar",
    ],
    "BUILD": [
        r"PyInstaller",
        r"build\.spec",
        r"cleanup_dlls",
        r"ISCC",
        r"Inno Setup",
        r"UPX",
        r"upx_exclude",
        r"DLL",
        r"api-ms-win",
        r"ext-ms-win",
    ],
    "SQLITE": [
        r"sqlite3",
        r"OperationalError",
        r"database",
        r"migration",
        r"schema_version",
        r"no such table",
        r"duplicate column",
        r".*\.db",
    ],
    "ENV": [
        r"Python",
        r"pip",
        r"ModuleNotFoundError",
        r"ImportError",
        r"version",
        r"compatible",
        r"requirements",
        r"fingerprint",
    ],
    "CI": [
        r"GitHub",
        r"actions",
        r"workflow",
        r"runner",
        r"artifact",
        r"upload",
        r"download",
    ],
    "NETWORK": [
        r"ConnectionError",
        r"Timeout",
        r"requests",
        r"urlopen",
        r"gh ",
        r"git.*push",
        r"git.*fetch",
    ],
    "RELEASE": [
        r"tag",
        r"release",
        r"rollback",
        r"publish",
        r"gh release",
    ],
    "CONTRACT": [
        r"Build Contract",
        r"validate_bundle",
        r"exe_exists",
        r"plugins_ok",
        r"resources_ok",
        r"internal_exists",
    ],
}


def classify_error(error, default="UNKNOWN"):
    """Classifica um erro em uma categoria."""
    error_str = str(error)
    for category, patterns in ERROR_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, error_str, re.IGNORECASE):
                return category
    return default


def format_error_report(error, context=None):
    """Gera relatório estruturado do erro."""
    return {
        "error": str(error),
        "category": classify_error(error),
        "context": context or {},
        "type": type(error).__name__,
    }
