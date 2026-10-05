from app.models import Database, FieldDefinition
from app.sorting import TableSorter
from app.storage import StorageManager

db = Database("demo")
t = db.create_table("numbers", [
    FieldDefinition("id", "integer"),
    FieldDefinition("z", "complexInteger"),
    FieldDefinition("name", "string"),
])
t.add_row({"id": "1", "z": "3+4i", "name": "Оля"})   # |z| = 5
t.add_row({"id": "2", "z": "-i",   "name": "Іван"})  # |z| = 1
t.add_row({"id": "3", "z": "5",    "name": "Анна"})  # |z| = 5, re = 5
t.add_row({"id": "4", "z": "0",    "name": "Петро"}) # |z| = 0

print("До сортування:")
for r in t.rows_as_text(): print(r)

TableSorter.sort(t, "z")
print("\nЗа зростанням модуля комплексного числа:")
for r in t.rows_as_text(): print(r)

TableSorter.sort(t, "name")
print("\nЗа іменем у алфавітному порядку:")
for r in t.rows_as_text(): print(r)

StorageManager.save(db, "demo.json")
db2 = StorageManager.load("demo.json")
print("\nПісля збереження і читання збігається:", db2.to_dict() == db.to_dict())
