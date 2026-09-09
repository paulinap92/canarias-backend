from app.services.beaches import _representative_coordinates as beach_coordinates
from app.services.places import _representative_coordinates as place_coordinates
from app.utils.islands import point_is_on_island


def test_la_graciosa_point_is_not_lanzarote() -> None:
    longitude = -13.502
    latitude = 29.2317

    assert point_is_on_island(longitude, latitude, "la-graciosa")
    assert not point_is_on_island(longitude, latitude, "lanzarote")


def test_lanzarote_point_remains_lanzarote() -> None:
    longitude = -13.5477
    latitude = 28.963

    assert point_is_on_island(longitude, latitude, "lanzarote")
    assert not point_is_on_island(longitude, latitude, "la-graciosa")


def test_place_representative_coordinate_uses_real_geometry() -> None:
    element = {
        "center": {"lat": 28.5, "lon": -16.5},
        "geometry": [
            {"lat": 28.10, "lon": -16.10},
            {"lat": 28.11, "lon": -16.11},
            {"lat": 28.12, "lon": -16.12},
        ],
    }

    result = place_coordinates(element)

    assert result in {
        (28.10, -16.10),
        (28.11, -16.11),
        (28.12, -16.12),
    }
    assert result != (28.5, -16.5)


def test_beach_representative_coordinate_uses_real_geometry() -> None:
    element = {
        "center": {"lat": 28.5, "lon": -16.5},
        "geometry": [
            {"lat": 28.20, "lon": -16.20},
            {"lat": 28.21, "lon": -16.21},
            {"lat": 28.22, "lon": -16.22},
        ],
    }

    result = beach_coordinates(element)

    assert result in {
        (28.20, -16.20),
        (28.21, -16.21),
        (28.22, -16.22),
    }
    assert result != (28.5, -16.5)
