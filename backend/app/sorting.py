"""Операція варіанту: сортування таблиці за одним полем.
"""
from __future__ import annotations

from typing import Any, Callable

from .field_types import get_type
from .models import FieldDefinition, Table


class FieldComparatorFactory:
    """Повертає функцію-ключ для порівняння значень поля заданого типу.

    Для complexInteger / complexReal порівняння йде за модулем числа,
    при рівності модулів - за дійсною, а потім за уявною частиною.
    """

    @staticmethod
    def key_for(field: FieldDefinition) -> Callable[[Any], Any]:
        return get_type(field.type_name).sort_key


class TableSorter:
    @staticmethod
    def sort(table: Table, field_name: str, descending: bool = False) -> None:
        """Сортує рядки таблиці на місці за полем field_name.

        Сортування стабільне: рядки з рівними значеннями зберігають
        свій попередній відносний порядок (і при спаданні теж).
        Якщо поля не існує - кидає NotFoundError.
        """
        field = table.field(field_name)
        key = FieldComparatorFactory.key_for(field)
        table.rows.sort(key=lambda row: key(row[field.name]), reverse=descending)
