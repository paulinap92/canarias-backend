# Known issues / follow-up

- The supplied backend snapshot contains only `data/content/la-gomera/explore.json` for La Gomera. The other Guide sections are missing in this snapshot. The geo audit reports this as a warning rather than inventing content.
- Static coordinate audit verifies island assignment and obvious outliers; it is not a substitute for manually checking every POI against an authoritative map/source when editorial precision is required.
- External providers (Overpass, GBIF, Open-Meteo, IGN/AEMET sources) can be temporarily unavailable; the disk cache mitigates this in normal operation.
