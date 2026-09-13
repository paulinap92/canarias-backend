# Canarias Cerca — Backend

FastAPI backend for the Canarias Cerca map. The API combines curated island content with live/model data and external geographic sources.

## Run locally

Requires Python 3.12+ and `uv`.

```powershell
cd "C:\projects\canary project\canarias-backend-starter"
uv sync --dev
uv run python -m uvicorn app.main:app --reload
```

API: `http://127.0.0.1:8000`  
Swagger: `http://127.0.0.1:8000/docs`

## Tests

```powershell
uv run pytest -q
```

## Geographic audit

Static map coordinates can be checked without calling external APIs:

```powershell
uv run python tools/audit_geo_data.py
```

The audit checks curated Explore points, monuments, weather points, air-quality points and coastal/tide points against their declared islands. It also reports missing Guide sections.

## Main API groups

- `/api/regions/canarias/explore?island=...` — curated Explore stories
- `/api/regions/canarias/content?island=...&section=...` — Guide content
- `/api/regions/canarias/places?island=...` — OSM/Overpass places + curated pueblos/patrimonio fallback
- `/api/regions/canarias/beaches?island=...` — OSM/Overpass beaches
- `/api/regions/canarias/trails?island=...` — OSM hiking/foot route relations (one feature per route)
- `/api/regions/canarias/wildlife?island=...` — GBIF observations
- `/api/regions/canarias/live/weather?island=...`
- `/api/regions/canarias/live/air-quality?island=...`
- `/api/regions/canarias/live/tides?island=...&hours=48`
- `/api/regions/canarias/ports?island=...`
- `/api/regions/canarias/transport/airports?island=...`

## Project structure

- `app/api/` — HTTP routes
- `app/services/` — providers and data normalization
- `app/utils/` — shared geographic/island helpers
- `data/content/<island>/` — curated Spanish content
- `data/*.json` — static reference points
- `tools/` — local diagnostics/audits
- `tests/` — regression tests
- `docs/` — implementation notes and archived historical instructions

Generated caches, virtual environments, IDE metadata and local `.env` files are intentionally excluded from the clean project package.

## Persisted data foundation (v23.11.17)

Normal GET requests for the current Explore layers, News, Calendar and the main Live layers read local JSON snapshots. External providers are contacted only by explicit POST refreshes. A failed refresh keeps the last good snapshot.

Examples:

```bash
# read saved snapshot
curl "http://127.0.0.1:8000/api/regions/canarias/places?island=tenerife"

# refresh + persist + return snapshot
curl -X POST "http://127.0.0.1:8000/api/regions/canarias/places?island=tenerife"

# same mechanism through the generic data route
curl -X POST "http://127.0.0.1:8000/api/regions/canarias/data/explore/places?island=tenerife"

# CLI alternative
uv run python tools/refresh_data.py explore places --island tenerife
uv run python tools/refresh_data.py news latest
uv run python tools/refresh_data.py calendar events --island tenerife --month 2026-09
uv run python tools/refresh_data.py live weather --island tenerife
```

Data layout follows the product: `data/explore`, `data/guide`, `data/live`, `data/calendar`, `data/news`.
