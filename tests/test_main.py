from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Canarias API"}


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["api"] == "ok"


def test_unknown_island_capabilities() -> None:
    response = client.get("/api/regions/canarias/islands/mars/capabilities")
    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown island"


def test_tenerife_capabilities() -> None:
    response = client.get("/api/regions/canarias/islands/tenerife/capabilities")
    assert response.status_code == 200
    features = response.json()["features"]
    assert features["weather"] is True
    assert features["air_quality"] is True
    assert features["tides"] is True


def test_la_graciosa_live_capabilities_match_point_data() -> None:
    response = client.get("/api/regions/canarias/islands/la-graciosa/capabilities")
    assert response.status_code == 200
    features = response.json()["features"]
    assert features["weather"] is True
    assert features["air_quality"] is True
    assert features["tides"] is True
    assert features["monuments"] is False


def test_invalid_content_section() -> None:
    response = client.get(
        "/api/regions/canarias/content/not-found",
        params={"island": "tenerife", "section": "nope"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid content section"
