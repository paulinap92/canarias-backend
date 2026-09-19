from __future__ import annotations

import asyncio
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.content_images import (
    dev_remote_images_enabled,
    extract_page_image_url,
)
from app.services.places import _representative_coordinates
from app.utils.islands import normalize_island, overpass_bbox


SOURCE_BASE = "https://www.holaislascanarias.com"
LISTING_URL = SOURCE_BASE + "/piscinas-naturales/{island}/all/?limit=48"

OVERPASS_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 Canarias-Cerca/1.0",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.7",
}

GENERIC_WORDS = {
    "piscina", "piscinas", "natural", "naturales",
    "charco", "charcos", "de", "del", "la", "las", "el", "los", "y",
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalise(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _clean(value).casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _core(value: Any) -> str:
    return " ".join(
        word for word in _normalise(value).split()
        if word not in GENERIC_WORDS
    )


def _match_score(left: str, right: str) -> float:
    left_norm = _normalise(left)
    right_norm = _normalise(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0

    left_core = _core(left_norm)
    right_core = _core(right_norm)
    ratio = SequenceMatcher(None, left_norm, right_norm).ratio()
    core_ratio = (
        SequenceMatcher(None, left_core, right_core).ratio()
        if left_core and right_core
        else 0.0
    )

    left_tokens = set(left_core.split())
    right_tokens = set(right_core.split())
    union = left_tokens | right_tokens
    overlap = len(left_tokens & right_tokens) / len(union) if union else 0.0

    if left_core and right_core and (left_core in right_core or right_core in left_core):
        core_ratio = max(core_ratio, 0.9)

    return max(ratio, core_ratio, overlap)


def _listing_links(html: str, island: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    prefix = f"/piscinas-naturales/{island}/"
    links: list[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(SOURCE_BASE, str(anchor.get("href") or ""))
        path = urlparse(href).path
        if not path.startswith(prefix):
            continue
        if path.rstrip("/") == f"{prefix}all".rstrip("/"):
            continue
        if href in seen:
            continue
        seen.add(href)
        links.append(href)

    return links


def _description_from_page(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    subtitle_node = soup.find("h3")
    subtitle = _clean(subtitle_node.get_text(" ", strip=True)) if subtitle_node else None

    description = None
    if subtitle_node is not None:
        node = subtitle_node.find_next("p")
        if node is not None:
            description = _clean(node.get_text(" ", strip=True))

    if not description:
        meta = soup.select_one('meta[name="description"]')
        if meta and meta.get("content"):
            description = _clean(meta.get("content"))

    return subtitle or None, description or None


def parse_detail_page(html: str, url: str, island: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.find("h1")
    title = _clean(title_node.get_text(" ", strip=True)) if title_node else ""
    if not title:
        return None

    subtitle, description = _description_from_page(soup)
    image_url = (
        extract_page_image_url(html, url)
        if dev_remote_images_enabled()
        else None
    )

    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return {
        "id": f"natural-pool:{island}:{slug}",
        "name": title,
        "description": description,
        "short_description": subtitle,
        "category": "natural_pool",
        "source": "Hola Islas Canarias",
        "source_url": url,
        "website": url,
        "island": island,
        "image_url": image_url,
        "image_origin": "dev-source-preview" if image_url else None,
        "image_temporary": True if image_url else None,
        "image_rights_status": "unverified" if image_url else None,
    }


def _overpass_query(island: str) -> str:
    bbox = overpass_bbox(island)
    return f"""
[out:json][timeout:35];
(
  nwr["leisure"="swimming_pool"]["name"]({bbox});
  nwr["amenity"="public_bath"]["name"]({bbox});
  nwr["tourism"="attraction"]["name"~"Piscina|Charco|Caletón|Caleton",i]({bbox});
  nwr["natural"="water"]["name"~"Piscina|Charco|Caletón|Caleton",i]({bbox});
);
out center geom tags;
"""


async def _fetch_osm_candidates(
    client: httpx.AsyncClient,
    island: str,
) -> list[dict[str, Any]]:
    body = "data=" + quote_plus(_overpass_query(island))
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Canarias-Cerca/1.0",
    }
    last_error: Exception | None = None

    for endpoint in OVERPASS_URLS:
        try:
            response = await client.post(endpoint, content=body, headers=headers)
            response.raise_for_status()
            if "json" not in response.headers.get("content-type", "").casefold():
                continue
            payload = response.json()
            candidates = []
            for element in payload.get("elements", []):
                tags = element.get("tags") or {}
                name = tags.get("name:es") or tags.get("name")
                coordinates = _representative_coordinates(element)
                if not name or coordinates is None:
                    continue
                candidates.append({
                    "name": str(name),
                    "coordinates": coordinates,
                    "osm_id": element.get("id"),
                    "osm_type": element.get("type"),
                    "wheelchair": tags.get("wheelchair"),
                    "access": tags.get("access"),
                    "opening_hours": tags.get("opening_hours"),
                })
            return candidates
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc

    raise RuntimeError(f"All Overpass servers failed: {last_error}")


def best_osm_candidate(
    name: str,
    candidates: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, float]:
    best = None
    best_score = 0.0
    for candidate in candidates:
        score = _match_score(name, str(candidate.get("name") or ""))
        if score > best_score:
            best = candidate
            best_score = score

    if best_score < 0.64:
        return None, best_score
    return best, best_score


async def fetch_natural_pools(
    limit: int = 200,
    island: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_island(island)
    if normalized is None:
        return {
            "type": "FeatureCollection",
            "features": [],
            "available": False,
            "reason": "invalid_island",
        }

    listing_url = LISTING_URL.format(island=normalized)
    async with httpx.AsyncClient(
        timeout=35.0,
        follow_redirects=True,
        headers=BROWSER_HEADERS,
    ) as client:
        listing = await client.get(listing_url)
        listing.raise_for_status()
        detail_urls = _listing_links(listing.text, normalized)[:limit]

        semaphore = asyncio.Semaphore(6)

        async def read_detail(url: str) -> dict[str, Any] | None:
            async with semaphore:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                except httpx.HTTPError:
                    return None
            return parse_detail_page(response.text, str(response.url), normalized)

        details = await asyncio.gather(*(read_detail(url) for url in detail_urls))
        official_items = [item for item in details if item is not None]

        try:
            osm_candidates = await _fetch_osm_candidates(client, normalized)
        except Exception:
            osm_candidates = []

    features: list[dict[str, Any]] = []
    unmapped: list[dict[str, Any]] = []

    for item in official_items:
        candidate, score = best_osm_candidate(item["name"], osm_candidates)
        if candidate is None:
            unmapped.append({
                "name": item["name"],
                "source_url": item["source_url"],
                "match_score": round(score, 3),
            })
            continue

        longitude, latitude = candidate["coordinates"]
        properties = {
            **item,
            "osm_id": candidate.get("osm_id"),
            "osm_type": candidate.get("osm_type"),
            "osm_name": candidate.get("name"),
            "osm_match_score": round(score, 3),
            "wheelchair": candidate.get("wheelchair"),
            "access": candidate.get("access"),
            "opening_hours": candidate.get("opening_hours"),
        }
        properties = {
            key: value for key, value in properties.items()
            if value not in (None, "")
        }
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude],
            },
            "properties": properties,
        })

    features.sort(
        key=lambda feature: str(
            (feature.get("properties") or {}).get("name") or ""
        ).casefold()
    )

    return {
        "type": "FeatureCollection",
        "features": features,
        "available": True,
        "source": "Hola Islas Canarias + OpenStreetMap geometry",
        "source_url": listing_url,
        "official_discovered": len(official_items),
        "mapped_count": len(features),
        "unmapped_count": len(unmapped),
        "unmapped_items": unmapped,
    }
