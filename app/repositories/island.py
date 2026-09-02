from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.island import Island
from app.models.region import Region
from app.repositories.base import GenericRepository


class IslandRepository(GenericRepository[Island]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Island, session)

    async def find_by_region_slug(self, region_slug: str) -> list[Island]:
        stmt = select(Island).join(Region).where(Region.slug == region_slug)

        result = await self.session.scalars(stmt)

        return list(result.all())
