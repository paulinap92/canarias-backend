from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils.islands import normalize_island


ROOT = Path(__file__).resolve().parents[2]

CONTENT_ROOT = ROOT / "data" / "guide" / "content"

VALID_SECTIONS = {
    "explore",
    "food",
    "culture",
    "music",
    "fiestas",
    "products",
    "stories",
    "crafts",
    "heritage",
    "history",
    "climate",
    "historical-weather",
    "geology",
    "nature",
    "experiences",
}


# Curated visual fallbacks used only when an editorial item has no image of its
# own. They keep the Guide/Explore experience visual without inventing factual
# item-specific photography. Existing image_url values always win.
ISLAND_IMAGE_FALLBACKS: dict[str, tuple[dict[str, str], ...]] = {
    "tenerife": (
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Teide%2C%20Roques%20de%20Garcia.jpg",
            "image_credit": "Ingo Mehling / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Teide,_Roques_de_Garcia.jpg",
        },
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Garachico%20%2832199%29.jpg",
            "image_credit": "Karmelo26 / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Garachico_(32199).jpg",
        },
    ),
    "gran-canaria": (
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Roque%20Nublo%2C%20gran%20canaria.JPG",
            "image_credit": "Donarreiskoffer / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Roque_Nublo,_gran_canaria.JPG",
        },
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Dunasmaspalomas.jpg",
            "image_credit": "Thomas Tolkien / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Dunasmaspalomas.jpg",
        },
    ),
    "lanzarote": (
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Timanfaya%20%2C%20Lanzarote.jpg",
            "image_credit": "Karmelo26 / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Timanfaya_,_Lanzarote.jpg",
        },
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Jameos%20del%20agua%20%28Lanzarote%29.jpg",
            "image_credit": "Tim Tim (VD fr) / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Jameos_del_agua_(Lanzarote).jpg",
        },
    ),
    "fuerteventura": (
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Dunas%20de%20Corralejo%2C%20Fuerteventura%2002.jpg",
            "image_credit": "Iván Hernández Cazorla / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Dunas_de_Corralejo,_Fuerteventura_02.jpg",
        },
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Islote%20de%20Lobos%20%28Fuerteventura%29.jpg",
            "image_credit": "Eafosan / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Islote_de_Lobos_(Fuerteventura).jpg",
        },
    ),
    "la-palma": (
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Caldera%20de%20Taburiente%20panorama.jpg",
            "image_credit": "Victor R. Ruiz / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Caldera_de_Taburiente_panorama.jpg",
        },
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Roque%20de%20los%20muchachos.jpg",
            "image_credit": "Tim Oberstebrink / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Roque_de_los_muchachos.jpg",
        },
    ),
    "la-gomera": (
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Garajonay%20La%20Gomera.jpg",
            "image_credit": "Arcy / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Garajonay_La_Gomera.jpg",
        },
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Valle%20Gran%20Rey.jpg",
            "image_credit": "Rwxrwxrwx / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Valle_Gran_Rey.jpg",
        },
    ),
    "el-hierro": (
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Sabinar%20de%20El%20Hierro.jpg",
            "image_credit": "Desde un tajinaste / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Sabinar_de_El_Hierro.jpg",
        },
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Charco%20Azul%20El%20Hierro.jpg",
            "image_credit": "Areuland / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Charco_Azul_El_Hierro.jpg",
        },
    ),
    "la-graciosa": (
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/La%20graciosa.jpg",
            "image_credit": "Halferitos / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:La_graciosa.jpg",
        },
        {
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Playa%20de%20Las%20Conchas%2C%20La%20Graciosa.jpg",
            "image_credit": "Artsuaga / Wikimedia Commons",
            "image_source_url": "https://commons.wikimedia.org/wiki/File:Playa_de_Las_Conchas,_La_Graciosa.jpg",
        },
    ),
}


def _has_image(item: dict[str, Any]) -> bool:
    return any(
        item.get(key)
        for key in (
            "image_url",
            "image",
            "photo_url",
            "thumbnail",
            "thumbnail_url",
            "cover_image",
            "hero_image",
        )
    )


def _add_missing_images(
    items: list[dict[str, Any]],
    *,
    island: str,
    section: str,
) -> list[dict[str, Any]]:
    fallbacks = ISLAND_IMAGE_FALLBACKS.get(island, ())
    if not fallbacks:
        return items

    # Stable rotation by section prevents every Guide chapter from repeating
    # exactly the same island image while remaining deterministic.
    offset = sum(ord(char) for char in section) % len(fallbacks)
    enriched: list[dict[str, Any]] = []

    for index, item in enumerate(items):
        current = dict(item)
        if not _has_image(current):
            fallback = fallbacks[(index + offset) % len(fallbacks)]
            current["image_url"] = fallback["image_url"]
            current["image_credit"] = fallback["image_credit"]
            current["image_source_url"] = fallback["image_source_url"]
            current["image_fallback"] = True
        enriched.append(current)

    return enriched


def _content_file(
    island: str,
    section: str,
) -> Path:
    return (
        CONTENT_ROOT
        / island
        / f"{section}.json"
    )


def get_content(
    island: str,
    section: str,
    *,
    limit: int = 50,
    featured_only: bool = False,
) -> dict[str, Any]:

    normalized_island = normalize_island(
        island
    )

    if normalized_island is None:
        return {
            "island": island,
            "section": section,
            "available": False,
            "reason": "invalid_island",
            "items": [],
        }

    if section not in VALID_SECTIONS:
        return {
            "island": normalized_island,
            "section": section,
            "available": False,
            "reason": "invalid_section",
            "items": [],
        }

    path = _content_file(
        normalized_island,
        section,
    )

    if not path.exists():
        return {
            "island": normalized_island,
            "section": section,
            "available": False,
            "reason": "content_not_created_yet",
            "items": [],
        }

    items = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if featured_only:
        items = [
            item
            for item in items
            if item.get("featured") is True
        ]

    items.sort(
        key=lambda item: (
            item.get("order", 9999),
            item.get("name")
            or item.get("title")
            or "",
        )
    )

    items = items[:limit]
    items = _add_missing_images(
        items,
        island=normalized_island,
        section=section,
    )

    return {
        "island": normalized_island,
        "section": section,
        "available": True,
        "count": len(items),
        "items": items,
    }


def get_content_item(
    island: str,
    section: str,
    slug: str,
) -> dict[str, Any] | None:

    data = get_content(
        island=island,
        section=section,
        limit=1000,
    )

    for item in data["items"]:

        if item.get("slug") == slug:
            return item

    return None