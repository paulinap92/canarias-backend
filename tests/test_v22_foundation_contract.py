import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.data_sources import get_data_source
from app.data_sources.calendar import CalendarSource
from app.data_sources.explore import PlacesSource, merge_feature_collections
from app.data_sources.live import WeatherSource
from app.data_sources.news import NewsSource
from app.main import app
from app.services.open_meteo_live import AIR_POINTS_FILE, COASTAL_POINTS_FILE, WEATHER_POINTS_FILE

client = TestClient(app)


def feature(osm_id: int, name: str, **props):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-16.5, 28.3]},
        "properties": {"osm_type": "node", "osm_id": osm_id, "name": name, **props},
    }


def test_explore_raw_refresh_is_upsert_not_replace():
    previous = {
        "type": "FeatureCollection",
        "features": [
            feature(1, "Keep me", description="old"),
            feature(2, "Temporarily missing", description="survives"),
        ],
    }
    fetched = {
        "type": "FeatureCollection",
        "features": [
            feature(1, "Keep me", website="https://fresh.example"),
            feature(3, "New place"),
        ],
    }

    merged, stats = merge_feature_collections(previous, fetched)
    by_id = {f["properties"]["osm_id"]: f for f in merged["features"]}

    assert set(by_id) == {1, 2, 3}
    assert by_id[1]["properties"]["description"] == "old"
    assert by_id[1]["properties"]["website"] == "https://fresh.example"
    assert by_id[2]["properties"]["description"] == "survives"
    assert stats["added"] == 1
    assert stats["kept_missing_from_refresh"] == 1
    assert stats["stored_raw"] == 3


def test_write_strategies_are_explicit():
    assert PlacesSource("explore", "places").write_strategy == "merge"
    assert CalendarSource("calendar", "events").write_strategy == "merge"
    assert NewsSource("news", "latest").write_strategy == "append"
    assert WeatherSource("live", "weather").write_strategy == "replace"


def test_normal_get_does_not_call_external_fetch(monkeypatch):
    source = get_data_source("explore", "places")

    async def explode(**kwargs):  # pragma: no cover - must never run
        raise AssertionError("GET attempted external fetch")

    monkeypatch.setattr(source, "fetch", explode)
    response = client.get("/api/regions/canarias/places?island=tenerife&limit=500")
    assert response.status_code == 200
    assert response.json()["type"] == "FeatureCollection"


def test_live_get_does_not_call_external_fetch(monkeypatch):
    source = get_data_source("live", "weather")

    async def explode(**kwargs):  # pragma: no cover - must never run
        raise AssertionError("GET attempted external fetch")

    monkeypatch.setattr(source, "fetch", explode)
    response = client.get("/api/regions/canarias/live/weather?island=tenerife")
    assert response.status_code == 200
    assert isinstance(response.json().get("points"), list)


def test_live_config_covers_every_island():
    expected = {
        "tenerife",
        "gran-canaria",
        "lanzarote",
        "fuerteventura",
        "la-palma",
        "la-gomera",
        "el-hierro",
        "la-graciosa",
    }
    for path in (WEATHER_POINTS_FILE, AIR_POINTS_FILE, COASTAL_POINTS_FILE):
        values = json.loads(Path(path).read_text(encoding="utf-8"))
        assert expected <= {item["island"] for item in values}


def test_news_merge_reports_refresh_stats():
    source = NewsSource("news", "latest")
    merged = source.merge_payload(
        {"items": [{"url": "https://x/1", "title": "Old"}]},
        {"items": [{"url": "https://x/1", "title": "Updated"}, {"url": "https://x/2", "title": "New"}]},
    )
    assert merged["refresh_stats"]["fetched"] == 2
    assert merged["refresh_stats"]["added"] == 1
    assert merged["refresh_stats"]["duplicates"] == 1
    assert merged["refresh_stats"]["stored"] == 2


def test_calendar_merge_reports_refresh_stats():
    source = CalendarSource("calendar", "events")
    merged = source.merge_payload(
        {"items": [{"url": "https://e/1", "title": "Old", "start_date": "2026-09-11"}]},
        {"items": [{"url": "https://e/1", "title": "Updated", "start_date": "2026-09-11"}, {"url": "https://e/2", "title": "New", "start_date": "2026-09-12"}]},
    )
    assert merged["refresh_stats"]["fetched"] == 2
    assert merged["refresh_stats"]["added"] == 1
    assert merged["refresh_stats"]["updated"] == 1
    assert merged["refresh_stats"]["stored"] == 2
