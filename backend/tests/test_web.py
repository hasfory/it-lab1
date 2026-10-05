import pytest
from fastapi.testclient import TestClient

from app import main
from app.service import SessionManager

SCHEMA = {"name": "t", "fields": [{"name": "id", "type": "integer"},
                                  {"name": "z", "type": "complexInteger"}]}
A = {"X-Session-Id": "session-aaaaaaaa"}
B = {"X-Session-Id": "session-bbbbbbbb"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "sessions", SessionManager(data_dir=str(tmp_path)))
    return TestClient(main.app)


def test_sessions_are_isolated(client):
    client.post("/api/tables", json=SCHEMA, headers=A)
    assert [t["name"] for t in client.get("/api/tables", headers=A).json()] == ["t"]
    assert client.get("/api/tables", headers=B).json() == []


def test_export_and_import_roundtrip(client):
    client.post("/api/database", json={"name": "lab"}, headers=A)
    client.post("/api/tables", json=SCHEMA, headers=A)
    client.post("/api/tables/t/rows", json={"values": {"id": "1", "z": "3+4i"}}, headers=A)
    payload = client.get("/api/database/export", headers=A).json()
    assert payload["version"] == 1 and payload["name"] == "lab"
    # інша сесія імпортує той самий файл
    r = client.post("/api/database/import", json=payload, headers=B)
    assert r.status_code == 200 and r.json()["tables"] == ["t"]
    assert client.get("/api/tables/t", headers=B).json()["rows"] == [{"id": "1", "z": "3+4i"}]


@pytest.mark.parametrize("bad", [
    {"version": 1, "name": 1, "tables": []},
    {"version": 1, "name": "x", "tables": [{"name": 5, "fields": [], "rows": []}]},
    {"version": 2, "name": "x", "tables": []},
    {"version": 1, "name": "x", "tables": "abc"},
    {"version": 1, "name": "x", "tables": [
        {"name": "t", "fields": [{"name": "a", "type": "integer"}], "rows": []},
        {"name": "t", "fields": [{"name": "a", "type": "integer"}], "rows": []}]},
])
def test_import_rejects_malformed_files(client, bad):
    assert client.post("/api/database/import", json=bad, headers=A).status_code == 422


def test_bad_session_id_rejected(client):
    r = client.get("/api/tables", headers={"X-Session-Id": "../etc"})
    assert r.status_code == 422


def test_session_files_are_separate(client):
    client.post("/api/tables", json=SCHEMA, headers=A)
    client.post("/api/database/save", json={"filename": "mine"}, headers=A)
    assert client.get("/api/database/files", headers=A).json() == ["mine"]
    assert client.get("/api/database/files", headers=B).json() == []


def test_session_limit_evicts_oldest(tmp_path):
    sm = SessionManager(data_dir=str(tmp_path), max_sessions=3)
    for i in range(5):
        sm.get(f"session-{i}-xxxxxxx")
    assert sm.count() <= 3
