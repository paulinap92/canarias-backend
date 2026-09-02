from fastapi.testclient import TestClient

from app.main import app
from app.models.island import Island
from app.models.region import Region
from app.repositories.island import IslandRepository
from app.repositories.region import RegionRepository


client = TestClient(app)


def test_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Canarias API"}


def test_get_regions(monkeypatch) -> None:
    async def fake_find_all(self):
        return [
            Region(
                id=1,
                name="Canarias",
                slug="canarias",
            )
        ]

    monkeypatch.setattr(
        RegionRepository,
        "find_all",
        fake_find_all,
    )

    response = client.get("/api/regions")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Canarias",
            "slug": "canarias",
        }
    ]


def test_get_region_by_slug(monkeypatch) -> None:
    async def fake_find_by_slug(self, slug: str):
        return Region(
            id=1,
            name="Canarias",
            slug=slug,
        )

    monkeypatch.setattr(
        RegionRepository,
        "find_by_slug",
        fake_find_by_slug,
    )

    response = client.get("/api/regions/canarias")

    assert response.status_code == 200
    assert response.json()["slug"] == "canarias"


def test_get_unknown_region(monkeypatch) -> None:
    async def fake_find_by_slug(self, slug: str):
        return None

    monkeypatch.setattr(
        RegionRepository,
        "find_by_slug",
        fake_find_by_slug,
    )

    response = client.get("/api/regions/mars")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Region not found",
    }


def test_get_islands_for_region(monkeypatch) -> None:
    async def fake_find_by_region_slug(self, region_slug: str):
        return [
            Island(
                id=1,
                name="Tenerife",
                slug="tenerife",
                region_id=1,
            )
        ]

    monkeypatch.setattr(
        IslandRepository,
        "find_by_region_slug",
        fake_find_by_region_slug,
    )

    response = client.get(
        "/api/regions/canarias/islands"
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Tenerife",
            "slug": "tenerife",
            "region_id": 1,
        }
    ]