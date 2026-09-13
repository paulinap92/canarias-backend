CANARIAS CERCA — SCROLLYTELLING BACKEND V1
07.09.2026

GOAL
====

Frontend is moving to:

Explore | Live | Calendar | News

Map-first + left-side scrollytelling.

This patch does NOT create another giant dashboard API.
It makes Tenerife usable first.


1. EXPLORE
==========

NEW:

GET /api/regions/canarias/explore?island=tenerife

Optional:

&limit=6
&category=nature

Tenerife currently returns 6 curated, display-ready items:

1. Parque Nacional del Teide
2. Parque Rural de Anaga
3. Masca
4. Garachico
5. La Orotava
6. Playa de Benijo

Every item already has:

id
slug
name
island
type
category
latitude
longitude
short_description
description
image_url
image_credit
image_source_url
source_url
featured
order
tags
language

This is deliberately curated content for scrollytelling.
It is NOT the full Places dataset.

Other islands currently return:

available=false

That is intentional.
Tenerife first; then copy the content model island by island.


2. EXISTING PLACES STAYS
========================

Existing endpoint stays:

GET /api/regions/canarias/places?island=tenerife

app/services/places.py is replaced only to make its properties predictable.

Every OSM Place now includes:

id
slug
name
island
category
latitude
longitude
short_description
description
image_url
image_credit
image_source_url
source_url
featured
order
osm_id
osm_type
website
wikipedia
wikidata
osm_url

For generic OSM records the editorial fields may be null.

If the OSM name matches one of our curated Tenerife records,
the richer text/image fields are automatically overlaid.

So:
- /places remains a broad map layer
- /explore remains a small editorial/scrollytelling selection


3. EVENTS / CALENDAR
====================

REPLACED:

app/services/events.py
app/api/events.py

The old source parser only returned:

title
summary
url
island
source

The new response is calendar-ready:

title
start_date
end_date
start_at
end_at
all_day
category
location_name
latitude
longitude
summary
image_url
url
island
source


LIST:

GET /api/regions/canarias/events?island=tenerife

Optional:

&month=2026-09
&category=music
&limit=100


CALENDAR:

GET /api/regions/canarias/events/calendar?island=tenerife

Optional:

&month=2026-09
&category=fiesta


Calendar response:

{
  "month": "2026-09",
  "events_count": 12,
  "days": {
    "2026-09-07": [...],
    "2026-09-12": [...]
  }
}

The service fetches the current paginated Turismo de Tenerife agenda
(page-index 1..3) and de-duplicates by event URL.

This avoids the previous problem where the root agenda page could show
an older slice of the listing.

IMPORTANT:
We do NOT invent coordinates, times or venue names when the listing
does not expose them reliably.

Those fields stay null until we enrich event-detail parsing later.


4. MAIN.PY — MANUAL MERGE ONLY
==============================

THIS PATCH DOES NOT REPLACE app/main.py.

Your local main.py is newer than the GitHub version and may already contain:
- Live/Open-Meteo
- transport
- ports/ferries
- background jobs
- guide
- capabilities

Add only:

from app.api.explore import router as explore_router

and:

app.include_router(explore_router)

Events router already exists in your current project.
The replacement app/api/events.py keeps the same router import path.


5. FILES
========

NEW:

data/explore_tenerife.json
data/places_enrichment_tenerife.json

app/services/explore.py
app/api/explore.py

tools/test_scrollytelling_backend.py


REPLACE:

app/services/places.py

app/services/events.py
app/api/events.py


6. TEST
=======

Restart:

uv run python -m uvicorn app.main:app --reload


MANUAL:

http://127.0.0.1:8000/api/regions/canarias/explore?island=tenerife

http://127.0.0.1:8000/api/regions/canarias/places?island=tenerife&limit=30

http://127.0.0.1:8000/api/regions/canarias/events?island=tenerife&month=2026-09

http://127.0.0.1:8000/api/regions/canarias/events/calendar?island=tenerife&month=2026-09


AUTOMATIC:

uv run python tools/test_scrollytelling_backend.py


Expected:

ALL SCROLLYTELLING BACKEND TESTS PASSED


7. FRONTEND CONTRACT
====================

STARTUP:
Do not fetch everything.

After island selection:

Explore click
-> GET /explore?island=tenerife

Live click
-> no request yet
-> request specific Live feature only after feature click

Calendar click
-> GET /events/calendar?island=tenerife

News click
-> GET /news?island=tenerife


EXPLORE SCROLL:

Each item already has coordinates.

Frontend should:
- render left story cards
- create MapLibre points once
- highlight active point on scroll
- do NOT auto-open popups
- do NOT aggressive flyTo on every scroll tick

A gentle easeTo only when the active story changes is enough.


8. WHAT NOT TO DO NEXT
======================

Do not add another 20 APIs.

Next backend step after this works:

- verify Tenerife Explore visually in frontend
- verify September Calendar visually
- enrich event detail only if missing location/time is actually a UX problem
- then add Explore content for the next island

Culture / food / recipes from the existing Guide work remain separate
and can later be surfaced from the same left scrollytelling design
without changing this Explore contract.
