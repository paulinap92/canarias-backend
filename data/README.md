# Canarias Cerca data

Runtime GETs read local JSON. External services are used only by explicit POST refreshes and, later, background jobs.

- `explore/` — published Explore data (Places, Beaches, Routes, Fauna, Flora)
- `guide/` — editorial Guide content
- `live/` — saved current-state snapshots
- `live/config/` — stable point definitions used by Weather, Air, Marine and Tides
- `calendar/` — persisted event snapshots by island/month
- `news/` — persisted news feed
- `state/` — last refresh success/error metadata

Refresh strategy:

- Live = replace the current snapshot only after a valid fetch.
- Calendar = merge/upsert with the stored month; one missing source response does not erase existing events.
- News = append + deduplicate; a short RSS window does not erase older locally stored items.

Failed refreshes keep the last valid JSON and are logged as `DATA REFRESH FAIL`.
