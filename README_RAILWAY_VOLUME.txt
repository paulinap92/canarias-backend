CANARIAS CERCA — PERSISTENT JSON CACHE

FILES TO COPY
=============

1. app/middleware/__init__.py
2. app/middleware/json_cache.py
3. app/api/cache.py
4. replace app/main.py with the supplied main.py

No new Python dependency is required.


LOCAL BEHAVIOUR
===============

Without Railway, cache files are written to:

    data/cache/

Example:

    data/cache/api_regions_canarias_seismic__xxxxxxxxxxxx.json


RAILWAY
=======

Attach ONE Railway Volume to the backend service.

Recommended mount path:

    /data

Railway automatically exposes:

    RAILWAY_VOLUME_MOUNT_PATH=/data

The code automatically detects it and stores cache in:

    /data/cache

No CACHE_DIR variable is required.

Optional manual override:

    CACHE_DIR=/some/other/path


WHAT IS CACHED
==============

weather       30 min
air quality   15 min
seismic       10 min
marine        30 min
tides         1 h
alerts        10 min
news          10 min
volcanic      6 h
places        24 h
beaches       24 h
trails        24 h
wildlife      6 h

cities and monuments are repo-static JSON and are not middleware-cached.


BEHAVIOUR
=========

Fresh cache:
    frontend -> FastAPI -> JSON file
    X-Canarias-Cache: HIT

Missing cache:
    frontend -> FastAPI -> upstream API -> save JSON
    X-Canarias-Cache: MISS

Expired cache:
    frontend -> FastAPI -> upstream API -> replace JSON
    X-Canarias-Cache: REFRESH

Upstream fails but an old JSON exists:
    frontend -> stale last-known-good JSON
    X-Canarias-Cache: STALE


TEST
====

Start locally:

    uv run python -m uvicorn app.main:app --reload

1. Check cache status:

    http://127.0.0.1:8000/api/cache/status

2. Call an endpoint:

    http://127.0.0.1:8000/api/regions/canarias/seismic

3. Check status again:

    http://127.0.0.1:8000/api/cache/status

You should see files_count increase.

4. Call seismic again inside 10 minutes.
   The response header should contain:

    X-Canarias-Cache: HIT


RAILWAY TEST
============

After deploy and attaching the Volume:

    https://canarias-backend-production.up.railway.app/api/cache/status

Expected:

    "cache_dir": "/data/cache"
    "railway_volume_mount_path": "/data"

Then call several live endpoints and check status again.

Finally redeploy the service and call /api/cache/status again.
The same files should still exist — this confirms persistence across deploys.
