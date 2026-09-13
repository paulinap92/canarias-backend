from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.rss import fetch_rss


# Primary archipelago-wide source. Additional sources are intentionally island
# specific and failure-isolated: one broken tourism website must not make the
# whole News refresh fail.
NEWS_RSS_URL = "https://www3.gobiernodecanarias.org/noticias/feed"

NEWS_HTML_SOURCES = [
    {
        "id": "tenerife-tourism",
        "url": "https://www.webtenerife.com/blogcorporativo/",
        "source": "Turismo de Tenerife",
        "island": "tenerife",
    },
    {
        "id": "gran-canaria-tourism",
        "url": "https://www.grancanaria.com/turismo/es/area-profesional/noticias/",
        "source": "Turismo de Gran Canaria",
        "island": "gran-canaria",
    },
    {
        "id": "lanzarote-tourism",
        "url": "https://corporativa.turismolanzarote.com/category/noticias/",
        "source": "Turismo Lanzarote",
        "island": "lanzarote",
    },
    {
        "id": "la-graciosa-tourism",
        "url": "https://www.visitlagraciosa.com/blog/",
        "source": "Visit La Graciosa",
        "island": "la-graciosa",
    },
]

SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
DATE_RE = re.compile(
    r"(?P<day>\d{1,2})\s+de\s+(?P<month>enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre),?\s+(?P<year>20\d{2})",
    re.IGNORECASE,
)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _published_iso(text: str) -> str | None:
    match = DATE_RE.search(text or "")
    if match is None:
        return None
    try:
        value = datetime(
            int(match.group("year")),
            SPANISH_MONTHS[match.group("month").casefold()],
            int(match.group("day")),
            tzinfo=timezone.utc,
        )
    except (KeyError, ValueError):
        return None
    return value.isoformat()


def parse_html_news(
    html: str,
    *,
    base_url: str,
    source: str,
    island: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Parse conservative title/date/summary cards from official news pages.

    It deliberately ignores blocks without a real heading + link. This is a
    fallback source adapter, not a general-purpose scraper.
    """
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for heading in soup.find_all(["h2", "h3", "h4"]):
        title = _clean(heading.get_text(" ", strip=True))
        if not title or title.casefold() in {"noticias", "todas las noticias", "últimas noticias"}:
            continue

        link = heading.find("a", href=True)
        if link is None:
            parent_link = heading.find_parent("a", href=True)
            link = parent_link
        if link is None:
            parent = heading.find_parent(["article", "li", "div"])
            link = parent.find("a", href=True) if parent is not None else None
        if link is None:
            continue

        url = urljoin(base_url, link.get("href", ""))
        key = url or title.casefold()
        if not url or key in seen:
            continue

        parent = heading.find_parent(["article", "li"])
        if parent is None:
            parent = heading.find_parent("div")
        context = _clean(parent.get_text(" ", strip=True) if parent is not None else title)
        published_at = _published_iso(context)

        summary = None
        if parent is not None:
            paragraph = parent.find("p")
            if paragraph is not None:
                value = _clean(paragraph.get_text(" ", strip=True))
                if value and value != title:
                    summary = value[:600]

        items.append(
            {
                "id": url,
                "title": title[:300],
                "summary": summary,
                "url": url,
                "published_at": published_at,
                "source": source,
                "scope": "island",
                "island": island,
            }
        )
        seen.add(key)
        if len(items) >= limit:
            break

    return items


async def _fetch_html_source(config: dict[str, str], limit: int) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        timeout=25.0,
        follow_redirects=True,
        headers={"User-Agent": "Canarias-Cerca/1.0"},
    ) as client:
        response = await client.get(config["url"])
        response.raise_for_status()
    return parse_html_news(
        response.text,
        base_url=config["url"],
        source=config["source"],
        island=config["island"],
        limit=limit,
    )


async def fetch_news_bundle(limit: int = 200) -> dict[str, Any]:
    status: list[dict[str, Any]] = []
    all_items: list[dict[str, Any]] = []

    try:
        government = await fetch_rss(NEWS_RSS_URL, limit)
        for item in government:
            item["source"] = "Gobierno de Canarias"
            item["scope"] = "canarias"
            item["island"] = None
        all_items.extend(government)
        status.append({"id": "gobierno-canarias", "ok": True, "count": len(government)})
    except Exception as exc:  # source failure is isolated
        status.append({"id": "gobierno-canarias", "ok": False, "error": str(exc)})

    results = await asyncio.gather(
        *[_fetch_html_source(config, min(limit, 80)) for config in NEWS_HTML_SOURCES],
        return_exceptions=True,
    )
    for config, result in zip(NEWS_HTML_SOURCES, results):
        if isinstance(result, Exception):
            status.append({"id": config["id"], "ok": False, "error": str(result)})
            continue
        all_items.extend(result)
        status.append({"id": config["id"], "ok": True, "count": len(result)})

    # Stable URL/id dedupe across sources. Prefer the first (primary source)
    # record but fill missing metadata from later source records.
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in all_items:
        key = str(item.get("url") or item.get("id") or item.get("title") or "").strip()
        if not key:
            continue
        if key not in merged:
            merged[key] = dict(item)
            order.append(key)
        else:
            old = merged[key]
            merged[key] = {**item, **{k: v for k, v in old.items() if v not in (None, "", [])}}

    items = [merged[key] for key in order]
    items.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return {
        "items": items[:limit],
        "available": bool(items),
        "source": "Gobierno de Canarias + fuentes turísticas oficiales",
        "sources": status,
    }


async def fetch_news(limit: int = 20) -> list[dict[str, Any]]:
    """Compatibility helper used by older code/tests."""
    return (await fetch_news_bundle(limit))["items"]
