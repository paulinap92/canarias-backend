# Canarias Cerca — Media storage plan

## Decision

Production media should live in **Cloudflare R2** (S3-compatible object storage), not in Git, not in the Railway filesystem, and not by hotlinking third-party websites.

The backend/database stores metadata; R2 stores the actual image files.

## Object key convention

```
canarias/
  guide/
    {island}/
      {section}/
        {slug}/
          hero.webp
          thumb.webp
  explore/
    {island}/
      {slug}/
        hero.webp
        thumb.webp
  user/
    paulina/
      food/
        papas-arrugadas/
          original.jpg
          hero.webp
          thumb.webp
```

Do not use filenames as identity. The content slug is the stable identity.

## Image metadata

Each curated item should eventually carry:

```json
{
  "image_url": "https://media.canariascerca.../hero.webp",
  "image_source_url": null,
  "image_credit": "Paulina",
  "image_license": "owned",
  "image_license_url": null,
  "image_origin": "own-photo"
}
```

For Wikimedia or another reusable source, keep the author, source page and exact license.

## Production rule

Only render an image when its rights status is known:

- `owned`
- `licensed`
- `public-domain`

Third-party page images discovered automatically are not production assets.

## Temporary development mode

`CANARIAS_DEV_REMOTE_IMAGES=1` enables source-page/RSS image previews so the UI can be designed with realistic imagery.

These images are explicitly marked in API responses as:

- `image_origin = "dev-source-preview"`
- `image_temporary = true`
- `image_rights_status = "unverified"`

Before public production, set:

```
CANARIAS_DEV_REMOTE_IMAGES=0
```

At that point only curated/licensed `image_url` values remain visible.

## Upload pipeline later

1. Upload original image.
2. Validate MIME type and dimensions.
3. Strip unnecessary EXIF metadata.
4. Create optimized WebP/AVIF hero + thumbnail variants.
5. Upload variants to R2.
6. Save media metadata against the content item.
7. Serve through a custom media domain/CDN.

The first perfect test asset is `papas-arrugadas`: replace the temporary preview with Paulina's own photo and mark it `owned`.


## Editorial workflow

Content editing should move in two stages.

### Stage 1 — manual editing now

Curated editorial content lives in:

```
data/guide/content/{island}/{section}.json
```

Examples:

```
data/guide/content/tenerife/food.json
data/guide/content/tenerife/history.json
data/guide/content/la-gomera/nature.json
data/guide/content/gran-canaria/explore.json
```

These files can be edited directly in GitHub's web editor or in a local clone with an IDE. Each item should keep a stable `slug`; URLs and media metadata may change without changing the slug.

Images should not be committed as a growing binary library in Git. Until the R2 upload workflow exists, use dev previews or manually curated external licensed URLs.

### Stage 2 — lightweight content editor

Build an internal editor so normal editorial work does not require editing JSON by hand.

The editor should support:

- island + section selector
- create/edit/delete content item
- title, short description, full description, tags and source URL
- map coordinates where relevant
- image upload
- image credit, origin and license
- live card preview
- validation before save
- write back to the content store without touching application code

The first editor/upload test item should be `tenerife / food / papas-arrugadas`.

## Media upload UX

When R2 is connected, an image workflow should be:

1. choose the content item
2. upload the original photo
3. backend generates hero + thumbnail variants
4. variants are stored in R2
5. the item receives `image_url`, `image_credit`, `image_license` and `image_origin`
6. frontend refreshes with the new image

For own photos use:

```json
{
  "image_credit": "Paulina",
  "image_license": "owned",
  "image_origin": "own-photo"
}
```
