# Canarias Cerca — Content editor and event discovery plan

## Current content editing

Editorial content currently lives in JSON files under:

```
data/guide/content/{island}/{section}.json
```

For immediate manual work, edit those files either in GitHub's web editor or locally in an IDE and push to `main`.

Do not store the future photo library in Git. Git should contain metadata and curated content; media files belong in Cloudflare R2.

## Near-term content editor

Create a small internal editor before content volume becomes large.

Minimum v1:

- island selector
- section selector
- item list
- edit/create form
- slug protected as stable identity
- title / descriptions / tags / source URL
- latitude / longitude when relevant
- photo upload
- photo credit / license / origin
- preview
- validation
- save

The editor should hide raw JSON for normal use but keep the JSON files/API contract underneath at first.

## Photo workflow

Production target: Cloudflare R2.

Object layout:

```
canarias/guide/{island}/{section}/{slug}/original.jpg
canarias/guide/{island}/{section}/{slug}/hero.webp
canarias/guide/{island}/{section}/{slug}/thumb.webp
```

Own photos are preferred whenever practical. Wikimedia Commons, Pexels, Unsplash or other sources may be used only when their exact reuse terms are recorded.

## Event discovery roadmap

Current Calendar uses one primary official agenda source per island. Upgrade this to multi-source discovery.

Priority source classes:

1. island tourism boards
2. cabildos
3. ayuntamientos
4. auditoriums, theatres, museums and cultural centres
5. official festival / fair / sports-event websites
6. other verified organisers

Pipeline:

```
sources -> fetch/parse -> normalize -> deduplicate -> validate dates/location -> classify -> calendar snapshot
```

Store `source`, `source_url`, `source_id` and discovery timestamp for every event.

Deduplicate primarily by normalized title + date + municipality/location, with source URL as supporting evidence.

Prefer official sources when duplicates disagree. Do not invent dates or locations; uncertain records stay unpublished until validated.

Future editor should also have an Events review queue so discovered events can be approved, corrected or rejected manually.
