from app.services.content import get_content
from app.services.news import parse_html_news


def test_missing_guide_images_receive_curated_island_fallbacks():
    history = get_content("tenerife", "history", limit=20)
    assert history["items"]
    assert all(item.get("image_url") for item in history["items"])
    assert all(item.get("image_source_url") for item in history["items"])


def test_existing_content_image_is_preserved():
    explore = get_content("tenerife", "explore", limit=20)
    teide = next(item for item in explore["items"] if item["slug"] == "parque-nacional-del-teide")
    assert teide["image_url"].endswith("Teide,%20Roques%20de%20Garcia.jpg")
    assert teide.get("image_fallback") is not True


def test_gran_canaria_missing_explore_images_are_filled():
    explore = get_content("gran-canaria", "explore", limit=30)
    assert explore["items"]
    assert all(item.get("image_url") for item in explore["items"])


def test_html_news_parser_keeps_relative_card_image():
    html = """
    <article>
        <img src="/media/story.jpg" alt="">
        <h2><a href="/noticias/story">Una noticia</a></h2>
        <p>Resumen breve.</p>
    </article>
    """
    items = parse_html_news(
        html,
        base_url="https://example.com/noticias/",
        source="Example",
        island="tenerife",
    )
    assert items[0]["image_url"] == "https://example.com/media/story.jpg"
