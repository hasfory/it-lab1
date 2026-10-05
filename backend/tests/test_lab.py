import pytest

from app.errors import ValidationError
from app.field_types import Complex, get_type
from app.models import Database, FieldDefinition
from app.sorting import TableSorter
from app.storage import StorageManager


def make_table():
    db = Database("demo")
    t = db.create_table("numbers", [
        FieldDefinition("id", "integer"),
        FieldDefinition("z", "complexInteger"),
        FieldDefinition("name", "string"),
    ])
    t.add_row({"id": "1", "z": "3+4i", "name": "Оля"})
    t.add_row({"id": "2", "z": "-i", "name": "Іван"})
    t.add_row({"id": "3", "z": "5", "name": "Анна"})
    t.add_row({"id": "4", "z": "0", "name": "Петро"})
    return db, t


def test_validation_of_complex_types():
    """Тест 1: валідація даних додаткових типів complexInteger / complexReal."""
    assert get_type("complexInteger").parse("3+4i") == Complex(3, 4)
    assert get_type("complexInteger").parse("-i") == Complex(0, -1)
    assert get_type("complexReal").parse("2.5-1.3i") == Complex(2.5, -1.3)
    with pytest.raises(ValidationError):
        get_type("complexInteger").parse("2.5+1i")   # дробові частини недопустимі
    with pytest.raises(ValidationError):
        get_type("complexReal").parse("abc")


def test_sort_table_by_field():
    """Тест 2 (індивідуальна операція): сортування таблиці за одним полем."""
    _, t = make_table()
    TableSorter.sort(t, "z")  # за модулем; при рівних модулях - за дійсною частиною
    assert [r["z"] for r in t.rows_as_text()] == ["0+0i", "0-1i", "3+4i", "5+0i"]
    TableSorter.sort(t, "name")  # за українським алфавітом
    assert [r["name"] for r in t.rows_as_text()] == ["Анна", "Іван", "Оля", "Петро"]
    TableSorter.sort(t, "id", descending=True)
    assert [r["id"] for r in t.rows_as_text()] == ["4", "3", "2", "1"]


def test_save_and_load_database(tmp_path):
    """Тест 3: збереження бази на диск і зчитування з диска без втрат."""
    db, _ = make_table()
    path = str(tmp_path / "demo.json")
    StorageManager.save(db, path)
    loaded = StorageManager.load(path)
    assert loaded.to_dict() == db.to_dict()
    assert loaded.get_table("numbers").rows_as_text()[0]["z"] == "3+4i"