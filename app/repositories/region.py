from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.region import Region
from app.repositories.base import GenericRepository


class RegionRepository(GenericRepository[Region]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Region, session)

    async def find_by_slug(self, slug: str) -> Region | None:
        stmt = select(Region).where(Region.slug == slug)
        result = await self.session.scalars(stmt)

        return result.first()
