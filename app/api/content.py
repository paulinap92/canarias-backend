from typing import Any
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import RedirectResponse

from app.services.content import (
    VALID_SECTIONS,
    get_content,
    get_content_item,
)
from app.services.content_images import (
    dev_remote_images_enabled,
    resolve_content_image_url,
)


router = APIRouter(
    prefix="/api/regions/canarias/content",
    tags=["content"],
)


def _dev_source_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        if item.get("image_url"):
            continue
        source_url = str(item.get("source_url") or item.get("url") or "").strip()
        if source_url:
            counts[source_url] = counts.get(source_url, 0) + 1
    return counts


def _with_resolved_image_route(
    item: dict[str, Any],
    *,
    request: Request,
    island: str,
    section: str,
    allow_dev_source: bool = True,
) -> dict[str, Any]:
    current = dict(item)
    if current.get("image_url"):
        current.setdefault("image_origin", "curated")
        return current

    if not dev_remote_images_enabled() or not allow_dev_source:
        return current

    slug = current.get("slug")
    source_url = current.get("source_url") or current.get("url")
    if not slug or not source_url:
        return current

    image_endpoint = str(
        request.url_for(
            "content_image",
            slug=str(slug),
        )
    )
    current["image_url"] = (
        image_endpoint
        + "?"
        + urlencode(
            {
                "island": island,
                "section": section,
                "preview": "strict-v2",
            }
        )
    )
    current["image_resolved_from_source"] = True
    current["image_origin"] = "dev-source-preview"
    current["image_temporary"] = True
    current["image_rights_status"] = "unverified"
    current["image_credit"] = "DEV preview · imagen de la fuente"
    current["image_source_url"] = str(source_url)
    return current


@router.get("")
async def content_list(
    request: Request,
    island: str = Query(...),
    section: str = Query(...),
    limit: int = Query(
        50,
        ge=1,
        le=200,
    ),
    featured_only: bool = Query(False),
) -> dict[str, Any]:
    data = get_content(
        island=island,
        section=section,
        limit=limit,
        featured_only=featured_only,
    )

    normalized_island = str(data.get("island") or island)
    raw_items = list(data.get("items", []))
    source_counts = _dev_source_counts(raw_items)

    data["items"] = [
        _with_resolved_image_route(
            item,
            request=request,
            island=normalized_island,
            section=section,
            allow_dev_source=(
                source_counts.get(
                    str(item.get("source_url") or item.get("url") or "").strip(),
                    0,
                )
                <= 1
            ),
        )
        for item in raw_items
    ]
    return data


@router.get("/{slug}/image", name="content_image")
async def content_image(
    slug: str,
    island: str = Query(...),
    section: str = Query(...),
):
    if not dev_remote_images_enabled():
        raise HTTPException(
            status_code=404,
            detail="Remote image previews are disabled",
        )

    if section not in VALID_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid content section",
        )

    item = get_content_item(
        island=island,
        section=section,
        slug=slug,
    )
    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Content item not found",
        )

    image_url = await resolve_content_image_url(item)
    if not image_url:
        raise HTTPException(
            status_code=404,
            detail="No item-specific image available",
        )

    return RedirectResponse(
        url=image_url,
        status_code=307,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{slug}")
async def content_detail(
    request: Request,
    slug: str,
    island: str = Query(...),
    section: str = Query(...),
) -> dict[str, Any]:
    if section not in VALID_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid content section",
        )

    item = get_content_item(
        island=island,
        section=section,
        slug=slug,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Content item not found",
        )

    section_items = get_content(
        island=island,
        section=section,
        limit=1000,
    ).get("items", [])
    source_counts = _dev_source_counts(section_items)
    source_url = str(item.get("source_url") or item.get("url") or "").strip()

    return _with_resolved_image_route(
        item,
        request=request,
        island=island,
        section=section,
        allow_dev_source=source_counts.get(source_url, 0) <= 1,
    )
