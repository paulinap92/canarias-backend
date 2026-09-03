from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


EVENTS_URL = "https://www.webtenerife.com/agenda/"


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


async def fetch_tenerife_events(
    limit: int = 30,
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        timeout=25.0,
        follow_redirects=True,
        headers={"User-Agent": "Canarias-Cerca/1.0"},
    ) as client:
        response = await client.get(EVENTS_URL)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(EVENTS_URL, anchor["href"])
        parsed = urlparse(href)
        path = parsed.path.rstrip("/")

        if "/agenda/" not in path:
            continue

        if path.endswith("/agenda"):
            continue

        if href in seen_urls:
            continue

        title = _clean(
            anchor.get_text(" ", strip=True)
        )

        if len(title) < 3:
            continue

        parent = anchor.find_parent(
            ["article", "li", "div"]
        )

        context = (
            _clean(parent.get_text(" ", strip=True))
            if parent is not None
            else title
        )

        results.append(
            {
                "title": title[:250],
                "summary": (
                    context[:500]
                    if context != title
                    else None
                ),
                "url": href,
                "island": "tenerife",
                "source": "Turismo de Tenerife",
            }
        )

        seen_urls.add(href)

        if len(results) >= limit:
            break

    return results
