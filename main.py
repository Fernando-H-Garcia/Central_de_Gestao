import os
import sys
import sqlite3
import shutil
from pathlib import Path
from core.startup import startup_init, log
from core.error_handler import setup_global_error_handler
from config import (
    DB_PATH, MIGRATIONS_DIR, LOGS_DIR,
    _is_bundled, DATA_DIR, BASE_DIR,
    INSTALL_DB_PATH, INSTALL_MIGRATIONS_DIR, INSTALL_CONFIG_DIR,
    CONFIG_DIR
)
from core.background_queue import task_queue


def initialize_appdata():
    """Copia dados do instalador para DATA_DIR (segunda camada de segurança)."""
    if not _is_bundled:
        return
    init_marker = DATA_DIR / ".initialized"
    first_run = not init_marker.exists()

    if first_run and INSTALL_DB_PATH.exists() and not DB_PATH.exists():
        shutil.copy2(str(INSTALL_DB_PATH), str(DB_PATH))
        log("Seed DB copiada (initialize_appdata)")

    if INSTALL_MIGRATIONS_DIR.exists():
        MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
        for f in INSTALL_MIGRATIONS_DIR.glob("*.sql"):
            dst = MIGRATIONS_DIR / f.name
            if not dst.exists():
                shutil.copy2(str(f), str(dst))
        log("Migrations copiadas (initialize_appdata)")

    if INSTALL_CONFIG_DIR.exists():
        for f in INSTALL_CONFIG_DIR.glob("*"):
            dst = CONFIG_DIR / f.name
            if not dst.exists():
                shutil.copy2(str(f), str(dst))
        log("Config copiada (initialize_appdata)")

    if first_run:
        init_marker.write_text("1")


def verify_build_hash():
    """Verifica integridade do build se build.hash existir."""
    import hashlib
    try:
        from config import BASE_DIR
        hash_path = BASE_DIR / "build.hash"
        if not hash_path.exists():
            return
        lines = {}
        for line in hash_path.read_text(encoding="utf-8").strip().split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                lines[k] = v
        exe_path = Path(sys.executable if getattr(sys, 'frozen', False) else __file__)
        if exe_path.exists() and "exe_sha256" in lines:
            current = hashlib.sha256(exe_path.read_bytes()).hexdigest()
            if current != lines["exe_sha256"]:
                log("Hash do executavel nao confere com build.hash", "warning")
    except Exception as e:
        log(f"Erro ao verificar hash: {e}", "warning")


def main():
    setup_global_error_handler()

    # ---- First Run Hardening: startup pipeline com auto-repair ----
    try:
        startup_init()
    except Exception as e:
        log(f"Startup pipeline falhou criticamente: {e}", "error")

    verify_build_hash()
    initialize_appdata()

    from PySide6.QtWidgets import QApplication
    from gui.main_window_qt import MainWindow

    qt_app = QApplication(sys.argv)

    from gui.theme import GLOBAL_STYLE
    qt_app.setStyleSheet(GLOBAL_STYLE)

    from gui.theme import style_calendar_today
    from PySide6.QtWidgets import QDateEdit, QDateTimeEdit, QCalendarWidget
    from PySide6.QtCore import QEvent, QObject, QTimer

    class _CalendarWatcher(QObject):
        def __init__(self, date_edit):
            super().__init__(date_edit)
            date_edit.installEventFilter(self)

        def eventFilter(self, obj, event):
            if event.type() == QEvent.ChildPolished and isinstance(event.child(), QCalendarWidget):
                QTimer.singleShot(0, lambda de=obj: style_calendar_today(de))
            return super().eventFilter(obj, event)

    _orig_date_cal = QDateEdit.setCalendarPopup
    def _patched_date_cal(self, enabled):
        _orig_date_cal(self, enabled)
        if enabled:
            _CalendarWatcher(self)
    QDateEdit.setCalendarPopup = _patched_date_cal

    _orig_dt_cal = QDateTimeEdit.setCalendarPopup
    def _patched_dt_cal(self, enabled):
        _orig_dt_cal(self, enabled)
        if enabled:
            _CalendarWatcher(self)
    QDateTimeEdit.setCalendarPopup = _patched_dt_cal

    window = MainWindow()
    window.showMaximized()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
