from typing import Any

from app.services.rss import fetch_rss


NEWS_RSS_URL = (
    "https://www3.gobiernodecanarias.org/noticias/"
    "hemeroteca/feed"
)


async def fetch_news(
    limit: int = 20,
) -> list[dict[str, Any]]:
    items = await fetch_rss(
        NEWS_RSS_URL,
        limit,
    )

    for item in items:
        item["source"] = "Gobierno de Canarias"
        item["scope"] = "canarias"
        item["island"] = None

    return items
