from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urljoin, urlparse
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup


AGENDA_URL = "https://www.webtenerife.com/agenda/"
CANARY_TZ = ZoneInfo("Atlantic/Canary")

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

DATE_RANGE_RE = re.compile(
    r"(?P<sd>\d{1,2})\s+"
    r"(?P<sm>enero|febrero|marzo|abril|mayo|junio|"
    r"julio|agosto|septiembre|octubre|noviembre|diciembre)"
    r"\s+(?P<sy>\d{4})\s*-\s*"
    r"(?P<ed>\d{1,2})\s+"
    r"(?P<em>enero|febrero|marzo|abril|mayo|junio|"
    r"julio|agosto|septiembre|octubre|noviembre|diciembre)"
    r"\s+(?P<ey>\d{4})",
    flags=re.IGNORECASE,
)

EVENT_PATH_RE = re.compile(
    r"/agenda/\d{4}/\d{2}/[^/]+/?$",
    flags=re.IGNORECASE,
)


def current_month() -> str:
    now = datetime.now(CANARY_TZ)
    return f"{now.year:04d}-{now.month:02d}"


def _clean(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _category(text: str) -> str:
    value = text.lower()

    mapping = [
        (
            (
                "romería",
                "romeria",
                "fiesta",
                "carnaval",
                "tradición",
                "tradicion",
            ),
            "fiesta",
        ),
        (
            (
                "concierto",
                "festival",
                "música",
                "musica",
                "dj",
                "salsa",
            ),
            "music",
        ),
        (
            (
                "teatro",
                "ópera",
                "opera",
                "danza",
                "ballet",
            ),
            "theatre",
        ),
        (
            (
                "humor",
                "cómica",
                "comica",
                "monólogo",
                "monologo",
            ),
            "comedy",
        ),
        (
            (
                "mercado",
                "feria",
                "artesanía",
                "artesania",
            ),
            "market",
        ),
        (
            (
                "gastronom",
                "vino",
                "tapa",
                "queso",
                "gastromercado",
            ),
            "food",
        ),
        (
            (
                "deporte",
                "carrera",
                "trail",
                "surf",
                "torneo",
                "waterpolo",
                "hyrox",
            ),
            "sport",
        ),
        (
            (
                "infantil",
                "familia",
                "niños",
                "ninos",
                "family",
            ),
            "family",
        ),
        (
            (
                "exposición",
                "exposicion",
                "museo",
                "cultura",
                "congreso",
            ),
            "culture",
        ),
    ]

    for words, category in mapping:
        if any(
            word in value
            for word in words
        ):
            return category

    return "other"


def _iso_date(
    day: str,
    month_name: str,
    year: str,
) -> str | None:
    try:
        value = datetime(
            int(year),
            MONTHS[month_name.lower()],
            int(day),
        )
    except (
        KeyError,
        ValueError,
    ):
        return None

    return value.date().isoformat()


def _date_range(
    text: str,
) -> tuple[
    str | None,
    str | None,
]:
    match = DATE_RANGE_RE.search(text)

    if match is None:
        return None, None

    start_date = _iso_date(
        match.group("sd"),
        match.group("sm"),
        match.group("sy"),
    )
    end_date = _iso_date(
        match.group("ed"),
        match.group("em"),
        match.group("ey"),
    )

    return start_date, end_date


def _title_from_url(url: str) -> str:
    slug = unquote(
        urlparse(url).path.rstrip("/").split("/")[-1]
    )

    value = slug.replace("-", " ")
    return value[:1].upper() + value[1:]


def _image_url(
    element: Any,
) -> str | None:
    if element is None:
        return None

    for attr in (
        "src",
        "data-src",
        "data-lazy-src",
        "data-original",
    ):
        value = element.get(attr)

        if value and not value.startswith("data:"):
            return urljoin(
                AGENDA_URL,
                value,
            )

    return None


def _parse_event_anchor(
    anchor: Any,
) -> dict[str, Any] | None:
    href = urljoin(
        AGENDA_URL,
        anchor.get("href", ""),
    )

    path = urlparse(href).path

    if not EVENT_PATH_RE.search(path):
        return None

    parent = anchor.find_parent(
        ["article", "li"]
    )

    if parent is None:
        parent = anchor.find_parent(
            "div"
        )

    context = _clean(
        (
            parent.get_text(
                " ",
                strip=True,
            )
            if parent is not None
            else anchor.get_text(
                " ",
                strip=True,
            )
        )
    )

    start_date, end_date = _date_range(
        context
    )

    if start_date is None:
        return None

    heading = None

    if parent is not None:
        heading = parent.find(
            ["h2", "h3", "h4"]
        )

    title = (
        _clean(
            heading.get_text(
                " ",
                strip=True,
            )
        )
        if heading is not None
        else ""
    )

    image = (
        parent.find("img")
        if parent is not None
        else None
    )

    image_alt = (
        _clean(
            image.get("alt", "")
        )
        if image is not None
        else ""
    )

    if (
        not title
        and image_alt
        and image_alt.lower()
        not in {
            "image",
            "imagen",
        }
    ):
        title = image_alt

    if not title:
        title = _title_from_url(
            href
        )

    summary = context

    match = DATE_RANGE_RE.search(
        summary
    )

    if match is not None:
        summary = (
            summary[: match.start()]
            + " "
            + summary[match.end() :]
        )

    summary = _clean(summary)

    if title:
        summary = _clean(
            summary.replace(
                title,
                "",
                1,
            )
        )

    return {
        "title": title[:250],
        "start_date": start_date,
        "end_date": end_date or start_date,
        "start_at": None,
        "end_at": None,
        "all_day": True,
        "category": _category(
            f"{title} {summary}"
        ),
        "location_name": None,
        "latitude": None,
        "longitude": None,
        "summary": (
            summary[:500]
            or None
        ),
        "image_url": _image_url(
            image
        ),
        "url": href,
        "island": "tenerife",
        "source": "Turismo de Tenerife",
    }


async def _fetch_page(
    client: httpx.AsyncClient,
    page_index: int,
) -> str:
    response = await client.get(
        AGENDA_URL,
        params={
            "page-index": page_index,
            "tab": 1,
        },
    )
    response.raise_for_status()
    return response.text


async def fetch_tenerife_events(
    limit: int = 100,
    month: str | None = None,
) -> list[dict[str, Any]]:
    # The current agenda is paginated. Fetching pages 1..3 is deliberate:
    # it captures the active/current agenda without scraping the full archive.
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Canarias-Cerca/1.0"
            ),
        },
    ) as client:
        pages = await asyncio.gather(
            *[
                _fetch_page(
                    client,
                    page_index,
                )
                for page_index in (
                    1,
                    2,
                    3,
                )
            ]
        )

    items: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for html in pages:
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        for anchor in soup.find_all(
            "a",
            href=True,
        ):
            item = _parse_event_anchor(
                anchor
            )

            if item is None:
                continue

            if item["url"] in seen_urls:
                continue

            if (
                month
                and not (
                    item["start_date"].startswith(month)
                    or item["end_date"].startswith(month)
                )
            ):
                continue

            seen_urls.add(
                item["url"]
            )
            items.append(item)

    items.sort(
        key=lambda item: (
            item["start_date"],
            item["title"],
        )
    )

    return items[:limit]
