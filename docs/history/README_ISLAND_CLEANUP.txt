CANARIAS CERCA — FINAL ISLAND CONTEXT CLEANUP

WHY THIS PATCH EXISTS
=====================

Selecting Lanzarote in the frontend must never silently show Tenerife-only
events/webcams or mixed-island Explore data.

AFTER THIS PATCH:

STRICTLY FILTERED BY ?island=
--------------------------------
cities
monuments
seismic
places
beaches
trails
wildlife
airports
ports
ferry routes

REGIONAL BY DESIGN
------------------
news
alerts
volcanic

News from Gobierno de Canarias is regional. It may appear while Lanzarote is
selected, but it is explicitly tagged:
    scope = "canarias"
    island = null

This is NOT a Tenerife news item pretending to be Lanzarote news.

SOURCE CURRENTLY AVAILABLE ONLY FOR TENERIFE
--------------------------------------------
events
webcams
TITSA stops/routes
air quality

Generic events/webcams endpoints now return:
    available = false
    items = []
for Lanzarote / Gran Canaria / etc.

So Tenerife data cannot leak into another island context.


NEW CAPABILITIES ENDPOINT
=========================

GET
/api/regions/canarias/islands/{island}/capabilities

Example:
/api/regions/canarias/islands/lanzarote/capabilities

Frontend can use this once after selecting an island to hide/disable features
that are not available for that island.


IMPORTANT FRONTEND RULE
=======================

When an island is selected, frontend MUST send island=<slug> to every endpoint
that supports it.

Example Lanzarote:

/cities?island=lanzarote
/monuments?island=lanzarote
/seismic?island=lanzarote
/places?island=lanzarote
/beaches?island=lanzarote
/trails?island=lanzarote
/wildlife?island=lanzarote
/news?island=lanzarote
/events?island=lanzarote
/webcams?island=lanzarote
/transport/airports?island=lanzarote
/ports?island=lanzarote
/ferries/routes?island=lanzarote


TESTS
=====

START BACKEND:

uv run python -m uvicorn app.main:app --reload


AUTOMATIC LOCAL TEST:

uv run python tools/test_island_context.py


AUTOMATIC RAILWAY TEST:

uv run python tools/test_island_context.py --base https://canarias-backend-production.up.railway.app


MANUAL TESTS — LANZAROTE
========================

1.
http://127.0.0.1:8000/api/regions/canarias/islands/lanzarote/capabilities

Expected:
events=false
webcams=false
titsa=false


2.
http://127.0.0.1:8000/api/regions/canarias/cities?island=lanzarote

Expected:
ONLY Lanzarote cities.


3.
http://127.0.0.1:8000/api/regions/canarias/monuments?island=lanzarote

Expected:
Every returned item:
island = lanzarote


4.
http://127.0.0.1:8000/api/regions/canarias/events?island=lanzarote&limit=5

Expected:
available=false
items=[]


5.
http://127.0.0.1:8000/api/regions/canarias/webcams?island=lanzarote&limit=5

Expected:
available=false
items=[]


6.
http://127.0.0.1:8000/api/regions/canarias/events?island=tenerife&limit=5

Expected:
available=true


7.
http://127.0.0.1:8000/api/regions/canarias/transport/airports?island=lanzarote

Expected:
ACE only.


8.
http://127.0.0.1:8000/api/regions/canarias/ports?island=lanzarote

Expected:
only Lanzarote ports.


9.
http://127.0.0.1:8000/api/regions/canarias/ferries/routes?island=lanzarote

Expected:
only routes touching Lanzarote.


10.
http://127.0.0.1:8000/api/regions/canarias/news?island=lanzarote&limit=5

Expected:
regional Gobierno de Canarias news is allowed.
No item may have island="tenerife".


11.
http://127.0.0.1:8000/health

Expected local:
status=ok
storage.writable=true

Expected Railway:
railway_volume_mount_path=/data
storage.writable=true


CACHE / BACKGROUND JOBS
=======================

Background warmer remains enabled.

It refreshes:
seismic/news/alerts        ~10 min
air quality                ~15 min
weather                    ~30 min
volcanic/wildlife          ~6 h
places/beaches/trails      ~24 h

It calls the FastAPI endpoints themselves, so persistent middleware cache
remains the single cache mechanism.


AFTER TESTS
===========

Commit:

git add .
git commit -m "normalize island context across backend"
git push

Then run the Railway test script.

After this patch, island context on the BACKEND is considered closed.
Frontend must now consistently pass the selected island slug.
