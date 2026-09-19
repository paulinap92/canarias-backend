from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.content_editor import create_item, delete_item, read_items, update_item


client = TestClient(app)


def _prepare(monkeypatch, tmp_path: Path) -> Path:
    root = tmp_path / "content"
    path = root / "tenerife" / "food.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        '[{"id":"food-1","slug":"papas-arrugadas","name":"Papas arrugadas"}]\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("CANARIAS_CONTENT_ROOT", str(root))
    return root


def test_editor_service_crud(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)

    created = create_item(
        "tenerife",
        "food",
        {
            "slug": "gofio-escaldado",
            "name": "Gofio escaldado",
            "tags": ["food"],
        },
    )
    assert created["slug"] == "gofio-escaldado"

    updated = update_item(
        "tenerife",
        "food",
        "gofio-escaldado",
        {**created, "description": "Receta tradicional."},
    )
    assert updated["description"] == "Receta tradicional."

    delete_item("tenerife", "food", "gofio-escaldado")
    assert [item["slug"] for item in read_items("tenerife", "food")] == ["papas-arrugadas"]


def test_editor_is_hidden_when_disabled(monkeypatch):
    monkeypatch.setenv("CANARIAS_CONTENT_EDITOR", "0")
    response = client.get("/editor")
    assert response.status_code == 404


def test_editor_api_with_remote_token(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)
    monkeypatch.setenv("CANARIAS_CONTENT_EDITOR", "1")
    monkeypatch.setenv("CANARIAS_CONTENT_EDITOR_TOKEN", "test-secret")

    response = client.get(
        "/api/editor/content",
        params={"island": "tenerife", "section": "food"},
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["slug"] == "papas-arrugadas"
