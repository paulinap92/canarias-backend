from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


_IMAGE_CACHE: dict[str, str | None] = {}


def extract_page_image_url(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    selectors = (
        ('meta[property="og:image"]', "content"),
        ('meta[property="og:image:url"]', "content"),
        ('meta[name="twitter:image"]', "content"),
        ('meta[name="twitter:image:src"]', "content"),
        ('link[rel="image_src"]', "href"),
    )

    for selector, attribute in selectors:
        node = soup.select_one(selector)
        value = node.get(attribute) if node is not None else None
        if value:
            return urljoin(base_url, str(value))

    for image in soup.find_all("img"):
        value = (
            image.get("src")
            or image.get("data-src")
            or image.get("data-lazy-src")
            or image.get("data-original")
        )

        if not value and image.get("srcset"):
            candidates = [
                part.strip().split(" ")[0]
                for part in image.get("srcset", "").split(",")
                if part.strip()
            ]
            value = candidates[-1] if candidates else None

        if not value:
            continue

        value = str(value)
        if value.startswith("data:"):
            continue

        lower = value.casefold()
        if any(token in lower for token in ("logo", "icon", "avatar", "sprite", "favicon")):
            continue

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
