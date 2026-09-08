from __future__ import annotations

import argparse

import httpx


def get_json(
    client: httpx.Client,
    base: str,
    path: str,
):
    response = client.get(
        f"{base}{path}"
    )

    if response.status_code != 200:
        raise AssertionError(
            f"{path}: HTTP "
            f"{response.status_code} "
            f"{response.text[:400]}"
        )

    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--base",
        default="http://127.0.0.1:8000",
    )

    args = parser.parse_args()
    base = args.base.rstrip("/")

    with httpx.Client(
        timeout=120.0,
        follow_redirects=True,
    ) as client:

        explore = get_json(
            client,
            base,
            (
                "/api/regions/canarias/"
                "explore?island=tenerife"
            ),
        )

        assert explore[
            "available"
        ] is True

        assert (
            3
            <= explore["count"]
            <= 6
        )

        required = {
            "id",
            "slug",
            "name",
            "island",
            "category",
            "latitude",
            "longitude",
            "short_description",
            "description",
            "image_url",
            "image_credit",
            "source_url",
            "featured",
            "order",
        }

        for item in explore["items"]:
            missing = (
                required
                - item.keys()
            )

            assert not missing, (
                f"Explore item missing "
                f"{missing}: {item}"
            )

        print(
            "OK Explore Tenerife:",
            explore["count"],
            "display-ready items",
        )

        calendar = get_json(
            client,
            base,
            (
                "/api/regions/canarias/"
                "events/calendar"
                "?island=tenerife"
            ),
        )

        assert calendar[
            "available"
        ] is True

        assert calendar[
            "calendar_ready"
        ] is True

        assert "days" in calendar

        for day, events in (
            calendar["days"].items()
        ):
            assert len(day) == 10

            for event in events:
                assert event[
                    "start_date"
                ]
                assert event[
                    "end_date"
                ]
                assert event[
                    "title"
                ]
                assert event[
                    "source"
                ]

        print(
            "OK Calendar Tenerife:",
            calendar[
                "events_count"
            ],
            "events",
        )

        no_leak = get_json(
            client,
            base,
            (
                "/api/regions/canarias/"
                "events/calendar"
                "?island=lanzarote"
            ),
        )

        assert no_leak[
            "available"
        ] is False

        assert (
            no_leak["days"]
            == {}
        )

        print(
            "OK no Tenerife "
            "events leak to Lanzarote"
        )

    print()
    print(
        "ALL SCROLLYTELLING "
        "BACKEND TESTS PASSED"
    )


if __name__ == "__main__":
    main()
