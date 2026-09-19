# Canarias Cerca — Content Editor

A local/internal editor for curated Guide and Explore JSON content.

## Run locally

From the backend repository:

### PowerShell

```powershell
$env:CANARIAS_CONTENT_EDITOR="1"
uv run uvicorn app.main:app --reload
```

Open:

```
http://127.0.0.1:8000/editor
```

The editor writes directly to:

```
data/guide/content/{island}/{section}.json
```

After editing, review the Git diff and commit the changed JSON files normally.

## Safety

The editor is disabled by default.

On localhost, no token is required.

If you intentionally expose it remotely, set both:

```
CANARIAS_CONTENT_EDITOR=1
CANARIAS_CONTENT_EDITOR_TOKEN=<long-random-secret>
```

Remote requests require that token as a Bearer token. Do not enable the editor publicly without access protection.

## Current v1

- island + section navigation
- list existing items
- create / edit / delete
- stable slug protection
- descriptions, tags, category, coordinates, source URL
- image URL + attribution/license metadata
- image preview
- advanced JSON editor for fields without a dedicated form
- atomic JSON writes

## Images

Direct photo upload is intentionally not active until Cloudflare R2 is configured.

For now:
- use curated/licensed `image_url` values, or
- leave the image empty and use the temporary dev resolver.

The R2 upload flow is the next media step: upload original → optimize → store → write metadata back to the content item.
