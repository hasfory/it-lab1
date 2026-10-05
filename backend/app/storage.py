"""Збереження бази даних на диск і читання з диска (формат JSON)."""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from .errors import NotFoundError, ValidationError
from .models import Database

FORMAT_VERSION = 1


class StorageManager:
    # ---- перетворення бази у/з JSON-структуру (спільне для файлів та імпорту) ----
    @staticmethod
    def to_payload(db: Database) -> dict:
        return {"version": FORMAT_VERSION, **db.to_dict()}

    @staticmethod
    def from_payload(data: Any) -> Database:
        if not isinstance(data, dict):
            raise ValidationError("Файл не є коректним файлом бази")
        if data.get("version") != FORMAT_VERSION:
            raise ValidationError(
                f"Непідтримувана версія формату: {data.get('version')}"
            )
        return Database.from_dict(data)

    # ---- файли на диску ----------------------------------------------------------
    @staticmethod
    def save(db: Database, path: str) -> None:
        """Записує базу у файл. Запис атомарний: спочатку у тимчасовий файл,
        потім заміна, тож при збої старий файл не буде пошкоджено."""
        payload = StorageManager.to_payload(db)
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    @staticmethod
    def load(path: str) -> Database:
        if not os.path.isfile(path):
            raise NotFoundError(f"Файл '{path}' не знайдено")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValidationError(f"Файл не є коректним файлом бази: {e}")
        return StorageManager.from_payload(data)
