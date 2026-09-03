from typing import Any
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup


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
        })

    return result
