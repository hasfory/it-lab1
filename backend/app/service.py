"""Сервісний шар: поточна база в пам'яті + операції над нею.

Відповідає класу TableService з діаграм етапу 1. API-шар (main.py) лише
приймає запити й викликає методи цього класу.
"""
from __future__ import annotations

import os
import re
import threading
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .errors import NotFoundError, ValidationError
from .field_types import TYPES, get_type
from .models import Database, FieldDefinition, Table
from .sorting import TableSorter
from .storage import StorageManager

_FILENAME_RE = re.compile(r"^[\w\- ]{1,64}$")  # \w включає кирилицю


class DatabaseService:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self._db = Database("database")
        self._lock = threading.RLock()

    # ---- база ---------------------------------------------------------------
    def new_database(self, name: str) -> dict:
        if not name or not name.strip():
            raise ValidationError("Назва бази не може бути порожньою")
        with self._lock:
            self._db = Database(name.strip())
            return self.info()

    def info(self) -> dict:
        with self._lock:
            return {"name": self._db.name, "tables": list(self._db.tables)}

    # ---- таблиці ------------------------------------------------------------
    def list_tables(self) -> List[dict]:
        with self._lock:
            return [self._schema(t) | {"row_count": len(t.rows)}
                    for t in self._db.tables.values()]

    def create_table(self, name: str, fields: List[Mapping[str, str]]) -> dict:
        defs = [FieldDefinition(f["name"], f["type"]) for f in fields]
        with self._lock:
            table = self._db.create_table(name, defs)
            return self.table_view(table.name)

    def drop_table(self, name: str) -> None:
        with self._lock:
            self._db.drop_table(name)

    def table_view(self, name: str) -> dict:
        with self._lock:
            t = self._db.get_table(name)
            return self._schema(t) | {"rows": t.rows_as_text()}

    # ---- рядки --------------------------------------------------------------
    def add_row(self, table: str, values: Mapping[str, Any]) -> dict:
        with self._lock:
            self._db.get_table(table).add_row(values)
            return self.table_view(table)

    def update_row(self, table: str, index: int, values: Mapping[str, Any]) -> dict:
        with self._lock:
            self._db.get_table(table).update_row(index, values)
            return self.table_view(table)

    def delete_row(self, table: str, index: int) -> dict:
        with self._lock:
            self._db.get_table(table).delete_row(index)
            return self.table_view(table)

    # ---- сортування (операція варіанту) -------------------------------------
    def sort_table(self, table: str, field: str, descending: bool) -> dict:
        with self._lock:
            TableSorter.sort(self._db.get_table(table), field, descending)
            return self.table_view(table)

    # ---- збереження / читання ----------------------------------------------
    def save(self, filename: str) -> dict:
        path = self._path(filename)
        with self._lock:
            StorageManager.save(self._db, path)
        return {"saved": os.path.basename(path)}

    def load(self, filename: str) -> dict:
        path = self._path(filename)
        if not os.path.isfile(path):
            raise NotFoundError(f"Файл '{os.path.basename(path)}' не знайдено")
        db = StorageManager.load(path)
        with self._lock:
            self._db = db
            return self.info()

    def list_files(self) -> List[str]:
        if not os.path.isdir(self.data_dir):
            return []
        return sorted(f[:-5] for f in os.listdir(self.data_dir) if f.endswith(".json"))

    # ---- обмін файлами з комп'ютером користувача (веб-версія) --------------------
    def export_payload(self) -> dict:
        with self._lock:
            return StorageManager.to_payload(self._db)

    def import_payload(self, data: Any) -> dict:
        db = StorageManager.from_payload(data)
        with self._lock:
            self._db = db
            return self.info()

    # ---- допоміжне ----------------------------------------------------------
    def _path(self, filename: str) -> str:
        name = (filename or "").strip()
        if name.endswith(".json"):
            name = name[:-5]
        if not _FILENAME_RE.match(name):
            raise ValidationError(
                "Некоректна назва файлу: дозволені літери, цифри, пробіл, '-' та '_' (до 64 символів)"
            )
        return os.path.join(self.data_dir, name + ".json")

    @staticmethod
    def _schema(t: Table) -> dict:
        return {"name": t.name,
                "fields": [{"name": f.name, "type": f.type_name} for f in t.fields]}

    @staticmethod
    def field_types() -> List[str]:
        return list(TYPES)


DEFAULT_SESSION = "default"
_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class SessionManager:
    """Окремий DatabaseService для кожної веб-сесії (браузера).

    Сесію ідентифікує заголовок X-Session-Id. Без заголовка використовується
    спільна сесія "default" (десктоп-клієнт, Swagger). Неактивні сесії
    видаляються з пам'яті через ttl_seconds, а при перевищенні max_sessions
    витісняється найдавніша.
    """

    def __init__(self, data_dir: str = "data", ttl_seconds: int = 12 * 3600,
                 max_sessions: int = 200):
        self.data_dir = data_dir
        self.ttl = ttl_seconds
        self.max_sessions = max_sessions
        self._items: Dict[str, Tuple[DatabaseService, float]] = {}
        self._lock = threading.Lock()

    def get(self, session_id: Optional[str]) -> DatabaseService:
        key = session_id or DEFAULT_SESSION
        if key != DEFAULT_SESSION and not _SESSION_RE.match(key):
            raise ValidationError("Некоректний ідентифікатор сесії")
        now = time.monotonic()
        with self._lock:
            self._purge(now)
            entry = self._items.get(key)
            if entry is None:
                folder = (self.data_dir if key == DEFAULT_SESSION
                          else os.path.join(self.data_dir, "sessions", key))
                service = DatabaseService(data_dir=folder)
                if len(self._items) >= self.max_sessions:
                    self._evict_oldest()
            else:
                service = entry[0]
            self._items[key] = (service, now)
            return service

    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def _purge(self, now: float) -> None:
        for k in [k for k, (_, t) in self._items.items()
                  if k != DEFAULT_SESSION and now - t > self.ttl]:
            del self._items[k]

    def _evict_oldest(self) -> None:
        candidates = [(t, k) for k, (_, t) in self._items.items() if k != DEFAULT_SESSION]
        if candidates:
            del self._items[min(candidates)[1]]
