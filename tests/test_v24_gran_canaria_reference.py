from __future__ import annotations

import json
from pathlib import Path

from app.data_sources.curation import curate_beaches, curate_places
from app.services.content import get_content
from app.services.events import EVENT_SOURCES

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def test_gran_canaria_places_have_balanced_editorial_backbone():
    raw = {"type": "FeatureCollection", "features": []}
    curated = curate_places(raw, island="gran-canaria")
    features = curated["features"]
    names = {f["properties"]["name"] for f in features}
    featured = [f["properties"]["name"] for f in features if f["properties"].get("featured")]

    assert len(features) >= 14
    assert {
        "Roque Nublo",
        "Dunas de Maspalomas",
        "Vegueta",
        "Tejeda",
        "Puerto de Mogán",
        "Puerto de las Nieves",
        "Teror",
        "Cueva Pintada de Gáldar",
    } <= names
    assert featured[:4] == ["Roque Nublo", "Dunas de Maspalomas", "Vegueta", "Tejeda"]


def test_gran_canaria_beach_catalog_seeds_product_without_external_refresh():
    raw = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-15.71, 28.10]},
                "properties": {"id": "legacy-agaete", "name": "Puerto de las Nieves"},
            }
        ],
    }
    curated = curate_beaches(raw, island="gran-canaria")
    features = curated["features"]
    names = [f["properties"]["name"] for f in features]

    assert len(features) >= 12
    assert names.count("Puerto de las Nieves") == 1
    assert {"Las Canteras", "Maspalomas", "Playa del Inglés", "Amadores", "Güigüi"} <= set(names)
    las_canteras = next(f for f in features if f["properties"]["name"] == "Las Canteras")
    assert las_canteras["properties"]["accessibility_status"] == "yes"
    assert curated["curation"] == "quality-gate:beaches-v2-editorial-first"


def test_gran_canaria_nature_catalogs_are_deeper_than_skeleton():
    for resource in ("fauna", "flora"):
        payload = json.loads((DATA / "curated" / "explore" / resource / "gran-canaria.json").read_text(encoding="utf-8"))
        assert len(payload["features"]) >= 6
        assert all((f.get("properties") or {}).get("description") for f in payload["features"])


def test_gran_canaria_guide_and_experiences_are_reference_island_depth():
    explore = get_content("gran-canaria", "explore", limit=30)
    experiences = get_content("gran-canaria", "experiences", limit=20)
    assert len(explore["items"]) >= 12
    assert len(experiences["items"]) >= 5
    assert any(item["name"] == "Las Palmas: historia y mar" for item in experiences["items"])


def test_gran_canaria_calendar_has_official_source():
    source = EVENT_SOURCES["gran-canaria"]
    assert source["source"] == "Turismo de Gran Canaria"
    assert source["url"].startswith("https://")
