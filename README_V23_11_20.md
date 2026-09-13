# Canarias Cerca backend v23.11.20 — cumulative PATCH

Apply over v23.11.18 or v23.11.19 backend with the server stopped.

This patch intentionally does **not** contain `data/explore/*` runtime snapshots,
so it will not overwrite JSONs already refreshed on your machine.

Included:
- v23.11.19 Live / News / Calendar stability fixes and Live config files,
- RAW -> curated/published Explore boundary,
- Places quality gate (category quotas instead of hundreds of points),
- Beaches tri-state metadata (`yes/no/unknown`),
- Fauna/Flora curated Tenerife catalog; GBIF stays RAW candidates,
- Routes published shortlist capped at 8,
- regression tests.

Refresh behaviour:
- Explore POST: external source -> `data/raw/explore/...` -> curation -> `data/explore/...`
- Live: replace current snapshot, keep previous on failure
- News: append + dedupe
- Calendar: merge/upsert

Tests in packaged working tree: 37 passed.
