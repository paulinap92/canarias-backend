from app.services.trails import _build_query, _route_feature


def test_trails_query_requests_route_relations_without_member_way_dump() -> None:
    query = _build_query("tenerife")
    assert 'relation' in query
    assert '["route"~"^(hiking|foot)$"]' in query
    assert 'out geom;' in query
    assert 'way(r.routes)' not in query


def test_route_relation_becomes_one_multiline_feature() -> None:
    relation = {
        "type": "relation",
        "id": 123,
        "tags": {
            "type": "route",
            "route": "hiking",
            "name": "Ruta de prueba",
            "ref": "PR TF-1",
            "distance": "8 km",
        },
        "members": [
            {
                "type": "way",
                "geometry": [
                    {"lat": 28.1, "lon": -16.5},
                    {"lat": 28.2, "lon": -16.6},
                ],
            },
            {
                "type": "way",
                "geometry": [
                    {"lat": 28.2, "lon": -16.6},
                    {"lat": 28.3, "lon": -16.7},
                ],
            },
        ],
    }

    feature = _route_feature(relation)
    assert feature is not None
    assert feature["geometry"]["type"] == "MultiLineString"
    assert feature["properties"]["route_id"] == "relation-123"
    assert feature["properties"]["name"] == "Ruta de prueba"
