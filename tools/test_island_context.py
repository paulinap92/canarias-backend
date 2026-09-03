from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx


def assert_status(
    response: httpx.Response,
    name: str,
) -> Any:
    if response.status_code != 200:
        raise AssertionError(
            f"{name}: HTTP {response.status_code} "
            f"{response.text[:300]}"
        )

    return response.json()


def assert_record_island(
    records: list[dict[str, Any]],
    island: str,
    name: str,
) -> None:
    wrong = [
        item
        for item in records
        if item.get("island") != island
    ]

    if wrong:
        raise AssertionError(
            f"{name}: found records from another island: "
            f"{wrong[:2]}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--base",
        default="http://127.0.0.1:8000",
    )

    args = parser.parse_args()
    base = args.base.rstrip("/")

    with httpx.Client(
        timeout=90.0,
        follow_redirects=True,
    ) as client:

        # 1. Health
        health = assert_status(
            client.get(f"{base}/health"),
            "health",
        )

        if not health["storage"]["writable"]:
            raise AssertionError(
                "health: cache storage is not writable"
            )

        print("OK health")

        # 2. Capabilities
        capabilities = assert_status(
            client.get(
                f"{base}/api/regions/canarias/"
                "islands/lanzarote/capabilities"
            ),
            "capabilities",
        )

        if capabilities["features"]["events"]:
            raise AssertionError(
                "Lanzarote must not claim Tenerife events"
            )

        if capabilities["features"]["webcams"]:
            raise AssertionError(
                "Lanzarote must not claim Tenerife webcams"
            )

        print("OK capabilities Lanzarote")

        # 3. Cities strict filter
        cities = assert_status(
            client.get(
                f"{base}/api/regions/canarias/"
                "cities?island=lanzarote"
            ),
            "cities",
        )
        assert_record_island(
            cities,
            "lanzarote",
            "cities",
        )
        print("OK cities Lanzarote")

        # 4. Monuments strict filter
        monuments = assert_status(
            client.get(
                f"{base}/api/regions/canarias/"
                "monuments?island=lanzarote"
            ),
            "monuments",
        )
        assert_record_island(
            monuments,
            "lanzarote",
            "monuments",
        )
        print("OK monuments Lanzarote")

        # 5. Events MUST NOT leak Tenerife
        events = assert_status(
            client.get(
                f"{base}/api/regions/canarias/"
                "events?island=lanzarote&limit=5"
            ),
            "events Lanzarote",
        )

        if events["available"] is not False:
            raise AssertionError(
                "Lanzarote events should be unavailable"
            )

        if events["items"]:
            raise AssertionError(
                "Lanzarote received Tenerife events"
            )

        print("OK no Tenerife events on Lanzarote")

        # 6. Webcams MUST NOT leak Tenerife
        webcams = assert_status(
            client.get(
                f"{base}/api/regions/canarias/"
                "webcams?island=lanzarote&limit=5"
            ),
            "webcams Lanzarote",
        )

        if webcams["available"] is not False:
            raise AssertionError(
                "Lanzarote webcams should be unavailable"
            )

        if webcams["items"]:
            raise AssertionError(
                "Lanzarote received Tenerife webcams"
            )

        print("OK no Tenerife webcams on Lanzarote")

        # 7. Tenerife events endpoint should be supported.
        tenerife_events = assert_status(
            client.get(
                f"{base}/api/regions/canarias/"
                "events?island=tenerife&limit=5"
            ),
            "events Tenerife",
        )

        if tenerife_events["available"] is not True:
            raise AssertionError(
                "Tenerife events should be available"
            )

        print("OK Tenerife events supported")

        # 8. Airports strict island filter
        airports = assert_status(
            client.get(
                f"{base}/api/regions/canarias/"
                "transport/airports?island=lanzarote"
            ),
            "airports",
        )
        assert_record_island(
            airports,
            "lanzarote",
            "airports",
        )
        print("OK airports Lanzarote")

        # 9. Ports filtered
        ports = assert_status(
            client.get(
                f"{base}/api/regions/canarias/"
                "ports?island=lanzarote"
            ),
            "ports",
        )

        for feature in ports["features"]:
            if (
                feature["properties"].get("island")
                != "lanzarote"
            ):
                raise AssertionError(
                    "Ports leaked another island"
                )

        print("OK ports Lanzarote")

        # 10. Ferry routes touching Lanzarote only
        ferries = assert_status(
            client.get(
                f"{base}/api/regions/canarias/"
                "ferries/routes?island=lanzarote"
            ),
            "ferries",
        )

        for route in ferries["routes"]:
            if "lanzarote" not in {
                route["origin_island"],
                route["destination_island"],
            }:
                raise AssertionError(
                    "Ferry filter leaked unrelated route"
                )

        print("OK ferries Lanzarote")

        # 11. GeoJSON endpoints: HTTP + filter metadata
        for endpoint in (
            "places",
            "beaches",
            "trails",
            "wildlife",
            "seismic",
        ):
            data = assert_status(
                client.get(
                    f"{base}/api/regions/canarias/"
                    f"{endpoint}?island=lanzarote&limit=5"
                    if endpoint != "seismic"
                    else
                    f"{base}/api/regions/canarias/"
                    "seismic?island=lanzarote"
                ),
                endpoint,
            )

            if data.get("type") != "FeatureCollection":
                raise AssertionError(
                    f"{endpoint}: not FeatureCollection"
                )

            print(
                f"OK {endpoint} Lanzarote "
                f"({len(data.get('features', []))} features)"
            )

        # 12. News are regional, not falsely Tenerife-labelled.
        news = assert_status(
            client.get(
                f"{base}/api/regions/canarias/"
                "news?island=lanzarote&limit=5"
            ),
            "news",
        )

        for item in news:
            if item.get("island") not in {
                None,
                "lanzarote",
            }:
                raise AssertionError(
                    "News leaked another island"
                )

        print("OK news regional/island-safe")

    print()
    print("ALL ISLAND CONTEXT TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
