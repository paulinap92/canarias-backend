from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urljoin, urlparse
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup


CANARY_TZ = ZoneInfo("Atlantic/Canary")
TENERIFE_AGENDA_URL = "https://www.webtenerife.com/agenda/"
AGENDA_URL = TENERIFE_AGENDA_URL  # compatibility with older tests/imports

EVENT_SOURCES: dict[str, dict[str, str]] = {
    "tenerife": {
        "id": "tenerife-tourism",
        "url": TENERIFE_AGENDA_URL,
        "source": "Turismo de Tenerife",
        "parser": "tenerife",
    },
    "gran-canaria": {
        "id": "gran-canaria-tourism",
        "url": "https://turismo.grancanaria.com/turismo/es/agenda/agenda/",
        "source": "Turismo de Gran Canaria",
        "parser": "generic",
    },
    "lanzarote": {
        "id": "lanzarote-tourism",
        "url": "https://turismolanzarote.com/agenda-de-eventos/",
        "source": "Turismo Lanzarote",
        "parser": "generic",
    },
    "fuerteventura": {
        "id": "fuerteventura-tourism",
        "url": "https://www.visitfuerteventura.com/eventos/fuerteventura/",
        "source": "Visit Fuerteventura",
        "parser": "generic",
    },
    "la-palma": {
        "id": "la-palma-tourism",
        "url": "https://visitlapalma.es/eventos/la-palma/",
        "source": "Visit La Palma",
        "parser": "generic",
    },
    "la-gomera": {
        "id": "la-gomera-tourism",
        "url": "https://lagomera.travel/eventos/la-gomera/",
        "source": "La Gomera Travel",
        "parser": "generic",
    },
    "el-hierro": {
        "id": "el-hierro-tourism",
        "url": "https://elhierro.travel/eventos/el-hierro/",
        "source": "El Hierro Travel",
        "parser": "generic",
    },
    "la-graciosa": {
        "id": "la-graciosa-tourism",
        "url": "https://www.visitlagraciosa.com/calendario-de-eventos/",
        "source": "Visit La Graciosa",
        "parser": "generic",
    },
}

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
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
MONTH_WORD = "|".join(MONTHS)

# WebTenerife uses full ranges such as "5 septiembre 2026 - 8 septiembre 2026".
DATE_RANGE_RE = re.compile(
    rf"(?P<sd>\d{{1,2}})\s+(?P<sm>{MONTH_WORD})\s+(?P<sy>\d{{4}})\s*-\s*"
    rf"(?P<ed>\d{{1,2}})\s+(?P<em>{MONTH_WORD})\s+(?P<ey>\d{{4}})",
    flags=re.IGNORECASE,
)
EVENT_PATH_RE = re.compile(r"/agenda/\d{4}/\d{2}/[^/]+/?$", flags=re.IGNORECASE)

NUMERIC_RANGE_RE = re.compile(
    r"(?P<sd>\d{1,2})[/.](?P<sm>\d{1,2})[/.](?P<sy>20\d{2})"
    r"\s*(?:-|–|—|al)\s*"
    r"(?P<ed>\d{1,2})[/.](?P<em>\d{1,2})[/.](?P<ey>20\d{2})",
    re.IGNORECASE,
)
NUMERIC_SINGLE_RE = re.compile(
    r"(?<!\d)(?P<d>\d{1,2})[/.](?P<m>\d{1,2})[/.](?P<y>20\d{2})(?!\d)"
)
TEXT_RANGE_RE = re.compile(
    rf"(?P<sd>\d{{1,2}})\s*(?:al|a|-|–|—)\s*(?P<ed>\d{{1,2}})\s+"
    rf"(?P<m>{MONTH_WORD})(?:\s+(?P<y>20\d{{2}}))?",
    re.IGNORECASE,
)
TEXT_SINGLE_RE = re.compile(
    rf"(?P<d>\d{{1,2}})\s+(?:de\s+)?(?P<m>{MONTH_WORD})"
    rf"(?:\s*(?:de|,)?\s*(?P<y>20\d{{2}}))?",
    re.IGNORECASE,
)
TEXT_CROSS_MONTH_RE = re.compile(
    rf"(?P<sd>\d{{1,2}})\s+(?P<sm>{MONTH_WORD})\s*(?:20\d{{2}})?\s*"
    rf"(?:-|–|—|al)\s*(?P<ed>\d{{1,2}})\s+(?P<em>{MONTH_WORD})\s+(?P<y>20\d{{2}})",
    re.IGNORECASE,
)


def current_month() -> str:
    now = datetime.now(CANARY_TZ)
    return f"{now.year:04d}-{now.month:02d}"


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _category(text: str) -> str:
    value = text.casefold()
    mapping = [
        (("romería", "romeria", "fiesta", "carnaval", "tradición", "tradicion"), "fiesta"),
        (("concierto", "festival", "música", "musica", " dj ", "salsa"), "music"),
        (("teatro", "ópera", "opera", "danza", "ballet"), "theatre"),
        (("humor", "cómica", "comica", "monólogo", "monologo"), "comedy"),
        (("mercado", "feria", "artesanía", "artesania"), "market"),
        (("gastronom", "vino", "tapa", "queso", "gastromercado"), "food"),
        (("deporte", "carrera", "trail", "surf", "torneo", "waterpolo", "hyrox"), "sport"),
        (("infantil", "familia", "niños", "ninos", "family"), "family"),
        (("exposición", "exposicion", "museo", "cultura", "congreso"), "culture"),
    ]
    for words, category in mapping:
        if any(word in value for word in words):
            return category
    return "other"


def _safe_date(year: int, month: int, day: int) -> str | None:
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def _iso_date(day: str, month_name: str, year: str) -> str | None:
    month = MONTHS.get(month_name.casefold())
    return _safe_date(int(year), month or 0, int(day))


def _infer_year(month_number: int, reference_year: int | None = None) -> int:
    now = datetime.now(CANARY_TZ)
    year = reference_year or now.year
    # Agenda pages commonly omit the year for upcoming dates. Around year end,
    # January/February items belong to the following year.
    if reference_year is None and now.month >= 10 and month_number <= 3:
        year += 1
    return year


def parse_event_dates(text: str, reference_year: int | None = None) -> tuple[str | None, str | None, str | None]:
    """Return (start_date, end_date, schedule_text) for common Canary agendas.

    The original human-facing date text is retained as schedule_text so recurring
    or partially specified dates are never silently converted into false precision.
    """
    text = _clean(text)
    if not text:
        return None, None, None

    match = DATE_RANGE_RE.search(text)
    if match:
        start = _iso_date(match.group("sd"), match.group("sm"), match.group("sy"))
        end = _iso_date(match.group("ed"), match.group("em"), match.group("ey"))
        return start, end or start, match.group(0)

    match = NUMERIC_RANGE_RE.search(text)
    if match:
        start = _safe_date(int(match.group("sy")), int(match.group("sm")), int(match.group("sd")))
        end = _safe_date(int(match.group("ey")), int(match.group("em")), int(match.group("ed")))
        return start, end or start, match.group(0)

    match = TEXT_CROSS_MONTH_RE.search(text)
    if match:
        sm = MONTHS[match.group("sm").casefold()]
        em = MONTHS[match.group("em").casefold()]
        year = int(match.group("y"))
        start = _safe_date(year, sm, int(match.group("sd")))
        end = _safe_date(year, em, int(match.group("ed")))
        return start, end or start, match.group(0)

    match = TEXT_RANGE_RE.search(text)
    if match:
        month = MONTHS[match.group("m").casefold()]
        year = int(match.group("y")) if match.group("y") else _infer_year(month, reference_year)
        start = _safe_date(year, month, int(match.group("sd")))
        end = _safe_date(year, month, int(match.group("ed")))
        return start, end or start, match.group(0)

    match = NUMERIC_SINGLE_RE.search(text)
    if match:
        start = _safe_date(int(match.group("y")), int(match.group("m")), int(match.group("d")))
        return start, start, match.group(0)

    match = TEXT_SINGLE_RE.search(text)
    if match:
        month = MONTHS[match.group("m").casefold()]
        year = int(match.group("y")) if match.group("y") else _infer_year(month, reference_year)
        start = _safe_date(year, month, int(match.group("d")))
        return start, start, match.group(0)

    recurrence = re.search(
        r"(?:todos?|cada)\s+(?:los\s+)?(?:lunes|martes|miércoles|miercoles|jueves|viernes|sábados|sabados|domingos)",
        text,
        re.IGNORECASE,
    )
    if recurrence:
        return None, None, recurrence.group(0)

    return None, None, None


def _date_range(text: str) -> tuple[str | None, str | None]:
    start, end, _ = parse_event_dates(text)
    return start, end


def _title_from_url(url: str) -> str:
    slug = unquote(urlparse(url).path.rstrip("/").split("/")[-1])
    value = slug.replace("-", " ")
    return value[:1].upper() + value[1:]


def _image_url(element: Any, base_url: str = TENERIFE_AGENDA_URL) -> str | None:
    if element is None:
        return None
    for attr in ("src", "data-src", "data-lazy-src", "data-original"):
        value = element.get(attr)
        if value and not value.startswith("data:"):
            return urljoin(base_url, value)
    return None


def _parse_event_anchor(anchor: Any) -> dict[str, Any] | None:
    """WebTenerife-specific parser kept for its stable agenda structure."""
    href = urljoin(TENERIFE_AGENDA_URL, anchor.get("href", ""))
    if not EVENT_PATH_RE.search(urlparse(href).path):
        return None

    parent = anchor.find_parent(["article", "li"]) or anchor.find_parent("div")
    context = _clean(parent.get_text(" ", strip=True) if parent is not None else anchor.get_text(" ", strip=True))
    start_date, end_date, schedule_text = parse_event_dates(context)
    if start_date is None:
        return None

    heading = parent.find(["h2", "h3", "h4"]) if parent is not None else None
    title = _clean(heading.get_text(" ", strip=True)) if heading is not None else ""
    image = parent.find("img") if parent is not None else None
    image_alt = _clean(image.get("alt", "")) if image is not None else ""
    if not title and image_alt.casefold() not in {"", "image", "imagen"}:
        title = image_alt
    if not title:
        title = _title_from_url(href)

    summary = context
    if schedule_text:
        summary = summary.replace(schedule_text, " ", 1)
    if title:
        summary = summary.replace(title, " ", 1)
    summary = _clean(summary)

    return {
        "id": href,
        "title": title[:250],
        "start_date": start_date,
        "end_date": end_date or start_date,
        "schedule_text": schedule_text,
        "start_at": None,
        "end_at": None,
        "all_day": True,
        "category": _category(f"{title} {summary}"),
        "location_name": None,
        "latitude": None,
        "longitude": None,
        "summary": summary[:500] or None,
        "image_url": _image_url(image),
        "url": href,
        "island": "tenerife",
        "source": "Turismo de Tenerife",
        "source_id": "tenerife-tourism",
    }


def _candidate_block(heading: Any) -> Any:
    return heading.find_parent(["article", "li", "section"]) or heading.find_parent("div") or heading


def parse_generic_events(
    html: str,
    *,
    base_url: str,
    source: str,
    source_id: str,
    island: str,
    month: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Conservative adapter for official island tourism agendas.

    Only blocks with a real heading/link and a parseable calendar date are
    published. This deliberately prefers missing an event over inventing a date.
    """
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    reference_year = int(month[:4]) if month and re.match(r"^20\d{2}-\d{2}$", month) else None

    for heading in soup.find_all(["h2", "h3", "h4", "h5"]):
        title = _clean(heading.get_text(" ", strip=True))
        if not title or title.casefold() in {"agenda", "eventos", "agenda de eventos", "próximos eventos", "proximos eventos"}:
            continue

        block = _candidate_block(heading)
        link = heading.find("a", href=True) or heading.find_parent("a", href=True)
        if link is None and block is not None:
            link = block.find("a", href=True)
        if link is None:
            continue

        href = urljoin(base_url, link.get("href", ""))
        if not href.startswith("http"):
            continue

        context = _clean(block.get_text(" ", strip=True) if block is not None else title)
        start_date, end_date, schedule_text = parse_event_dates(context, reference_year=reference_year)
        if start_date is None:
            # Recurring-only wording is retained only when a concrete date is
            # also present. Otherwise it cannot be placed safely in a calendar.
            continue
        if month and not ((start_date or "").startswith(month) or (end_date or "").startswith(month)):
            continue

        key = href.rstrip("/") or f"{source_id}:{title.casefold()}:{start_date}"
        if key in seen:
            continue

        summary = context
        if schedule_text:
            summary = summary.replace(schedule_text, " ", 1)
        summary = _clean(summary.replace(title, " ", 1))
        paragraph = block.find("p") if block is not None else None
        paragraph_text = _clean(paragraph.get_text(" ", strip=True)) if paragraph is not None else ""
        if paragraph_text and paragraph_text != title and len(paragraph_text) > 12:
            summary = paragraph_text

        image = block.find("img") if block is not None else None
        location_name = None
        for selector in (".location", ".lugar", ".place", "[class*='location']", "[class*='lugar']"):
            node = block.select_one(selector) if block is not None else None
            if node is not None:
                location_name = _clean(node.get_text(" ", strip=True)) or None
                if location_name:
                    break

        items.append({
            "id": key,
            "title": title[:250],
            "start_date": start_date,
            "end_date": end_date or start_date,
            "schedule_text": schedule_text,
            "start_at": None,
            "end_at": None,
            "all_day": True,
            "category": _category(f"{title} {summary}"),
            "location_name": location_name,
            "latitude": None,
            "longitude": None,
            "summary": summary[:500] or None,
            "image_url": _image_url(image, base_url),
            "url": href,
            "island": island,
            "source": source,
            "source_id": source_id,
        })
        seen.add(key)
        if len(items) >= limit:
            break

    items.sort(key=lambda item: (item["start_date"], item["title"]))
    return items


async def _fetch_tenerife_page(client: httpx.AsyncClient, page_index: int) -> str:
    response = await client.get(TENERIFE_AGENDA_URL, params={"page-index": page_index, "tab": 1})
    response.raise_for_status()
    return response.text


async def fetch_tenerife_events(limit: int = 100, month: str | None = None) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "Canarias-Cerca/1.0"},
    ) as client:
        pages = await asyncio.gather(*[_fetch_tenerife_page(client, page_index) for page_index in (1, 2, 3)])

    items: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for html in pages:
        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a", href=True):
            item = _parse_event_anchor(anchor)
            if item is None or item["url"] in seen_urls:
                continue
            if month and not (item["start_date"].startswith(month) or item["end_date"].startswith(month)):
                continue
            seen_urls.add(item["url"])
            items.append(item)
    items.sort(key=lambda item: (item["start_date"], item["title"]))
    return items[:limit]


async def fetch_island_events(island: str, limit: int = 200, month: str | None = None) -> dict[str, Any]:
    config = EVENT_SOURCES.get(island)
    if config is None:
        raise ValueError(f"Unknown calendar source for island: {island}")

    if config["parser"] == "tenerife":
        items = await fetch_tenerife_events(limit=limit, month=month)
    else:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Canarias-Cerca/1.0"},
        ) as client:
            response = await client.get(config["url"])
            response.raise_for_status()
        items = parse_generic_events(
            response.text,
            base_url=config["url"],
            source=config["source"],
            source_id=config["id"],
            island=island,
            month=month,
            limit=limit,
        )

    return {
        "island": island,
        "month": month or current_month(),
        "items": items,
        "available": True,
        "source": config["source"],
        "source_url": config["url"],
        "source_id": config["id"],
        "calendar_ready": True,
    }
