from typing import Any

from app.services.rss import fetch_rss


ALERTS_RSS_URL = (
    "https://www3.gobiernodecanarias.org/noticias/"
    "hemeroteca/category/alertas/feed"
)


def _alert_type(title: str) -> str:
    value = title.lower()
    mapping = {
        "costero": "coastal",
        "viento": "wind",
        "lluvia": "rain",
        "calima": "calima",
        "temperatura": "heat",
        "incendio": "fire",
        "tormenta": "storm",
    }

    for word, alert_type in mapping.items():
        if word in value:
            return alert_type

    return "other"


async def fetch_alerts(limit: int = 20) -> list[dict[str, Any]]:
    items = await fetch_rss(ALERTS_RSS_URL, limit)

    for item in items:
        item["type"] = _alert_type(item["title"])
        item["source"] = "Gobierno de Canarias"

    return items
