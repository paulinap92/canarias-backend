# Canarias Backend v23.11.22 — Foundation 1–7

This pass closes the agreed foundation through point 7 without introducing background jobs or SQL yet.

## Main changes

- Explore remains behind FastAPI; JSON is temporary persistence only.
- Explore RAW refresh is now merge/upsert instead of blind replace.
- Missing candidates survive one refresh; new candidates are added and existing candidates updated.
- RAW -> quality gate -> PUBLISHED boundary remains enforced.
- DataSource write strategy is explicit: Explore=merge, Live=replace, Calendar=merge, News=append.
- Calendar and News refreshes expose useful refresh_stats and backend logs include write strategy/stats.
- GET endpoints remain local-only and do not invoke external fetchers.
- 48 backend tests pass.

## Important

This patch intentionally does NOT include your local Explore/Live/Calendar/News snapshots, so applying it should not overwrite data you already refreshed locally.

Background jobs and PostgreSQL/PostGIS are later stages. The API contract is kept stable so JSON can be replaced by SQL later without rebuilding the frontend.
