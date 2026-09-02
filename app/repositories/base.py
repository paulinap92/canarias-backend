from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class GenericRepository[T: Base]:
    def __init__(
        self,
        model_type: type[T],
        session: AsyncSession,
    ) -> None:
        self.model_type = model_type
        self.session = session

    async def find_all(self) -> list[T]:
        stmt = select(self.model_type)
        result = await self.session.scalars(stmt)

        return list(result.all())
