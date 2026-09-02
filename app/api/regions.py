from fastapi import APIRouter, HTTPException

from app.db.database import SessionDep
from app.repositories.region import RegionRepository
from app.schemas.region import RegionRead

router = APIRouter(
    prefix="/api/regions",
    tags=["regions"],
)


@router.get("")
async def get_regions(
    session: SessionDep,
) -> list[RegionRead]:
    repository = RegionRepository(session)

    regions = await repository.find_all()

    return [RegionRead.model_validate(region) for region in regions]


@router.get("/{slug}")
async def get_region(
    slug: str,
    session: SessionDep,
) -> RegionRead:
    repository = RegionRepository(session)

    region = await repository.find_by_slug(slug)

    if region is None:
        raise HTTPException(
            status_code=404,
            detail="Region not found",
        )

    return RegionRead.model_validate(region)
