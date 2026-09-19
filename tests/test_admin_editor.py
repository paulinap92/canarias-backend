from pathlib import Path

from app.data_sources import get_data_source
from app.services.admin_editor import (
    create_event,
    create_explore,
    hide_explore,
    read_events,
    read_explore,
    update_event,
    update_explore,
)


def test_explore_admin_create_edit_hide(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CANARIAS_EDITOR_DATA_ROOT", str(tmp_path))

    created = create_explore(
        "tenerife",
        "places",
        {
            "name": "Mirador de prueba",
            "category": "viewpoint",
            "latitude": 28.3,
            "longitude": -16.5,
            "description": "Inicial",
        },
    )
    assert created["name"] == "Mirador de prueba"

    data = read_explore("tenerife", "places")
    key = data["items"][0]["_editor_key"]

    updated = update_explore(
        "tenerife",
        "places",
        key,
        {**data["items"][0], "description": "Editado"},
    )
    assert updated["description"] == "Editado"
    assert updated["editorial_override"] is True

    hidden = hide_explore("tenerife", "places", key)
    assert hidden["hidden"] is True


def test_event_editorial_override_survives_refresh_merge(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CANARIAS_EDITOR_DATA_ROOT", str(tmp_path))

    created = create_event(
        "tenerife",
        "2026-09",
        {
            "title": "Evento manual",
            "start_date": "2026-09-25",
            "summary": "Original",
        },
    )
    data = read_events("tenerife", "2026-09")
    key = data["items"][0]["_editor_key"]

    edited = update_event(
        "tenerife",
        "2026-09",
        key,
        {**created, "title": "Título editorial", "summary": "Editado"},
    )

    source = get_data_source("calendar", "events")
    previous = {"items": [dict(edited)]}
    fetched = {
        "items": [
            {
                "id": edited["id"],
                "title": "Título del scraper",
                "summary": "Scraper",
                "start_date": "2026-09-25",
            }
        ]
    }

    merged = source.merge_payload(previous, fetched)
    assert merged["items"][0]["title"] == "Título editorial"
    assert merged["items"][0]["summary"] == "Editado"
