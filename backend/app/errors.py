class ValidationError(ValueError):
    """Помилка валідації даних (тип значення, схема таблиці тощо)."""


class NotFoundError(KeyError):
    """Таблицю, поле або рядок не знайдено."""

    def __str__(self) -> str:  # щоб повідомлення не брати в лапки
        return str(self.args[0]) if self.args else ""
