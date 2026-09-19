from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.content_images import (
    dev_remote_images_enabled,
    extract_page_image_url,
)
from app.services.places import _representative_coordinates
from app.utils.islands import normalize_island, overpass_bbox


SOURCE_BASE = "https://www.holaislascanarias.com"

DIRECTORIES = {
    "marinas": {
        "section": "puertos-y-marinas",
        "source": "Hola Islas Canarias",
    },
    "food-producers": {
        "section": "bodegas-y-queserias",
        "source": "Hola Islas Canarias",
    },
}

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 Canarias-Cerca/1.0",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.7",
}

OVERPASS_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalise(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _clean(value).casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _match_score(left: str, right: str) -> float:
    a = _normalise(left)
    b = _normalise(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    ratio = SequenceMatcher(None, a, b).ratio()
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    union = a_tokens | b_tokens
    overlap = len(a_tokens & b_tokens) / len(union) if union else 0.0

    if a in b or b in a:
        ratio = max(ratio, 0.9)

    return max(ratio, overlap)


def _listing_url(resource: str, island: str) -> str:
    section = DIRECTORIES[resource]["section"]
    return f"{SOURCE_BASE}/{section}/{island}/?limit=48"


def _listing_links(html: str, resource: str, island: str) -> list[str]:
    section = DIRECTORIES[resource]["section"]
    prefix = f"/{section}/{island}/"
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(SOURCE_BASE, str(anchor.get("href") or ""))
        path = urlparse(href).path
        if not path.startswith(prefix):
            continue
        parts = [part for part in path.strip("/").split("/") if part]
        if len(parts) != 3:
            continue
        if parts[-1] == "all":
            continue
        if href in seen:
            continue
        seen.add(href)
        links.append(href)

    return links


def _json_ld_coordinates(value: Any) -> tuple[float, float] | None:
    if isinstance(value, list):
        for item in value:
            result = _json_ld_coordinates(item)
            if result is not None:
                return result
        return None

    if not isinstance(value, dict):
        return None

    geo = value.get("geo")
    if isinstance(geo, dict):
        latitude = geo.get("latitude")
        longitude = geo.get("longitude")
        try:
            if latitude is not None and longitude is not None:
                return float(longitude), float(latitude)
        except (TypeError, ValueError):
            pass

    for nested in value.values():
        if isinstance(nested, (dict, list)):
            result = _json_ld_coordinates(nested)
            if result is not None:
                return result
    return None


def _map_coordinates(soup: BeautifulSoup) -> tuple[float, float] | None:
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        result = _json_ld_coordinates(payload)
        if result is not None:
            return result

    number = r"(-?\d{1,3}(?:\.\d+)?)"
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "")
        if "google." not in href and "maps." not in href:
            continue

        parsed = urlparse(href)
        query = parse_qs(parsed.query)
        for key in ("q", "query", "ll"):
            if key not in query:
                continue
            match = re.search(number + r"\s*,\s*" + number, query[key][0])
            if match:
                return float(match.group(2)), float(match.group(1))

        match = re.search(r"/@" + number + r"," + number, href)
        if match:
            return float(match.group(2)), float(match.group(1))

    return None


def _description(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    subtitle_node = soup.find("h3")
    subtitle = _clean(subtitle_node.get_text(" ", strip=True)) if subtitle_node else None

    description = None
    if subtitle_node is not None:
        paragraph = subtitle_node.find_next("p")
        if paragraph is not None:
            description = _clean(paragraph.get_text(" ", strip=True))

    if not description:
        meta = soup.select_one('meta[name="description"]')
        if meta and meta.get("content"):
            description = _clean(meta.get("content"))

    return subtitle or None, description or None


def _food_category(title: str, text: str) -> str:
    haystack = _normalise(f"{title} {text}")
    cheese_words = ("queseria", "queso", "granja", "lacteo")
    if any(word in haystack for word in cheese_words):
        return "cheese_dairy"
    return "winery"


def parse_directory_detail(
    html: str,
    url: str,
    resource: str,
    island: str,
) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.find("h1")
    title = _clean(title_node.get_text(" ", strip=True)) if title_node else ""
    if not title:
        return None

    subtitle, description = _description(soup)
    coordinates = _map_coordinates(soup)

    category = "marina"
    if resource == "food-producers":
        category = _food_category(title, f"{subtitle or ''} {description or ''}")

    image_url = (
        extract_page_image_url(html, url)
        if dev_remote_images_enabled()
        else None
    )

    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return {
        "id": f"{resource}:{island}:{slug}",
        "name": title,
        "description": description,
        "short_description": subtitle,
        "category": category,
        "source": DIRECTORIES[resource]["source"],
        "source_url": url,
        "website": url,
        "island": island,
        "coordinates": coordinates,
        "image_url": image_url,
        "image_origin": "dev-source-preview" if image_url else None,
        "image_temporary": True if image_url else None,
        "image_rights_status": "unverified" if image_url else None,
    }


def _osm_query(resource: str, island: str) -> str:
    bbox = overpass_bbox(island)

    if resource == "marinas":
        selectors = f"""
  nwr["leisure"="marina"]["name"]({bbox});
  nwr["harbour"]["name"]({bbox});
  nwr["seamark:type"="harbour"]["name"]({bbox});
  nwr["amenity"="ferry_terminal"]["name"]({bbox});
"""
    elif resource == "food-producers":
        selectors = f"""
  nwr["craft"="winery"]["name"]({bbox});
  nwr["shop"="wine"]["name"]({bbox});
  nwr["amenity"="winery"]["name"]({bbox});
  nwr["craft"="cheese"]["name"]({bbox});
  nwr["shop"="cheese"]["name"]({bbox});
  nwr["produce"~"wine|cheese",i]["name"]({bbox});
"""
    else:
        raise ValueError(f"Unsupported directory resource: {resource}")

    return f"""
[out:json][timeout:35];
(
{selectors}
);
out center geom tags;
"""


async def _osm_candidates(
    client: httpx.AsyncClient,
    resource: str,
    island: str,
) -> list[dict[str, Any]]:
    body = "data=" + quote_plus(_osm_query(resource, island))
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
            candidates: list[dict[str, Any]] = []
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
                    "website": tags.get("website"),
                })
            return candidates
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc

    raise RuntimeError(f"All Overpass servers failed: {last_error}")


def _best_candidate(
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
    return (best, best_score) if best_score >= 0.62 else (None, best_score)


async def fetch_official_directory(
    resource: str,
    *,
    island: str | None,
    limit: int = 200,
) -> dict[str, Any]:
    if resource not in DIRECTORIES:
        raise ValueError(f"Unsupported resource: {resource}")

    normalized = normalize_island(island)
    if normalized is None:
        return {
            "type": "FeatureCollection",
            "features": [],
            "available": False,
            "reason": "invalid_island",
        }

    listing_url = _listing_url(resource, normalized)
    async with httpx.AsyncClient(
        timeout=35.0,
        follow_redirects=True,
        headers=BROWSER_HEADERS,
    ) as client:
        listing = await client.get(listing_url)
        listing.raise_for_status()
        detail_urls = _listing_links(
            listing.text,
            resource,
            normalized,
        )[:limit]

        semaphore = asyncio.Semaphore(6)

        async def fetch_detail(url: str) -> dict[str, Any] | None:
            async with semaphore:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                except httpx.HTTPError:
                    return None
            return parse_directory_detail(
                response.text,
                str(response.url),
                resource,
                normalized,
            )

        details = await asyncio.gather(*(fetch_detail(url) for url in detail_urls))
        official_items = [item for item in details if item is not None]

        try:
            candidates = await _osm_candidates(client, resource, normalized)
        except Exception:
            candidates = []

    features: list[dict[str, Any]] = []
    unmapped: list[dict[str, Any]] = []

    for item in official_items:
        coordinates = item.pop("coordinates", None)
        candidate = None
        score = 1.0 if coordinates is not None else 0.0

        if coordinates is None:
            candidate, score = _best_candidate(item["name"], candidates)
            if candidate is not None:
                coordinates = candidate["coordinates"]

        if coordinates is None:
            unmapped.append({
                "name": item["name"],
                "source_url": item["source_url"],
                "match_score": round(score, 3),
            })
            continue

        properties = dict(item)
        if candidate is not None:
            properties["osm_id"] = candidate.get("osm_id")
            properties["osm_type"] = candidate.get("osm_type")
            properties["osm_match_score"] = round(score, 3)

        properties = {
            key: value
            for key, value in properties.items()
            if value not in (None, "")
        }

        longitude, latitude = coordinates
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(longitude), float(latitude)],
            },
            "properties": properties,
        })

    features.sort(
        key=lambda feature: _normalise(
            (feature.get("properties") or {}).get("name")
        )
    )

    return {
        "type": "FeatureCollection",
        "features": features,
        "available": True,
        "source": f"{DIRECTORIES[resource]['source']} + map coordinates",
        "source_url": listing_url,
        "official_discovered": len(official_items),
        "mapped_count": len(features),
        "unmapped_count": len(unmapped),
        "unmapped_items": unmapped,
    }


def _terrain_query(resource: str, island: str) -> str:
    bbox = overpass_bbox(island)
    natural = "volcano" if resource == "volcanoes" else "peak"
    return f"""
[out:json][timeout:35];
nwr["natural"="{natural}"]["name"]({bbox});
out center geom tags;
"""


def _elevation(tags: dict[str, Any]) -> float | None:
    raw = str(tags.get("ele") or "").replace(",", ".").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _terrain_score(resource: str, tags: dict[str, Any]) -> float:
    score = 0.0
    if tags.get("wikipedia"):
        score += 100
    if tags.get("wikidata"):
        score += 70
    if tags.get("name:es"):
        score += 8

    elevation = _elevation(tags)
    if elevation is not None:
        score += max(0.0, elevation) / 100.0

    if resource == "volcanoes":
        name = _normalise(tags.get("name"))
        for keyword in (
            "teide", "pico viejo", "teneguia", "tajogaite", "san antonio",
            "chinyero", "arenas negras", "cuervo", "corona", "timanfaya",
        ):
            if keyword in name:
                score += 80

    return score


async def fetch_terrain_features(
    resource: str,
    *,
    island: str | None,
    limit: int = 40,
) -> dict[str, Any]:
    if resource not in {"volcanoes", "summits"}:
        raise ValueError(f"Unsupported terrain resource: {resource}")

    normalized = normalize_island(island)
    if normalized is None:
        return {
            "type": "FeatureCollection",
            "features": [],
            "available": False,
            "reason": "invalid_island",
        }

    body = "data=" + quote_plus(_terrain_query(resource, normalized))
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Canarias-Cerca/1.0",
    }

    payload = None
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        for endpoint in OVERPASS_URLS:
            try:
                response = await client.post(endpoint, content=body, headers=headers)
                response.raise_for_status()
                if "json" not in response.headers.get("content-type", "").casefold():
                    continue
                payload = response.json()
                break
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc

    if payload is None:
        raise RuntimeError(f"All Overpass servers failed: {last_error}")

    candidates: list[tuple[float, dict[str, Any]]] = []
    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        name = tags.get("name:es") or tags.get("name")
        coordinates = _representative_coordinates(element)
        if not name or coordinates is None:
            continue

        score = _terrain_score(resource, tags)
        elevation = _elevation(tags)

        if resource == "summits":
            # Cumbres is an editorial discovery list, not every named hill.
            # Keep notable peaks or clearly high summits for the island.
            if not tags.get("wikipedia") and not tags.get("wikidata"):
                threshold = {
                    "tenerife": 1800,
                    "gran-canaria": 1400,
                    "la-palma": 1400,
                    "la-gomera": 900,
                    "el-hierro": 900,
                    "lanzarote": 500,
                    "fuerteventura": 600,
                    "la-graciosa": 200,
                }.get(normalized, 1000)
                if elevation is None or elevation < threshold:
                    continue

        if resource == "volcanoes" and score < 5:
            continue

        longitude, latitude = coordinates
        category = "volcano" if resource == "volcanoes" else "summit"
        hiking_url = f"{SOURCE_BASE}/senderos/{normalized}/"
        props = {
            "id": f"osm:{element.get('type')}:{element.get('id')}",
            "osm_id": element.get("id"),
            "osm_type": element.get("type"),
            "name": name,
            "category": category,
            "island": normalized,
            "elevation_m": elevation,
            "wikipedia": tags.get("wikipedia"),
            "wikidata": tags.get("wikidata"),
            "source": "OpenStreetMap",
            "official_hiking_url": hiking_url if resource == "summits" else None,
            "access_notes": (
                "Cumbre de referencia. Consulta una ruta oficial y restricciones antes de subir."
                if resource == "summits"
                else None
            ),
            "importance_score": round(score, 1),
        }
        props = {
            key: value
            for key, value in props.items()
            if value not in (None, "")
        }
        candidates.append((
            score,
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [longitude, latitude],
                },
                "properties": props,
            },
        ))

    candidates.sort(
        key=lambda pair: (
            -pair[0],
            _normalise((pair[1].get("properties") or {}).get("name")),
        )
    )
    features = [feature for _, feature in candidates[:limit]]

    return {
        "type": "FeatureCollection",
        "features": features,
        "available": True,
        "source": "OpenStreetMap",
        "reference_source": (
            "IGN Volcanología"
            if resource == "volcanoes"
            else "Hola Islas Canarias · Senderos"
        ),
        "reference_url": (
            "https://www.ign.es/web/vlc-area-volcanologia"
            if resource == "volcanoes"
            else f"{SOURCE_BASE}/senderos/{normalized}/"
        ),
    }
