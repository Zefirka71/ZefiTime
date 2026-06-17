"""Пути приложения: исходники, PyInstaller, запись данных."""
import os
import sys


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_path(*parts: str) -> str:
    """Файлы из сборки (PyInstaller: sys._MEIPASS) или корень проекта при запуске из исходников."""
    if is_frozen():
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def local_data_db_path() -> str:
    """SQLite: в сборке — в каталоге данных пользователя; из исходников — текущая рабочая папка."""
    if is_frozen():
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            folder = os.path.join(base, "ZefiTime")
        else:
            base = os.environ.get("XDG_DATA_HOME") or os.path.join(
                os.path.expanduser("~"), ".local", "share"
            )
            folder = os.path.join(base, "zefitime")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "local_data.db")
    return os.path.join(os.getcwd(), "local_data.db")
