import re
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag


IGN_VOLCANIC_URL = (
    "https://www.ign.es/web/resources/"
    "volcanologia/html/CA_noticias.html"
)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _metrics(report_text: str) -> tuple[int | None, float | None, bool | None]:
    total_match = re.search(
        r"total de\s+(\d+)\s+terremotos",
        report_text,
        flags=re.IGNORECASE,
    )
    magnitude_match = re.search(
        r"magnitud máxima[^0-9]*([0-9]+(?:[.,][0-9]+)?)",
        report_text,
        flags=re.IGNORECASE,
    )

    lower_text = report_text.lower()
    if "no muestran deformaciones significativas" in lower_text:
        significant_deformation = False
    elif "deformaciones significativas" in lower_text:
        significant_deformation = True
    else:
        significant_deformation = None

    return (
        int(total_match.group(1)) if total_match else None,
        float(magnitude_match.group(1).replace(",", ".")) if magnitude_match else None,
        significant_deformation,
    )


def parse_volcanic_reports(html: str, limit: int = 12) -> list[dict[str, Any]]:
    """Parse IGN volcanic news/monthly reports in page order.

    The IGN page uses an h3 period followed by an h2 report title and body
    paragraphs until the next h3. Keeping multiple reports lets the product
    show the latest status *and* recent volcanic bulletins/news instead of
    collapsing the whole source into one card.
    """
    soup = BeautifulSoup(html, "html.parser")
    reports: list[dict[str, Any]] = []

    for period_node in soup.find_all("h3"):
        title_node = period_node.find_next_sibling("h2")
        if title_node is None:
            # Some versions of the page wrap nodes; find the next h2 but stop
            # if another period starts first.
            node = period_node.find_next()
            title_node = None
            while node is not None:
                if isinstance(node, Tag) and node.name == "h3":
                    break
                if isinstance(node, Tag) and node.name == "h2":
                    title_node = node
                    break
                node = node.find_next()
        if title_node is None:
            continue

        paragraphs: list[str] = []
        node = title_node.find_next()
        while node is not None:
            if isinstance(node, Tag) and node.name == "h3":
                break
            if isinstance(node, Tag) and node.name == "p":
                text = _clean(node.get_text(" ", strip=True))
                if text and (not paragraphs or text != paragraphs[-1]):
                    paragraphs.append(text)
            node = node.find_next()

        report_text = _clean(" ".join(paragraphs))
        if not report_text:
            continue

        total, max_magnitude, significant_deformation = _metrics(report_text)
        link = title_node.find("a", href=True)
        title = _clean(title_node.get_text(" ", strip=True))
        period = _clean(period_node.get_text(" ", strip=True))

        reports.append(
            {
                "period": period,
                "title": title,
                "summary": report_text[:900],
                "earthquakes_total": total,
                "max_magnitude": max_magnitude,
                "significant_deformation_detected": significant_deformation,
                "source": "IGN",
                "source_url": urljoin(IGN_VOLCANIC_URL, link["href"]) if link else IGN_VOLCANIC_URL,
            }
        )
        if len(reports) >= limit:
            break

    return reports


async def fetch_volcanic_activity() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(
            IGN_VOLCANIC_URL,
            headers={"User-Agent": "Canarias-Cerca/1.0"},
        )
        response.raise_for_status()

    reports = parse_volcanic_reports(response.text)
    if not reports:
        raise RuntimeError("IGN volcanic reports not found")

    latest = reports[0]
    return {
        **latest,
        "reports": reports,
        "reports_count": len(reports),
        "source": "IGN",
        "source_url": IGN_VOLCANIC_URL,
    }
