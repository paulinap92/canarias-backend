from app.data_sources.curation import curate_beaches, curate_explore, curate_places, curate_routes


def point(name, category="village", **extra):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-16.5, 28.3]},
        "properties": {"name": name, "category": category, **extra},
    }


def test_places_caps_raw_dump():
    raw = {
        "type": "FeatureCollection",
        "features": [point(f"Village {i}") for i in range(100)],
    }
    curated = curate_places(raw, island="tenerife")
    # The editorial backbone is always present and the raw import only extends
    # it under conservative category quotas. We care about bounded output, not
    # the old magic number from the raw-only curator.
    assert 8 <= len(curated["features"]) <= 24
    assert curated["raw_count"] == 100
    assert all(f["properties"]["status"] == "published" for f in curated["features"])
    assert any(f["properties"].get("cc_curated") for f in curated["features"])


def test_beach_missing_flags_are_unknown_not_false():
    raw = {"type": "FeatureCollection", "features": [point("Playa X", category="beach")]}
    curated = curate_beaches(raw, island="tenerife")
    p = curated["features"][0]["properties"]
    assert p["accessibility_status"] == "unknown"
    assert p["lifeguard_status"] == "unknown"
    assert p["nudism_status"] == "unknown"


def test_routes_publish_only_shortlist():
    features = []
    for i in range(30):
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[-16.5, 28.3], [-16.4, 28.4]]},
            "properties": {"route_id": f"r{i}", "name": f"Route {i}", "distance": f"{i+1} km"},
        })
    curated = curate_routes({"type": "FeatureCollection", "features": features}, island="tenerife")
    assert len(curated["features"]) == 8


def test_fauna_uses_curated_catalog_not_occurrence_dump():
    raw = {
        "type": "FeatureCollection",
        "features": [point("Random occurrence", category="observation", scientific_name="Something random")],
    }
    curated = curate_explore("fauna", raw, island="tenerife")
    assert 1 <= len(curated["features"]) <= 10
    assert all("hotspot" in f["properties"] for f in curated["features"])
    assert all(f["properties"].get("name") != "Random occurrence" for f in curated["features"])
