# v23.11.23 — pre-SQL completion

This release finishes the current pre-SQL backend pass.

Highlights:
- current Explore curation applied on every GET without overwriting local snapshots,
- curated Explore catalogs / Guide / Experiences retained,
- multi-island Calendar source registry and conservative date parser,
- multi-source News failure isolation,
- transport overview foundation,
- deterministic local-data `GET /api/regions/canarias/today?island=...`,
- manual Refresh architecture remains; no scheduler/background jobs,
- no PostgreSQL/PostGIS migration yet.

Validation: `63 passed` + Python compile check.
