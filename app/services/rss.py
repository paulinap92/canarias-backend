from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup


def _rss_image_url(item: Any, description_html: str, base_url: str) -> str | None:
    for node in item.iter():
        tag = str(node.tag).rsplit("}", 1)[-1].lower()
        candidate = node.attrib.get("url")
        media_type = str(node.attrib.get("type") or "").lower()
        if candidate and (
            tag == "thumbnail"
            or (tag in {"content", "enclosure"} and media_type.startswith("image/"))
        ):
            return urljoin(base_url, candidate)

    soup = BeautifulSoup(description_html, "html.parser")
    image = soup.find("img")
    if image is None:
        return None

    candidate = (
        image.get("src")
        or image.get("data-src")
        or image.get("data-lazy-src")
        or image.get("data-original")
    )
    if not candidate or str(candidate).startswith("data:"):
        return None

    return urljoin(base_url, str(candidate))


async def fetch_rss(url: str, limit: int = 20) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "Canarias-Cerca/1.0"})
        response.raise_for_status()

    root = ElementTree.fromstring(response.content)
    items = root.findall("./channel/item")
    result = []

    for item in items[:limit]:
        description_html = item.findtext("description") or ""
        description = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)

        result.append({
            "title": (item.findtext("title") or "").strip(),
            "published_at": (item.findtext("pubDate") or "").strip() or None,
            "url": (item.findtext("link") or "").strip() or None,
            "summary": description[:400] or None,
            "image_url": _rss_image_url(item, description_html, url),
        })

    return result
