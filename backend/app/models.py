"""Модель даних: Database -> Table -> (FieldDefinition, рядки)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from .errors import NotFoundError, ValidationError
from .field_types import get_type


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    type_name: str


class Table:
    """Таблиця: схема (список полів) і рядки (список словників ім'я -> значення)."""

    def __init__(self, name: str, fields: List[FieldDefinition]):
        self.name = name
        self.fields = fields
        self.rows: List[Dict[str, Any]] = []

    # ---- схема --------------------------------------------------------------
    @staticmethod
    def validate_schema(name: str, fields: List[FieldDefinition]) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Назва таблиці не може бути порожньою")
        if not fields:
            raise ValidationError("Таблиця повинна мати хоча б одне поле")
        seen = set()
        for f in fields:
            if not isinstance(f.name, str) or not f.name.strip():
                raise ValidationError("Назва поля не може бути порожньою")
            if not isinstance(f.type_name, str):
                raise ValidationError("Тип поля має бути рядком")
            key = f.name.strip().lower()
            if key in seen:
                raise ValidationError(f"Повторювана назва поля: '{f.name}'")
            seen.add(key)
            get_type(f.type_name)  # кине ValidationError, якщо тип невідомий

    def field(self, name: str) -> FieldDefinition:
        for f in self.fields:
            if f.name == name:
                return f
        raise NotFoundError(f"Поле '{name}' не існує в таблиці '{self.name}'")

    # ---- рядки --------------------------------------------------------------
    def _validate_row(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        unknown = set(values) - {f.name for f in self.fields}
        if unknown:
            raise ValidationError(f"Невідомі поля: {', '.join(sorted(unknown))}")
        parsed: Dict[str, Any] = {}
        for f in self.fields:
            if f.name not in values:
                raise ValidationError(f"Не вказано значення для поля '{f.name}'")
            try:
                parsed[f.name] = get_type(f.type_name).parse(values[f.name])
            except ValidationError as e:
                raise ValidationError(f"Поле '{f.name}': {e}")
        return parsed

    def _check_index(self, index: int) -> None:
        if not (0 <= index < len(self.rows)):
            raise NotFoundError(f"Рядка з індексом {index} не існує")

    def add_row(self, values: Mapping[str, Any]) -> int:
        self.rows.append(self._validate_row(values))
        return len(self.rows) - 1

    def update_row(self, index: int, values: Mapping[str, Any]) -> None:
        self._check_index(index)
        self.rows[index] = self._validate_row(values)

    def delete_row(self, index: int) -> None:
        self._check_index(index)
        del self.rows[index]

    # ---- серіалізація -------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "fields": [{"name": f.name, "type": f.type_name} for f in self.fields],
            "rows": [
                {f.name: get_type(f.type_name).to_json(r[f.name]) for f in self.fields}
                for r in self.rows
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Table":
        try:
            fields = [FieldDefinition(f["name"], f["type"]) for f in data["fields"]]
            cls.validate_schema(data["name"], fields)
            table = cls(data["name"], fields)
            for raw_row in data["rows"]:
                row = {}
                for f in fields:
                    row[f.name] = get_type(f.type_name).from_json(raw_row[f.name])
                table.rows.append(row)
        except (KeyError, TypeError, AttributeError) as e:
            raise ValidationError(f"Пошкоджений формат таблиці: {e}")
        return table

    def rows_as_text(self) -> List[Dict[str, str]]:
        """Рядки у зручному для показу вигляді (усі значення як текст)."""
        return [
            {f.name: get_type(f.type_name).to_str(r[f.name]) for f in self.fields}
            for r in self.rows
        ]


class Database:
    def __init__(self, name: str = "database"):
        self.name = name
        self.tables: Dict[str, Table] = {}

    def create_table(self, name: str, fields: List[FieldDefinition]) -> Table:
        Table.validate_schema(name, fields)
        if name in self.tables:
            raise ValidationError(f"Таблиця '{name}' вже існує")
        table = Table(name, fields)
        self.tables[name] = table
        return table

    def drop_table(self, name: str) -> None:
        if name not in self.tables:
            raise NotFoundError(f"Таблиці '{name}' не існує")
        del self.tables[name]

    def get_table(self, name: str) -> Table:
        if name not in self.tables:
            raise NotFoundError(f"Таблиці '{name}' не існує")
        return self.tables[name]

    def to_dict(self) -> dict:
        return {"name": self.name, "tables": [t.to_dict() for t in self.tables.values()]}

    @classmethod
    def from_dict(cls, data: dict) -> "Database":
        try:
            if not isinstance(data["name"], str) or not data["name"].strip():
                raise ValidationError("Назва бази має бути непорожнім рядком")
            db = cls(data["name"])
            if not isinstance(data["tables"], list):
                raise ValidationError("Список таблиць має бути масивом")
            for t in data["tables"]:
                table = Table.from_dict(t)
                if table.name in db.tables:
                    raise ValidationError(f"Повторювана назва таблиці: '{table.name}'")
                db.tables[table.name] = table
        except (KeyError, TypeError, AttributeError) as e:
            raise ValidationError(f"Пошкоджений формат бази: {e}")
        return db
