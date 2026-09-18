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
