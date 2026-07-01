import os
import sys
from pathlib import Path


def is_bundled():
    return getattr(sys, 'frozen', False)


def app_root():
    if is_bundled():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_root():
    if is_bundled():
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS)
        return app_root() / "_internal"
    return app_root()


def data_root():
    if is_bundled():
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "CentralGestao"
    return app_root()


def resource_path(relative_path):
    return resource_root() / relative_path


def data_path(relative_path):
    return data_root() / relative_path


def user_docs_path():
    return Path(os.path.expanduser("~/Documents")) / "Central de Gestão" / "Anexos"
