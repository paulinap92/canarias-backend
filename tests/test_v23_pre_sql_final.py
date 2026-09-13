from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.events import EVENT_SOURCES, parse_event_dates, parse_generic_events
from app.services.news import NEWS_HTML_SOURCES, parse_html_news
from app.services.transport import get_transport_overview
from app.utils.islands import VALID_ISLANDS

client = TestClient(app)


def test_calendar_sources_cover_all_islands():
    assert set(EVENT_SOURCES) == set(VALID_ISLANDS)
    assert all(value.get("url", "").startswith("https://") for value in EVENT_SOURCES.values())


def test_calendar_date_parser_handles_real_agenda_patterns():
    assert parse_event_dates("04/08/2026")[0] == "2026-08-04"
    assert parse_event_dates("07/08/2026 - 16/08/2026")[:2] == ("2026-08-07", "2026-08-16")
    assert parse_event_dates("17 al 20 Septiembre 2026")[:2] == ("2026-09-17", "2026-09-20")
    assert parse_event_dates("jueves, 01 de enero, 2026")[0] == "2026-01-01"
    assert parse_event_dates("3 al 25 julio", reference_year=2026)[:2] == ("2026-07-03", "2026-07-25")
    assert parse_event_dates("Todos los viernes")[2].casefold() == "todos los viernes"


def test_generic_calendar_parser_is_conservative_and_keeps_source_metadata():
    html = """
    <article>
      <h3><a href="/eventos/fuerteventura/fiesta-del-mar/">Fiesta del Mar</a></h3>
      <div class="location">Puerto del Rosario</div>
      <p>17 al 20 Septiembre 2026 · música y gastronomía</p>
    </article>
    <article>
      <h3><a href="/eventos/fuerteventura/sin-fecha/">Sin fecha inventada</a></h3>
      <p>Información general sin fecha.</p>
    </article>
    """
    items = parse_generic_events(
        html,
        base_url="https://www.visitfuerteventura.com/eventos/fuerteventura/",
        source="Visit Fuerteventura",
        source_id="fuerteventura-tourism",
        island="fuerteventura",
        month="2026-09",
    )
    assert len(items) == 1
    item = items[0]
    assert item["title"] == "Fiesta del Mar"
    assert item["start_date"] == "2026-09-17"
    assert item["end_date"] == "2026-09-20"
    assert item["island"] == "fuerteventura"
    assert item["source_id"] == "fuerteventura-tourism"
    assert item["location_name"] == "Puerto del Rosario"


def test_events_endpoint_supports_all_islands_from_persisted_store():
    for island in VALID_ISLANDS:
        response = client.get(f"/api/regions/canarias/events?island={island}&month=2026-09")
        assert response.status_code == 200
        body = response.json()
        assert body["island"] == island
        assert body.get("calendar_ready") is True


def test_capabilities_marks_calendar_available_for_every_valid_island():
    for island in VALID_ISLANDS:
        response = client.get(f"/api/regions/canarias/islands/{island}/capabilities")
        assert response.status_code == 200
        assert response.json()["features"]["events"] is True


def test_news_is_truly_multi_source_and_parser_keeps_island():
    ids = {item["id"] for item in NEWS_HTML_SOURCES}
    assert {"tenerife-tourism", "gran-canaria-tourism", "lanzarote-tourism", "la-graciosa-tourism"}.issubset(ids)
    html = """
    <article><h2><a href="/noticia/uno">Nueva campaña</a></h2><p>11 de septiembre, 2026. Información.</p></article>
    """
    items = parse_html_news(
        html,
        base_url="https://example.test/",
        source="Turismo de Tenerife",
        island="tenerife",
    )
    assert items[0]["island"] == "tenerife"
    assert items[0]["source"] == "Turismo de Tenerife"


def test_transport_overview_covers_every_island_without_claiming_live_timetable():
    for island in VALID_ISLANDS:
        overview = get_transport_overview(island)
        assert overview["available"] is True
        assert overview["live_timetable"] is False
        assert isinstance(overview["ports"], list)
        assert isinstance(overview["ferry_routes"], list)
    assert get_transport_overview("tenerife")["local_transit"]["provider"] == "TITSA"
    assert any(r["destination_island"] == "la-graciosa" or r["origin_island"] == "la-graciosa" for r in get_transport_overview("la-graciosa")["ferry_routes"])


def test_today_endpoint_is_local_data_foundation_not_llm_generation():
    response = client.get("/api/regions/canarias/today?island=tenerife")
    assert response.status_code == 200
    body = response.json()
    assert body["island"] == "tenerife"
    assert body["mode"] == "deterministic_local_data"
    assert body["generated_by_llm"] is False
    assert set(body["featured"]) == {"places", "beaches", "routes"}
    assert "conditions" in body
    assert "alerts" in body
    assert "news" in body
