# Geographic audit

## What was fixed

1. **Places / Beaches**
   - Overpass queries are scoped to the selected island.
   - `way`/`relation` markers prefer a point from the real returned geometry instead of blindly using the Overpass bounding-box `center`.

2. **Trails**
   - Overpass requests are scoped to the selected island before filtering.

3. **Wildlife**
   - GBIF receives an island-specific search geometry instead of the whole archipelago for every request.

4. **Lanzarote / La Graciosa**
   - Their coarse rectangular bboxes overlap. A conservative La Graciosa polygon prevents cross-island leakage while keeping Órzola and Mirador del Río on Lanzarote.

5. **Static points**
   - `tools/audit_geo_data.py` checks static coordinates and curated Explore points against the declared island.

## Tides

The live tide endpoint already returns named coastal points from `data/coastal_points.json`. The frontend patch treats Tides as a multi-point layer and no longer includes the selected island centre in the Tides toggle event. Only Marine deliberately uses the island reference coordinate.
