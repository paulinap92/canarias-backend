from fastapi import APIRouter

from app.db.database import SessionDep
from app.repositories.island import IslandRepository
from app.schemas.island import IslandRead

router = APIRouter(
    prefix="/api/regions/{region_slug}/islands",
    tags=["islands"],
)


@router.get("")
async def get_islands(
    region_slug: str,
    session: SessionDep,
) -> list[IslandRead]:
    repository = IslandRepository(session)

    islands = await repository.find_by_region_slug(region_slug)

    return [IslandRead.model_validate(island) for island in islands]
