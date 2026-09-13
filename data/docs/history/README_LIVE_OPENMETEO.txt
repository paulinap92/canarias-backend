CANARIAS CERCA — LIVE OPEN-METEO PATCH

NEW LIVE DATA
=============

WEATHER:
GET /api/regions/canarias/live/weather?island=tenerife

- 41 named points across the archipelago
- Tenerife: 8 points
- current temperature / feels-like / humidity / wind
- daily min/max / rain probability / UV
- sunrise + sunset + daylight duration
- source: Open-Meteo

AIR / CALIMA:
GET /api/regions/canarias/live/air-quality?island=lanzarote

- 20 modeled points across the archipelago
- PM10, PM2.5, Saharan dust, European AQI, NO2, O3
- source: Open-Meteo / CAMS
- IMPORTANT: modeled data, not observed Gobierno station measurements

TIDES:
GET /api/regions/canarias/live/tides?island=tenerife&hours=48

- 22 named coastal points
- Tenerife: Santa Cruz, Puerto de la Cruz, Los Cristianos, Los Gigantes
- returns high/low turns + next_high + next_low
- source: Open-Meteo Marine
- IMPORTANT: modeled sea level including tides; not for navigation

MARINE:
Keep existing coordinate endpoint:
/api/regions/canarias/marine?latitude=...&longitude=...

Best use:
click a beach/coastal point -> fetch Marine for that exact coordinate.

VOLCANIC:
Keep as report/status. No fake map points.

ALERTS:
GET /api/regions/canarias/alerts
GET /api/regions/canarias/alerts?island=lanzarote

Old RSS/history dump is removed.
Source is now the official Gobierno de Canarias emergency alert database.
Only records explicitly marked "Vigente: SI" are returned.

Each alert includes:
status=active
official_vigente=true
type
level
islands
date
summary

FILES
=====

NEW:
data/weather_points.json
data/air_quality_points.json
data/coastal_points.json
app/services/open_meteo_live.py
app/api/live.py
tools/test_live_openmeteo.py

REPLACE:
app/services/alerts.py
app/api/alerts.py
app/jobs/cache_warmer.py
app/main.py

CACHE
=====

No json_cache.py replacement is needed.
Existing markers /weather, /air-quality, /tides and /alerts already match
the new endpoint paths.

TEST
====

Restart:

uv run python -m uvicorn app.main:app --reload

Manual:

http://127.0.0.1:8000/api/regions/canarias/live/weather?island=tenerife

http://127.0.0.1:8000/api/regions/canarias/live/air-quality?island=lanzarote

http://127.0.0.1:8000/api/regions/canarias/live/tides?island=tenerife&hours=48

http://127.0.0.1:8000/api/regions/canarias/alerts?island=lanzarote

Automatic:

uv run python tools/test_live_openmeteo.py

Expected:

ALL LIVE OPEN-METEO TESTS PASSED

Then Railway:

uv run python tools/test_live_openmeteo.py --base https://canarias-backend-production.up.railway.app
