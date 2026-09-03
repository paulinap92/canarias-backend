import re
from typing import Any

import httpx
from bs4 import BeautifulSoup


IGN_VOLCANIC_URL = (
    "https://www.ign.es/web/resources/"
    "volcanologia/html/CA_noticias.html"
)


async def fetch_volcanic_activity() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(
            IGN_VOLCANIC_URL,
            headers={"User-Agent": "Canarias-Cerca/1.0"},
        )
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    period_node = soup.find("h3")
    if period_node is None:
        raise RuntimeError("IGN volcanic report period not found")

    title_node = period_node.find_next("h2")
    if title_node is None:
        raise RuntimeError("IGN volcanic report title not found")

    paragraphs = []
    for node in title_node.find_all_next(["p", "h3"]):
        if node.name == "h3":
            break
        text = node.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)

    report_text = " ".join(paragraphs)

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

    return {
        "period": period_node.get_text(" ", strip=True),
        "title": title_node.get_text(" ", strip=True),
        "earthquakes_total": int(total_match.group(1)) if total_match else None,
        "max_magnitude": (
            float(magnitude_match.group(1).replace(",", "."))
            if magnitude_match else None
        ),
        "significant_deformation_detected": significant_deformation,
        "summary": report_text[:700] if report_text else None,
        "source": "IGN",
        "source_url": IGN_VOLCANIC_URL,
    }
