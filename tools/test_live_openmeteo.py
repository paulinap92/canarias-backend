from __future__ import annotations

import argparse
import sys
import httpx


def get_json(client: httpx.Client, base: str, path: str):
    response = client.get(f"{base}{path}")
    if response.status_code != 200:
        raise AssertionError(
            f"{path}: HTTP {response.status_code} {response.text[:300]}"
        )
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base",
        default="http://127.0.0.1:8000",
    )
    args = parser.parse_args()
    base = args.base.rstrip("/")

    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        weather = get_json(
            client,
            base,
            "/api/regions/canarias/live/weather?island=tenerife",
        )
        assert weather["source"] == "Open-Meteo"
        assert weather["points_count"] >= 8
        assert all(p["island"] == "tenerife" for p in weather["points"])
        assert all(p["sunrise"] and p["sunset"] for p in weather["points"])
        print("OK weather Tenerife:", weather["points_count"])

        air = get_json(
            client,
            base,
            "/api/regions/canarias/live/air-quality?island=lanzarote",
        )
        assert air["points_count"] >= 3
        assert all(p["island"] == "lanzarote" for p in air["points"])
        assert all("dust" in p and "european_aqi" in p for p in air["points"])
        print("OK air/calima Lanzarote:", air["points_count"])

        tides = get_json(
            client,
            base,
            "/api/regions/canarias/live/tides?island=tenerife&hours=48",
        )
        assert tides["points_count"] >= 4
        assert all(p["island"] == "tenerife" for p in tides["points"])
        assert all("turns" in p for p in tides["points"])
        print("OK tides Tenerife:", tides["points_count"])

        alerts = get_json(
            client,
            base,
            "/api/regions/canarias/alerts?island=lanzarote",
        )
        for alert in alerts:
            assert alert["status"] == "active"
            assert alert["official_vigente"] is True
            assert "lanzarote" in alert["islands"]
        print("OK active alerts Lanzarote:", len(alerts))

    print()
    print("ALL LIVE OPEN-METEO TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
