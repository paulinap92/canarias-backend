from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


_IMAGE_CACHE: dict[str, str | None] = {}


def dev_remote_images_enabled() -> bool:
    return os.environ.get("CANARIAS_DEV_REMOTE_IMAGES", "1").strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _json_ld_image(value: Any) -> str | None:
    if isinstance(value, str):
        return value or None

    if isinstance(value, list):
        for item in value:
            image = _json_ld_image(item)
            if image:
                return image
        return None

    if not isinstance(value, dict):
        return None

    image = value.get("image")
    if image:
        if isinstance(image, dict):
            candidate = image.get("url") or image.get("contentUrl")
            if candidate:
                return str(candidate)
        candidate = _json_ld_image(image)
        if candidate:
            return candidate

    for key in ("thumbnailUrl", "contentUrl"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate

    graph = value.get("@graph")
    if graph:
        return _json_ld_image(graph)

    return None


def extract_page_image_url(html: str, base_url: str) -> str | None:
    """Return only an image explicitly declared as page metadata.

    Dev previews must never guess from arbitrary body <img> elements because
    generic site heroes/logos were being reused for unrelated Guide cards.
    """
    soup = BeautifulSoup(html, "html.parser")

    selectors = (
        ('meta[property="og:image"]', "content"),
        ('meta[property="og:image:url"]', "content"),
        ('meta[property="og:image:secure_url"]', "content"),
        ('meta[name="twitter:image"]', "content"),
        ('meta[name="twitter:image:src"]', "content"),
        ('link[rel="image_src"]', "href"),
    )

    for selector, attribute in selectors:
        node = soup.select_one(selector)
        value = node.get(attribute) if node is not None else None
        if value and not str(value).startswith("data:"):
            return urljoin(base_url, str(value))

    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

        value = _json_ld_image(payload)
        if value and not value.startswith("data:"):
            return urljoin(base_url, value)

    return None


async def resolve_content_image_url(item: dict[str, Any]) -> str | None:
    source_url = str(item.get("source_url") or item.get("url") or "").strip()
    if not source_url:
        return None

    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"}:
        return None

    if parsed.path.casefold().endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx")):
        return None

    if source_url in _IMAGE_CACHE:
        return _IMAGE_CACHE[source_url]

    try:
        async with httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 Canarias-Cerca/1.0",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.7",
            },
        ) as client:
            response = await client.get(source_url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "").casefold()
        if "html" not in content_type:
            _IMAGE_CACHE[source_url] = None
            return None

        image_url = extract_page_image_url(response.text, str(response.url))
        _IMAGE_CACHE[source_url] = image_url
        return image_url
    except Exception:
        _IMAGE_CACHE[source_url] = None
        return None
