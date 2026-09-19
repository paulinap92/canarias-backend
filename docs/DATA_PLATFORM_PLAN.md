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


---

## G. Data access and licensing

Prefer public/open datasets as the default foundation for Canarias en datos.

Current working assumptions:
- ISTAC is the primary source for demographic, economic, tourism, employment, housing and environmental statistics.
- Gobierno de Canarias open-data datasets are generally reusable under their published open-data terms; verify the license on each dataset before production use.
- Cabildo / municipal open-data portals should be treated the same way: record source URL, license, attribution text and last update.
- External providers such as AENA, port authorities, transport operators and private ferry companies must be checked individually before integrating or redistributing their data.

For every dataset store:
- source
- dataset_id / canonical source URL
- license
- attribution
- geographic coverage
- update frequency
- last source update
- last Canarias Cerca ingestion
- raw snapshot version

The target is to keep the core data platform close to zero data-acquisition cost by preferring official open data whenever possible.

---

## H. Transport layer — future direction

Treat transport as two related products:

### 1. Transport map / practical mobility

Possible layers:
- bus / guagua stops
- tram stops
- public transport lines
- ferry terminals
- airports
- ports / marinas
- taxi ranks
- park-and-ride
- public parking
- EV charging
- bike infrastructure / shared bikes where open data exists
- road incidents / closures where an official feed exists

### 2. Mobility intelligence

Possible datasets:
- GTFS schedules and route geometries
- origin-destination public-transport flows
- monthly passenger volumes
- transfers
- busiest stops / corridors
- travel-time and accessibility indicators
- inter-island ferry and air connectivity
- seasonality
- service frequency by area / time of day

Avoid claiming real-time vehicle position unless a reliable GTFS-Realtime or equivalent official feed is actually available.

A normalized internal transport model should eventually separate:
- operators
- stops
- routes
- trips
- schedules
- service calendars
- transport modes
- terminals
- origin-destination flows
- live/realtime observations when available


---

## I. Editorial content and CMS direction

Guide is mostly evergreen content and should change relatively slowly after it is populated.

The dynamic editorial layer should live around Actualidad and should be managed through the Canarias Cerca editor.

### Dynamic content types

- News — aggregate from multiple reliable local and official sources, not a single feed.
- Events — multi-source event discovery with review before publication.
- Alerts and closures — trails, roads, beaches, protected areas, weather-related closures and access restrictions.
- Transport updates — diversions, service changes, road disruptions and special event transport.
- Hoy / Este finde briefings — short editorial summaries combining weather, events, alerts and useful local context.
- New openings / relevant changes — important new museums, public spaces, routes, viewpoints, cultural venues or major reopenings.
- Nature updates — relevant environmental notices, seasonal phenomena, protected-area restrictions and significant observations.
- Volcanic / seismic digest — calm, factual summaries when there is meaningful activity.
- Canarias en datos stories — short explainers when ISTAC or another official source publishes meaningful new statistics.
- Seasonal content — carnival, romerías, almond blossom, vendimia, meteor showers, wildlife seasons, tajinaste flowering, etc.
- Editor picks — manually curated weekend / today / seasonal recommendations.

### Actualidad product structure

Possible frontend grouping:

- Hoy
- Noticias
- Eventos
- Alertas
- Transporte
- Cultura
- Naturaleza
- Datos

### Editor as the operational CMS

The editor should become the control center for editorial content rather than only a JSON form.

Shared editorial states:

- discovered
- pending_review
- published
- hidden
- rejected

The editor should support:
- approve
- edit
- hide
- reject
- feature
- merge duplicates where applicable
- source inspection
- image / attribution review
- draft vs published separation

Dynamic sources should write to a discovered/review layer first. Published content should remain a separate, controlled layer.

Live telemetry such as weather, tides, waves and seismic feeds should normally remain read-only in the editor.

---

## J. LLM role in Canarias Cerca

LLM is useful, but it should not be the source of truth and should not sit in every pipeline.

### Good LLM use cases

1. News clustering and summarization
   - group multiple articles about the same story
   - produce a short neutral summary from supplied source material
   - suggest category / tags
   - create a draft for editor review

2. Daily / weekend briefings
   - turn already validated structured data into readable text
   - e.g. weather + alerts + selected events + transport changes
   - all factual values must come from trusted structured sources

3. Data stories
   - draft a human-readable explanation of new ISTAC / transport / environmental statistics
   - calculations and indicators remain deterministic
   - LLM explains the result; it does not compute authoritative metrics

4. Editorial assistance
   - rewrite descriptions
   - shorten long source text
   - propose titles
   - translate ES/EN
   - suggest tags
   - prepare social-media drafts
   - all output can flow through the editor before publication

### Translation workflow TODO

Treat Spanish as the canonical editorial language and generate English from it with LLM assistance.

Apply this to:
- Guide
- Explore descriptions
- Events
- News
- Hoy / Este finde briefings
- Canarias en datos stories
- descriptive alert / transport-update text
- other editorial content managed in the editor

Recommended content model:
- title_es / title_en
- summary_es / summary_en
- description_es / description_en

Editor workflow:
- show whether EN is current or outdated
- mark EN as outdated whenever the canonical ES text changes
- add a "Regenerate translation" action
- allow manual correction of generated EN
- never overwrite a manually edited translation without explicit confirmation
- preserve names, source references, dates and structured factual fields
- keep technical / numeric values outside the translation step where possible

Initial supported languages: Spanish and English only.

5. Search / Q&A later
   - a grounded Canarias Cerca assistant over curated Guide, Explore, Calendar, News and normalized datasets
   - retrieval should provide the source context
   - the answer should cite / link the underlying Canarias Cerca source records

### Where not to use LLM as the decision engine

- weather values
- tides / waves
- seismic measurements
- official alerts
- transport schedules
- event dates when a deterministic source provides them
- statistical calculations
- suitability scoring for ¿Qué hacer hoy? v1
- factual geolocation
- safety or closure state

These remain deterministic and source-backed.

### Principle

DATA / SOURCES -> deterministic validation and calculations -> optional LLM presentation layer -> editor review where editorial content is published

The LLM should mainly help Canarias Cerca write, summarize, organize and explain. It should not invent or replace the underlying data.
