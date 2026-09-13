# Canarias Cerca backend v23.11.18 — Data Foundation regression fix

## What changed

- Normal `GET` requests read local JSON snapshots only.
- Manual `POST` refreshes the external source, validates it, atomically writes JSON, then returns the saved snapshot.
- Failed refresh never overwrites the last valid snapshot.
- Refresh/read operations now print explicit terminal logs.
- Explore data folders: `data/explore/{places,beaches,routes,fauna,flora}/`.
- Live snapshot folders: `data/live/...`.
- Old HTTP JSON cache/cache-warmer runtime path removed.
- Flora refresh source added through GBIF (temporary raw-data source; later product model will be curated hotspots/species).
- Tenerife Places/Beaches and other islands receive a small curated seed from existing Explore editorial content so a fresh install is not completely blank before the first refresh.

## Expected logs

Normal read:

```text
[DATA GET] explore:places:tenerife status=seed count=9 file=.../data/explore/places/tenerife.json
```

Manual refresh:

```text
[DATA REFRESH START] explore:places:tenerife -> .../data/explore/places/tenerife.json
[DATA REFRESH OK] explore:places:tenerife count=123 updated_at=...
```

Failure:

```text
[DATA REFRESH FAIL] explore:places:tenerife keeping_previous=True error=...
```

A failure returns the previous JSON with `status: stale` instead of deleting it.

## Run

```bash
uv run python -m uvicorn app.main:app --reload
```

Stop Uvicorn before replacing the backend folder, then start it again.
