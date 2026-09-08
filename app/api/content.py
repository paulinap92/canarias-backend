from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from app.services.content import (
    VALID_SECTIONS,
    get_content,
    get_content_item,
)


router = APIRouter(
    prefix="/api/regions/canarias/content",
    tags=["content"],
)


@router.get("")
async def content_list(
    island: str = Query(...),
    section: str = Query(...),
    limit: int = Query(
        50,
        ge=1,
        le=200,
    ),
    featured_only: bool = Query(False),
) -> dict[str, Any]:

    return get_content(
        island=island,
        section=section,
        limit=limit,
        featured_only=featured_only,
    )


@router.get("/{slug}")
async def content_detail(
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

    return item