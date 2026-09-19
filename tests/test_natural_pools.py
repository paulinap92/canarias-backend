from app.services.natural_pools import (
    _listing_links,
    best_osm_candidate,
    parse_detail_page,
)


def test_listing_links_keeps_only_pool_details():
    html = """
    <a href="/piscinas-naturales/tenerife/all/">Todas</a>
    <a href="/piscinas-naturales/tenerife/charco-de-isla-cangrejo/">Isla Cangrejo</a>
    <a href="/piscinas-naturales/tenerife/piscinas-naturales-de-mesa-del-mar/">Mesa del Mar</a>
    <a href="/playas/tenerife/foo/">Otra cosa</a>
    """
    assert _listing_links(html, "tenerife") == [
        "https://www.holaislascanarias.com/piscinas-naturales/tenerife/charco-de-isla-cangrejo/",
        "https://www.holaislascanarias.com/piscinas-naturales/tenerife/piscinas-naturales-de-mesa-del-mar/",
    ]


def test_detail_parser_extracts_editorial_text(monkeypatch):
    monkeypatch.setenv("CANARIAS_DEV_REMOTE_IMAGES", "0")
    html = """
    <html><body>
      <h1>Charco de Isla Cangrejo</h1>
      <h3>Una piscina perfecta para un baño en familia</h3>
      <p>Es una piscina natural junto a Santiago del Teide.</p>
    </body></html>
    """
    item = parse_detail_page(
        html,
        "https://www.holaislascanarias.com/piscinas-naturales/tenerife/charco-de-isla-cangrejo/",
        "tenerife",
    )
    assert item is not None
    assert item["name"] == "Charco de Isla Cangrejo"
    assert item["category"] == "natural_pool"
    assert item["image_url"] is None


def test_osm_matching_handles_generic_pool_words():
    candidates = [
        {
            "name": "Charco de Isla Cangrejo",
            "coordinates": (-16.8434, 28.24152),
        },
        {
            "name": "Piscina Municipal",
            "coordinates": (-16.2, 28.4),
        },
    ]
    candidate, score = best_osm_candidate(
        "Piscina natural Charco de Isla Cangrejo",
        candidates,
    )
    assert candidate is not None
    assert candidate["name"] == "Charco de Isla Cangrejo"
    assert score >= 0.64
