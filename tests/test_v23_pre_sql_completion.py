import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.data_sources.curation import curate_explore, curate_places
from app.main import app
from app.services.content import get_content
from app.services.trails import _route_feature


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ISLANDS = {
    "tenerife",
    "gran-canaria",
    "lanzarote",
    "fuerteventura",
    "la-palma",
    "la-gomera",
    "el-hierro",
    "la-graciosa",
}
GUIDE_EXPANSION = {
    "history",
    "climate",
    "historical-weather",
    "geology",
    "nature",
    "experiences",
}

client = TestClient(app)


def _point(name: str, category: str = "village") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-16.5, 28.3]},
        "properties": {"name": name, "category": category},
    }


def test_tenerife_places_have_editorial_backbone_and_featured_is_not_adeje():
    raw = {
        "type": "FeatureCollection",
        "features": [_point("Adeje"), *[_point(f"Village {i}") for i in range(60)]],
    }
    curated = curate_places(raw, island="tenerife")
    names = {f["properties"].get("name") for f in curated["features"]}
    featured = {
        f["properties"].get("name")
        for f in curated["features"]
        if f["properties"].get("featured") is True
    }

    assert {"Parque Nacional del Teide", "Parque Rural de Anaga", "Masca", "Garachico"} <= names
    assert "Adeje" not in featured
    assert curated["curation"] == "quality-gate:places-v2-editorial-first"


def test_fauna_and_flora_are_curated_and_non_empty_for_every_island():
    # Product GETs re-run the current curator over any stored snapshot, so the
    # regression contract must validate the product view rather than assume the
    # on-disk published file has already been rewritten after every catalog update.
    for resource in ("fauna", "flora"):
        for island in ISLANDS:
            path = DATA / "explore" / resource / f"{island}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            product = curate_explore(resource, payload, island=island, previous=payload)
            features = product.get("features") or []
            assert features, f"{resource}/{island} is empty"
            for feature in features:
                props = feature.get("properties") or {}
                assert props.get("status") == "published"
                assert props.get("featured") is not None
                assert props.get("description")
                # Product data must describe a useful place/habitat, not an occurrence dump.
                if resource == "fauna":
                    assert props.get("hotspot")
                else:
                    assert props.get("hotspot") or props.get("habitat")
                assert props.get("occurrence_id") is None


def test_expanded_guide_sections_exist_for_every_island():
    for island in ISLANDS:
        for section in GUIDE_EXPANSION:
            data = get_content(island, section, limit=50)
            assert data["available"] is True, f"{island}/{section} unavailable"
            assert data["items"], f"{island}/{section} empty"


def test_historical_weather_is_explicitly_qualitative_until_normals_are_added():
    for island in ISLANDS:
        data = get_content(island, "historical-weather", limit=20)
        assert len(data["items"]) == 12
        assert all(item.get("data_quality") == "qualitative_climate_calendar" for item in data["items"])


def test_experiences_have_ordered_stops_from_curated_content():
    for island in ISLANDS:
        data = get_content(island, "experiences", limit=10)
        for item in data["items"]:
            stops = item.get("ordered_stops") or []
            assert len(stops) >= 2
            assert all(stop.get("name") for stop in stops)
            assert all(isinstance(stop.get("latitude"), (int, float)) for stop in stops)
            assert all(isinstance(stop.get("longitude"), (int, float)) for stop in stops)


def test_content_api_serves_new_guide_sections():
    response = client.get("/api/regions/canarias/content?island=tenerife&section=history")
    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["items"]


def test_route_metadata_exposes_numeric_distance_duration_difficulty_and_circular():
    relation = {
        "type": "relation",
        "id": 987,
        "tags": {
            "type": "route",
            "route": "hiking",
            "name": "Ruta metadata",
            "duration": "02:30",
            "sac_scale": "mountain_hiking",
            "roundtrip": "yes",
        },
        "members": [
            {
                "type": "way",
                "geometry": [
                    {"lat": 28.1, "lon": -16.5},
                    {"lat": 28.2, "lon": -16.6},
                ],
            }
        ],
    }
    feature = _route_feature(relation)
    props = feature["properties"]
    assert props["distance_km"] > 0
    assert props["duration"] == "02:30"
    assert props["difficulty"] == "media"
    assert props["circular"] is True
