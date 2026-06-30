import os
import sys
from pathlib import Path

APP_NAME = "Central de Gestão"
APP_VERSION = "0.8"

_is_bundled = getattr(sys, 'frozen', False)

if _is_bundled:
    BASE_DIR = Path(sys.executable).resolve().parent
    _internal_dir = BASE_DIR / "_internal"
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "CentralGestao"
else:
    BASE_DIR = Path(__file__).resolve().parent
    _internal_dir = BASE_DIR
    DATA_DIR = BASE_DIR

INSTALL_DB_DIR = _internal_dir / "database"
INSTALL_DB_PATH = INSTALL_DB_DIR / "novo_cerebro.db"
INSTALL_MIGRATIONS_DIR = _internal_dir / "database" / "migrations"
INSTALL_CONFIG_DIR = _internal_dir / "config"

DB_DIR = DATA_DIR / "database"
DB_PATH = DB_DIR / "novo_cerebro.db"
MIGRATIONS_DIR = DATA_DIR / "database" / "migrations"
CONFIG_DIR = DATA_DIR / "config"
LOGS_DIR = DATA_DIR / "logs"
BACKUPS_DIR = DATA_DIR / "backups"

ATTACHMENTS_DIR = _internal_dir / "attachments"

USER_DOCS_DIR = Path(os.path.expanduser("~/Documents"))
ATTACHMENTS_STORAGE_DIR = USER_DOCS_DIR / APP_NAME / "Anexos"

for dir_path in [DATA_DIR, DB_DIR, MIGRATIONS_DIR, CONFIG_DIR, LOGS_DIR, BACKUPS_DIR, ATTACHMENTS_STORAGE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


