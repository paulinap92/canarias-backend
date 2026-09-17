from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.rss import fetch_rss


NEWS_RSS_URL = "https://www3.gobiernodecanarias.org/noticias/feed"

# Official island/tourism sources. Each source is failure-isolated so one broken
# site never removes news from the rest of Canarias.
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
    {
        "id": "la-palma-cabildo",
        "url": "https://www.cabildodelapalma.es/es/noticias",
        "source": "Cabildo de La Palma",
        "island": "la-palma",
    },
    {
        "id": "la-gomera-cabildo",
        "url": "https://www.lagomera.es/noticias/1",
        "source": "Cabildo de La Gomera",
        "island": "la-gomera",
    },
    {
        "id": "el-hierro-cabildo",
        "url": "https://www.elhierro.es/es/noticias",
        "source": "Cabildo de El Hierro",
        "island": "el-hierro",
    },
    {
        "id": "fuerteventura-cabildo",
        "url": "https://www.cabildofuer.es/cabildo/noticias/",
        "source": "Cabildo de Fuerteventura",
        "island": "fuerteventura",
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
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
MONTH_WORD = "|".join(SPANISH_MONTHS)
TEXT_DATE_RE = re.compile(
    rf"(?P<day>\d{{1,2}})\s+(?:de\s+)?(?P<month>{MONTH_WORD}),?\s+(?:de\s+)?(?P<year>20\d{{2}})",
    re.IGNORECASE,
)
NUMERIC_DATE_RE = re.compile(
    r"(?<!\d)(?P<day>\d{1,2})[-/.](?P<month>\d{1,2})[-/.](?P<year>20\d{2})(?!\d)"
)
ISO_DATE_RE = re.compile(r"(?<!\d)(?P<year>20\d{2})-(?P<month>\d{2})-(?P<day>\d{2})(?!\d)")

ISLAND_TERMS = {
    "el-hierro": ("el hierro", "herreño", "herreña"),
    "la-palma": ("la palma", "palmero", "palmera"),
    "la-gomera": ("la gomera", "gomero", "gomera"),
    "tenerife": ("tenerife", "tinerfeño", "tinerfeña"),
    "gran-canaria": ("gran canaria", "grancanaria"),
    "fuerteventura": ("fuerteventura", "majorero", "majorera"),
    "lanzarote": ("lanzarote", "conejero", "conejera"),
    "la-graciosa": ("la graciosa", "graciosa"),
}


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _published_iso(text: str) -> str | None:
    text = text or ""
    match = TEXT_DATE_RE.search(text)
    try:
        if match is not None:
            value = datetime(
                int(match.group("year")),
                SPANISH_MONTHS[match.group("month").casefold()],
                int(match.group("day")),
                tzinfo=timezone.utc,
            )
            return value.isoformat()

        match = NUMERIC_DATE_RE.search(text)
        if match is not None:
            value = datetime(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
                tzinfo=timezone.utc,
            )
            return value.isoformat()

        match = ISO_DATE_RE.search(text)
        if match is not None:
            value = datetime(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
                tzinfo=timezone.utc,
            )
            return value.isoformat()
    except (KeyError, ValueError):
        return None
    return None


def _government_island(item: dict[str, Any]) -> str | None:
    text = _clean(
        " ".join(
            str(item.get(key) or "")
            for key in ("title", "summary", "description", "content", "url")
        )
    ).casefold()
    matches = [
        island
        for island, terms in ISLAND_TERMS.items()
        if any(term in text for term in terms)
    ]
    return matches[0] if len(matches) == 1 else None


def parse_html_news(
    html: str,
    *,
    base_url: str,
    source: str,
    island: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Parse title/date/summary cards from official news pages."""
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for heading in soup.find_all(["h2", "h3", "h4", "h5"]):
        title = _clean(heading.get_text(" ", strip=True))
        if not title or title.casefold() in {
            "noticias", "todas las noticias", "últimas noticias", "ultimas noticias"
        }:
            continue

        link = heading.find("a", href=True) or heading.find_parent("a", href=True)
        parent = heading.find_parent(["article", "li", "section"])
        if parent is None:
            parent = heading.find_parent("div")
        if link is None and parent is not None:
            link = parent.find("a", href=True)
        if link is None:
            continue

        url = urljoin(base_url, link.get("href", ""))
        key = url or title.casefold()
        if not url or key in seen:
            continue

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

    items.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return items


async def _fetch_html_source(config: dict[str, str], limit: int) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        timeout=25.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 Canarias-Cerca/1.0",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.7",
        },
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
            island = _government_island(item)
            item["scope"] = "island" if island else "canarias"
            item["island"] = island
        all_items.extend(government)
        status.append({"id": "gobierno-canarias", "ok": True, "count": len(government)})
    except Exception as exc:
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

    merged: dict[str, dict[str, Any]] = {}
    for item in all_items:
        key = str(item.get("url") or item.get("id") or item.get("title") or "").strip()
        if not key:
            continue
        if key not in merged:
            merged[key] = dict(item)
        else:
            old = merged[key]
            merged[key] = {**item, **{k: v for k, v in old.items() if v not in (None, "", [])}}

    items = list(merged.values())
    items.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return {
        "items": items[:limit],
        "available": bool(items),
        "source": "Gobierno de Canarias + cabildos y fuentes turísticas oficiales",
        "sources": status,
    }


async def fetch_news(limit: int = 20) -> list[dict[str, Any]]:
    """Compatibility helper used by older code/tests."""
    return (await fetch_news_bundle(limit))["items"]
