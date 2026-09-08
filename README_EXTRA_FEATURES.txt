CANARIAS CERCA — EXTRA FEATURES

This patch adds:
- Canary airports
- Tenerife TITSA GTFS stops
- Tenerife TITSA GTFS routes
- Tenerife events (Turismo de Tenerife)
- Tenerife webcam directory (Turismo de Tenerife)

FILES
=====

NEW:
app/services/transport.py
app/api/transport.py
app/services/events.py
app/api/events.py
app/services/webcams.py
app/api/webcams.py

REPLACE:
app/main.py
app/middleware/json_cache.py


NO NEW DEPENDENCIES
===================

Uses packages already used by the backend:
httpx
beautifulsoup4


TEST URLS
=========

AIRPORTS
http://127.0.0.1:8000/api/regions/canarias/transport/airports

TITSA STOPS
http://127.0.0.1:8000/api/regions/canarias/islands/tenerife/transport/stops?limit=20

TITSA ROUTES
http://127.0.0.1:8000/api/regions/canarias/islands/tenerife/transport/routes?limit=20

EVENTS
http://127.0.0.1:8000/api/regions/canarias/islands/tenerife/events?limit=10

WEBCAMS
http://127.0.0.1:8000/api/regions/canarias/islands/tenerife/webcams?limit=20


RAILWAY
=======

Same endpoint paths under:

https://canarias-backend-production.up.railway.app

The TITSA GTFS ZIP is persisted in the Railway Volume under:
/data/transport/titsa_gtfs.zip

It is refreshed at most once every 24 hours.

JSON endpoint responses are also cached by the existing middleware.

NOTE ABOUT WEBCAMS
==================

This v1 endpoint returns the official Turismo de Tenerife webcam directory entries.
It intentionally does NOT scrape/rebroadcast third-party webcam video streams.
Frontend can show the list and link users to the official webcam source page.
