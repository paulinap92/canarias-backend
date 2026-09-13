from __future__ import annotations

from typing import Any


def _featured_from_fc(payload: Any, limit: int = 3) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    features = payload.get("features") or []
    values: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        props = dict(feature.get("properties") or {})
        if not props.get("featured"):
            continue
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") if geometry.get("type") == "Point" else None
        values.append({
            "id": props.get("id") or props.get("cc_id") or props.get("name"),
            "name": props.get("name") or props.get("common_name"),
            "description": props.get("short_description") or props.get("description"),
            "category": props.get("category"),
            "coordinates": coords if isinstance(coords, list) and len(coords) >= 2 else None,
        })
        if len(values) >= limit:
            break
    return values


def _first_upcoming_event(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    if not items:
        return None
    item = items[0]
    return {
        key: item.get(key)
        for key in ("id", "title", "start_date", "end_date", "schedule_text", "category", "location_name", "url", "source")
        if item.get(key) is not None
    }


def build_today_payload(
    *,
    island: str,
    weather: Any,
    alerts: Any,
    events: Any,
    places: Any,
    beaches: Any,
    routes: Any,
    news_items: list[dict[str, Any]],
) -> dict[str, Any]:
    weather_points = weather.get("points", []) if isinstance(weather, dict) else []
    alert_items = alerts.get("items", []) if isinstance(alerts, dict) else []
    return {
        "island": island,
        "available": True,
        "mode": "deterministic_local_data",
        "generated_by_llm": False,
        "conditions": {
            "points": weather_points[:3],
            "source": weather.get("source") if isinstance(weather, dict) else None,
            "updated_at": weather.get("updated_at") if isinstance(weather, dict) else None,
            "status": weather.get("status") if isinstance(weather, dict) else None,
        },
        "alerts": {
            "items": alert_items[:5],
            "updated_at": alerts.get("updated_at") if isinstance(alerts, dict) else None,
            "status": alerts.get("status") if isinstance(alerts, dict) else None,
        },
        "next_event": _first_upcoming_event(events),
        "featured": {
            "places": _featured_from_fc(places, 3),
            "beaches": _featured_from_fc(beaches, 3),
            "routes": _featured_from_fc(routes, 3),
        },
        "news": news_items[:5],
        "freshness": {
            "weather": weather.get("updated_at") if isinstance(weather, dict) else None,
            "alerts": alerts.get("updated_at") if isinstance(alerts, dict) else None,
            "calendar": events.get("updated_at") if isinstance(events, dict) else None,
        },
        "note": "Foundation payload for Canarias Hoy. It reads stored data only; LLM narration is intentionally deferred.",
    }
