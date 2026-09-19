# Canarias Cerca — Data Platform Roadmap

## Goal

Build a long-term data layer that makes Canarias Cerca useful not only as a map/catalog, but also as a place to understand how the islands move and change over time.

The advantage should come from combining:

1. public statistical datasets,
2. live operational data,
3. curated place data,
4. historical snapshots collected by Canarias Cerca,
5. derived indicators and suitability scores.

The product should progressively move from:

RAW DATA -> NORMALIZED DATA -> ENRICHED DATA -> INTELLIGENCE

---

## A. Statistical data like passenger flows

This is the priority for a future "Canarias en datos" / data section.

### Transport and mobility

- airport passengers by island / airport
- arrivals vs departures
- domestic / international / inter-island traffic
- passenger origin / previous or next territory where available
- monthly and annual trends
- maritime passengers by port
- regular ferry / cruise / excursion passenger traffic
- cruise passengers
- ferry traffic between islands
- air and maritime cargo
- flight / operation counts
- transport seasonality
- mobility indicators from tourist surveys

Primary candidates:
- ISTAC air transport datasets
- ISTAC maritime transport datasets
- AENA where useful
- Puertos Canarios / Puertos del Estado datasets where appropriate

### Tourism demand

- tourist arrivals
- tourists by island
- tourists by origin country
- tourists by age / profile where available
- purpose of trip
- repeat visitors
- duration of stay
- accommodation type
- satisfaction
- activities performed
- mobility during the trip
- seasonality

Primary source:
- ISTAC tourism demand / tourist expenditure surveys

### Tourist spending

- total tourist expenditure
- expenditure per tourist
- expenditure per day
- expenditure by island
- expenditure by municipality
- expenditure by country of origin
- expenditure by category if available
- quarterly / annual comparison

Primary source:
- ISTAC Encuesta sobre Gasto Turístico

### Accommodation

- hotel occupancy
- apartment occupancy
- vacation-rental occupancy
- overnight stays
- average stay
- beds / rooms available
- establishments open
- occupancy by rooms and beds
- prices
- revenue / profitability indicators
- employment in accommodation
- municipality / island / microdestination comparison

Primary source:
- ISTAC Encuestas de Alojamiento Turístico

### Cruise and port activity

- passengers by port
- regular passenger traffic
- cruise traffic
- excursion traffic
- monthly trends
- seasonality
- port comparison

---

## B. Other public statistical layers worth adding later

### Population and territory

- population by island / municipality
- age structure
- resident vs non-resident population where available
- population growth
- density
- migration
- households

### Economy and employment

- employment / unemployment
- employment by sector
- business counts
- tourism-sector employment
- salaries / income indicators where available
- GDP / economic indicators by island where meaningful

### Housing and tourism pressure

- vacation rental supply
- hotel / apartment capacity
- tourist beds vs resident population
- housing prices / rents where a reliable public source exists
- tourism intensity indicators
- overnight stays per resident
- passengers / tourists per resident

These should be descriptive indicators, not political conclusions.

### Environment and resources

- water consumption / reservoirs where public data exists
- electricity demand / renewable generation
- waste generation
- protected areas
- wildfire history
- air quality history
- temperature / rainfall climatology

---

## C. Canarias Cerca historical datasets

Persist snapshots over time instead of only showing current values.

Examples:

- weather by place / island
- wind
- waves / swell
- tides
- air quality / calima
- alerts
- volcanic / seismic activity
- closures
- passenger statistics when new official releases appear
- tourism and accommodation releases

This creates an internal historical dataset that can later power comparisons and models.

---

## D. Derived Canarias Cerca indicators

Do not just copy source tables. Build derived values after the raw datasets are reliable.

Examples:

- tourism seasonality index
- airport growth by island
- ferry / air modal share where comparable
- tourist spending per visitor
- overnight stays per tourist
- occupancy pressure
- tourism intensity per resident
- cruise seasonality
- inter-island mobility trend
- "busy month" / "quiet month" comparisons
- weather suitability by activity
- beach / hiking / surf / stargazing scores

Every derived metric must keep:
- source dataset
- source period
- formula / methodology
- geographic level
- last update timestamp

---

## E. Future product surfaces

Possible UI modules:

### Canarias en datos

Dashboard with:
- overview cards
- island selector
- time range
- trend charts
- island comparison
- source and last-updated metadata

Suggested sections:
- Pasajeros
- Turismo
- Alojamiento
- Gasto
- Puertos y cruceros
- Población
- Economía
- Vivienda / presión turística
- Medio ambiente

### Island profile

Each island page can expose compact indicators:
- airport passengers
- ferry passengers
- tourists
- hotel occupancy
- tourist spend
- population
- seasonal patterns

### Data API

Normalized internal endpoints independent from ISTAC's raw schema, e.g.:

- /api/regions/canarias/data/air-passengers
- /api/regions/canarias/data/maritime-passengers
- /api/regions/canarias/data/tourism
- /api/regions/canarias/data/accommodation
- /api/regions/canarias/data/tourist-spend

---

## F. Separate but related long-term intelligence plan

Keep for later:

- richer place metadata
- family / accessibility / parking / booking / difficulty attributes
- historical weather per place
- microclimate comparisons
- crowd-risk estimates only when supported by real data
- ¿Qué hacer hoy? suitability engine
- best time today
- beach / hiking / surf / stargazing / sunset / swimming scores

The aim is eventually to combine statistical context with place-level and live data, rather than treating these as isolated dashboards.
