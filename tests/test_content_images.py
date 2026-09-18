from app.services.content import get_content
from app.services.content_images import extract_page_image_url


def test_content_does_not_invent_wrong_island_wide_image():
    food = get_content("tenerife", "food", limit=20)
    papas = next(item for item in food["items"] if item["slug"] == "papas-arrugadas")
    assert papas.get("image_url") is None
    assert papas.get("image_fallback") is None


def test_existing_curated_content_image_is_preserved():
    explore = get_content("tenerife", "explore", limit=20)
    teide = next(item for item in explore["items"] if item["slug"] == "parque-nacional-del-teide")
    assert teide["image_url"].endswith("Teide,%20Roques%20de%20Garcia.jpg")


def test_extract_page_image_prefers_open_graph_image():
    html = """
    <html>
      <head>
        <meta property="og:image" content="/media/papas.jpg">
      </head>
      <body>
        <img src="/media/logo.png">
      </body>
    </html>
    """
    assert (
        extract_page_image_url(html, "https://example.com/recetas/papas/")
        == "https://example.com/media/papas.jpg"
    )


def test_extract_page_image_does_not_guess_from_body_images():
    html = """
    <html>
      <body>
        <img src="/assets/logo.svg">
        <img data-src="/photos/random-tree.jpg">
      </body>
    </html>
    """
    assert extract_page_image_url(html, "https://example.com/guide/item/") is None


def test_extract_page_image_accepts_json_ld_item_image():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Papas arrugadas",
            "image": ["/photos/papas.jpg"]
          }
        </script>
      </head>
    </html>
    """
    assert (
        extract_page_image_url(html, "https://example.com/recetas/papas/")
        == "https://example.com/photos/papas.jpg"
    )


def test_dev_remote_image_flag_defaults_enabled(monkeypatch):
    from app.services.content_images import dev_remote_images_enabled

    monkeypatch.delenv("CANARIAS_DEV_REMOTE_IMAGES", raising=False)
    assert dev_remote_images_enabled() is True


def test_dev_remote_image_flag_can_be_disabled(monkeypatch):
    from app.services.content_images import dev_remote_images_enabled

    monkeypatch.setenv("CANARIAS_DEV_REMOTE_IMAGES", "0")
    assert dev_remote_images_enabled() is False


def test_duplicate_source_urls_are_detected():
    from app.api.content import _dev_source_counts

    items = [
        {"slug": "one", "source_url": "https://example.com/generic"},
        {"slug": "two", "source_url": "https://example.com/generic"},
        {"slug": "three", "source_url": "https://example.com/specific"},
    ]
    assert _dev_source_counts(items) == {
        "https://example.com/generic": 2,
        "https://example.com/specific": 1,
    }
