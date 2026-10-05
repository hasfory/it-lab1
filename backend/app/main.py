"""REST API (FastAPI) для системи керування табличними базами даних.

Веб-версія: цей самий процес віддає і API (/api/...), і зібраний інтерфейс
(папка static, якщо вона є). Кожен браузер працює у власній сесії
(заголовок X-Session-Id), тому дані різних користувачів не змішуються.

Запуск:  uvicorn app.main:app --host 0.0.0.0 --port 8000
Документація API:  http://127.0.0.1:8000/docs
"""
import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .errors import NotFoundError, ValidationError
from .service import DatabaseService, SessionManager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 МБ

app = FastAPI(title="Table DBMS API", version="2.0")


# Обмеження розміру запиту (захист від завеликих файлів при імпорті).
@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
        return JSONResponse(status_code=413, content={"detail": "Запит завеликий (максимум 5 МБ)"})
    return await call_next(request)


# Дозволяємо звернення з іншого origin (режим розробки, десктоп-клієнт).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = SessionManager(data_dir=os.path.join(BASE_DIR, "data"))


def get_service(x_session_id: Optional[str] = Header(default=None)) -> DatabaseService:
    """Сервіс поточної сесії (за заголовком X-Session-Id)."""
    return sessions.get(x_session_id)


# ------------------------------------------------------------ схеми запитів --
class NewDatabase(BaseModel):
    name: str


class FileRequest(BaseModel):
    filename: str


class FieldSchema(BaseModel):
    name: str
    type: str


class NewTable(BaseModel):
    name: str
    fields: List[FieldSchema]


class RowValues(BaseModel):
    values: Dict[str, Any]


class SortRequest(BaseModel):
    field: str
    descending: bool = False


# --------------------------------------------------------- обробка помилок --
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


# ------------------------------------------------------------------- база --
@app.get("/api/types")
def get_types(s: DatabaseService = Depends(get_service)):
    return s.field_types()


@app.get("/api/database")
def get_database(s: DatabaseService = Depends(get_service)):
    return s.info()


@app.post("/api/database", status_code=201)
def create_database(body: NewDatabase, s: DatabaseService = Depends(get_service)):
    return s.new_database(body.name)


@app.get("/api/database/files")
def list_files(s: DatabaseService = Depends(get_service)):
    return s.list_files()


@app.post("/api/database/save")
def save_database(body: FileRequest, s: DatabaseService = Depends(get_service)):
    return s.save(body.filename)


@app.post("/api/database/load")
def load_database(body: FileRequest, s: DatabaseService = Depends(get_service)):
    return s.load(body.filename)


@app.get("/api/database/export")
def export_database(s: DatabaseService = Depends(get_service)):
    """Уся база одним JSON (клієнт зберігає її у файл на комп'ютері користувача)."""
    return s.export_payload()


@app.post("/api/database/import")
def import_database(body: Dict[str, Any], s: DatabaseService = Depends(get_service)):
    """Замінює поточну базу вмістом файлу, який вибрав користувач."""
    return s.import_payload(body)


# --------------------------------------------------------------- таблиці --
@app.get("/api/tables")
def list_tables(s: DatabaseService = Depends(get_service)):
    return s.list_tables()


@app.post("/api/tables", status_code=201)
def create_table(body: NewTable, s: DatabaseService = Depends(get_service)):
    return s.create_table(body.name, [f.model_dump() for f in body.fields])


@app.get("/api/tables/{name}")
def get_table(name: str, s: DatabaseService = Depends(get_service)):
    return s.table_view(name)


@app.delete("/api/tables/{name}")
def delete_table(name: str, s: DatabaseService = Depends(get_service)):
    s.drop_table(name)
    return {"deleted": name}


# ---------------------------------------------------------------- рядки --
@app.post("/api/tables/{name}/rows", status_code=201)
def add_row(name: str, body: RowValues, s: DatabaseService = Depends(get_service)):
    return s.add_row(name, body.values)


@app.put("/api/tables/{name}/rows/{index}")
def update_row(name: str, index: int, body: RowValues, s: DatabaseService = Depends(get_service)):
    return s.update_row(name, index, body.values)


@app.delete("/api/tables/{name}/rows/{index}")
def delete_row(name: str, index: int, s: DatabaseService = Depends(get_service)):
    return s.delete_row(name, index)


# ------------------------------------------------------------- сортування --
@app.post("/api/tables/{name}/sort")
def sort_table(name: str, body: SortRequest, s: DatabaseService = Depends(get_service)):
    return s.sort_table(name, body.field, body.descending)


# ------------------------------------------------- веб-інтерфейс (React) --
# Монтується останнім, щоб не перекривати /api та /docs.
if os.path.isfile(os.path.join(STATIC_DIR, "index.html")):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="web")
