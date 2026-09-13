from app.services.places import _balanced_limit, _build_overpass_query, _representative_coordinates
from app.utils.islands import point_is_on_island


def test_lanzarote_does_not_include_la_graciosa() -> None:
    assert point_is_on_island(-13.502, 29.2317, "la-graciosa")
    assert not point_is_on_island(-13.502, 29.2317, "lanzarote")


def test_north_lanzarote_is_not_mistaken_for_la_graciosa() -> None:
    assert point_is_on_island(-13.4812, 29.2145, "lanzarote")  # Mirador del Río
    assert point_is_on_island(-13.4521, 29.2227, "lanzarote")  # Órzola


def test_tenerife_point_is_inside_tenerife_bbox() -> None:
    assert point_is_on_island(-16.6425, 28.2724, "tenerife")


def test_places_query_is_scoped_and_requests_geometry() -> None:
    query = _build_overpass_query("tenerife")
    assert "27.95,-16.95,28.65,-16.05" in query
    assert "out center geom tags" in query


def test_representative_point_prefers_real_geometry_over_bbox_center() -> None:
    element = {
        "center": {"lat": 99.0, "lon": 99.0},
        "geometry": [
            {"lat": 28.0, "lon": -16.0},
            {"lat": 28.1, "lon": -16.1},
            {"lat": 28.2, "lon": -16.2},
        ],
    }

    longitude, latitude = _representative_coordinates(element) or (None, None)
    assert (longitude, latitude) in {
        (-16.0, 28.0),
        (-16.1, 28.1),
        (-16.2, 28.2),
    }
    assert (longitude, latitude) != (99.0, 99.0)


def test_places_limit_keeps_towns_and_villages_discoverable() -> None:
    def feature(category: str, osm_id: int) -> dict:
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-16.0, 28.0]},
            "properties": {
                "category": category,
                "osm_type": "node",
                "osm_id": osm_id,
                "name": f"{category}-{osm_id}",
            },
        }

    noisy = [feature("viewpoint", i) for i in range(1000)]
    towns = [feature("town", 2000 + i) for i in range(3)]
    villages = [feature("village", 3000 + i) for i in range(4)]

    result = _balanced_limit(noisy + towns + villages, 100)
    categories = [item["properties"]["category"] for item in result]

    assert len(result) == 100
    assert categories.count("town") == 3
    assert categories.count("village") == 4


def test_places_query_includes_pueblos_and_heritage() -> None:
    query = _build_overpass_query("tenerife")
    assert '"place"~"^(town|village|hamlet)$"' in query
    assert '"historic"~"^(castle|fort|archaeological_site|monument|city_gate|ruins)$"' in query


def test_balanced_limit_keeps_heritage_discoverable() -> None:
    def feature(category: str, osm_id: int) -> dict:
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-16.0, 28.0]},
            "properties": {
                "category": category,
                "osm_type": "node",
                "osm_id": osm_id,
                "name": f"{category}-{osm_id}",
            },
        }

    noisy = [feature("viewpoint", i) for i in range(1000)]
    heritage = [feature("heritage", 5000 + i) for i in range(5)]
    result = _balanced_limit(noisy + heritage, 100)
    assert sum(item["properties"]["category"] == "heritage" for item in result) == 5
