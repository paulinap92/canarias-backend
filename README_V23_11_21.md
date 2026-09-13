# Canarias Cerca backend v23.11.21 — daily UX + live pass

Cumulative code patch over the Data Foundation line. It intentionally does **not** include user-generated published/raw snapshots, so local refreshed JSON data is preserved.

Changes:
- Seismic snapshots declare the IGN 10-day window and source metadata.
- Volcanic data uses one canonical `data/live/volcanic/canarias.json` snapshot.
- Volcanic refresh parses multiple recent IGN reports/news, not just one summary.
- Migration fallback can reuse an older meaningful island volcanic snapshot until the first global refresh.
- Existing v23.11.19/v23.11.20 Data Foundation, Live config, News append+dedupe, Calendar merge/upsert and Explore curation are retained.

Validation: 41 backend tests passed.
