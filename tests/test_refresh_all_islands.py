from app.tools.refresh_all_islands import RESOURCE_SPECS, _is_ok
from app.utils.islands import VALID_ISLANDS


def test_all_eight_islands_are_included() -> None:
    assert set(VALID_ISLANDS) == {
        "tenerife",
        "gran-canaria",
        "lanzarote",
        "fuerteventura",
        "la-palma",
        "la-gomera",
        "el-hierro",
        "la-graciosa",
    }


def test_core_refresh_resources_cover_equal_island_scope() -> None:
    per_island = {spec.label for spec in RESOURCE_SPECS if spec.per_island}
    assert per_island == {
        "Rutas",
        "Weather",
        "Air",
        "Marine",
        "Tides",
        "Seismic",
        "Alerts",
        "Calendar",
    }


def test_routes_and_live_measurements_require_real_data() -> None:
    required = {spec.label for spec in RESOURCE_SPECS if spec.require_nonempty}
    assert required == {"Rutas", "Weather", "Air", "Marine", "Tides"}


def test_empty_required_payload_fails() -> None:
    ok, reason = _is_ok(
        {"status": "ok", "available": True, "features": []},
        require_nonempty=True,
    )
    assert ok is False
    assert reason == "empty"


def test_empty_valid_state_can_pass_for_alerts_or_calendar() -> None:
    ok, reason = _is_ok(
        {"status": "ok", "available": True, "items": []},
        require_nonempty=False,
    )
    assert ok is True
    assert reason == "ok"


def test_stale_payload_never_counts_as_ready() -> None:
    ok, reason = _is_ok(
        {"status": "stale", "available": True, "points": [{"id": 1}]},
        require_nonempty=True,
    )
    assert ok is False
    assert reason == "stale"
