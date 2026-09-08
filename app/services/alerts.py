from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup


ALERTS_URL = (
    "https://www.gobiernodecanarias.org/"
    "emergencias/alertas/historial-alertas/"
)

ISLAND_NAMES: dict[str, tuple[str, ...]] = {
    "tenerife": ("tenerife",),
    "gran-canaria": ("gran canaria",),
    "lanzarote": ("lanzarote",),
    "fuerteventura": ("fuerteventura",),
    "la-palma": ("la palma",),
    "la-gomera": ("la gomera",),
    "el-hierro": ("el hierro",),
    "la-graciosa": ("la graciosa", "graciosa"),
}


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _alert_type(text: str) -> str:
    value = text.lower()
    mapping = [
        (("calima", "calimas"), "calima"),
        (("fenómenos costeros", "fenomenos costeros", "costeros"), "coastal"),
        (("viento", "vientos"), "wind"),
        (("lluvia", "lluvias"), "rain"),
        (("temperaturas máximas", "temperaturas maximas", "calor"), "heat"),
        (("incendios forestales", "incendio forestal"), "fire"),
        (("tormenta", "tormentas"), "storm"),
        (("nevadas", "nieve"), "snow"),
        (("desprendimientos",), "landslide"),
        (("contaminación marítima", "contaminacion maritima"), "marine_pollution"),
    ]
    for words, alert_type in mapping:
        if any(word in value for word in words):
            return alert_type
    return "other"


def _level(text: str) -> str:
    value = text.lower()
    if "alerta máxima" in value or "alerta maxima" in value:
        return "maximum_alert"
    if "prealerta" in value:
        return "prealert"
    if "alerta" in value:
        return "alert"
    return "unknown"


def _islands(text: str) -> list[str]:
    value = text.lower()
    result = [
        slug
        for slug, aliases in ISLAND_NAMES.items()
        if any(alias in value for alias in aliases)
    ]
    if not result and (
        "comunidad autónoma de canarias" in value
        or "comunidad autonoma de canarias" in value
        or "todas las islas" in value
    ):
        return list(ISLAND_NAMES.keys())
    return result


async def fetch_active_alerts(
    island: str | None = None,
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        timeout=25.0,
        follow_redirects=True,
        headers={"User-Agent": "Canarias-Cerca/1.0"},
    ) as client:
        response = await client.get(ALERTS_URL)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    chunks = re.split(
        r"(?=Descripción:)",
        text,
        flags=re.IGNORECASE,
    )

    result = []

    for chunk in chunks:
        if not re.search(
            r"Vigente:\s*SI\b",
            chunk,
            flags=re.IGNORECASE,
        ):
            continue

        description_match = re.search(
            r"Descripción:\s*(.*?)\s*Fecha:",
            chunk,
            flags=re.IGNORECASE | re.DOTALL,
        )
        date_match = re.search(
            r"Fecha:\s*(\d{2}/\d{2}/\d{4})",
            chunk,
            flags=re.IGNORECASE,
        )
        detail_match = re.search(
            r"Datos Alerta\s*(.*)",
            chunk,
            flags=re.IGNORECASE | re.DOTALL,
        )

        description = _clean(
            description_match.group(1)
            if description_match
            else ""
        )
        detail = _clean(
            detail_match.group(1)
            if detail_match
            else chunk
        )

        combined = f"{description} {detail}"
        islands = _islands(combined)

        item = {
            "title": description,
            "date": date_match.group(1) if date_match else None,
            "status": "active",
            "official_vigente": True,
            "type": _alert_type(combined),
            "level": _level(combined),
            "islands": islands,
            "summary": detail[:700] or None,
            "source": "Gobierno de Canarias - Dirección General de Emergencias",
            "url": ALERTS_URL,
        }

        if island and island not in islands:
            continue

        result.append(item)

    return result
