from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup


WEBCAMS_URL = (
    "https://www.webtenerife.com/"
    "galeria-multimedia/webcam/"
)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


async def fetch_tenerife_webcams(
    limit: int = 100,
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        headers={"User-Agent": "Canarias-Cerca/1.0"},
    ) as client:
        response = await client.get(WEBCAMS_URL)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    seen = set()

    for heading in soup.find_all(["h2", "h3"]):
        name = _clean(
            heading.get_text(" ", strip=True)
        )

        if not name:
            continue

        if name.lower() in {"webcam", "webcams"}:
            continue

        if name in seen or len(name) > 120:
            continue

        results.append(
            {
                "name": name,
                "island": "tenerife",
                "source": "Turismo de Tenerife",
                "source_page": WEBCAMS_URL,
            }
        )

        seen.add(name)

        if len(results) >= limit:
            break

    return results
