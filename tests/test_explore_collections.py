from app.services.explore_collections import (
    _best_candidate,
    _food_category,
    _listing_links,
    parse_directory_detail,
)


def test_marina_listing_links_are_scoped_to_island() -> None:
    html = """
    <a href="/puertos-y-marinas/tenerife/all/">Todas</a>
    <a href="/puertos-y-marinas/tenerife/puerto-colon/">Puerto Colón</a>
    <a href="/puertos-y-marinas/gran-canaria/puerto-rico/">Otro</a>
    """
    assert _listing_links(html, "marinas", "tenerife") == [
        "https://www.holaislascanarias.com/puertos-y-marinas/tenerife/puerto-colon/"
    ]


def test_food_directory_classifies_cheese_and_wine() -> None:
    assert _food_category("Quesería Benijos", "") == "cheese_dairy"
    assert _food_category("Bodegas Monje", "Vinos de Tenerife") == "winery"


def test_directory_detail_uses_page_coordinates(monkeypatch) -> None:
    monkeypatch.setenv("CANARIAS_DEV_REMOTE_IMAGES", "0")
    html = """
    <html>
      <head>
        <script type="application/ld+json">
          {"@type":"Winery","geo":{"latitude":28.4,"longitude":-16.5}}
        </script>
      </head>
      <body>
        <h1>Bodegas de prueba</h1>
        <h3>Vinos de la isla</h3>
        <p>Visitas y degustaciones.</p>
      </body>
    </html>
    """
    item = parse_directory_detail(
        html,
        "https://www.holaislascanarias.com/bodegas-y-queserias/tenerife/test/",
        "food-producers",
        "tenerife",
    )
    assert item is not None
    assert item["coordinates"] == (-16.5, 28.4)
    assert item["category"] == "winery"


def test_directory_osm_name_matching() -> None:
    candidate, score = _best_candidate(
        "Puerto Deportivo Puerto Colón",
        [{"name": "Puerto Colón", "coordinates": (-16.73, 28.08)}],
    )
    assert candidate is not None
    assert score >= 0.62
