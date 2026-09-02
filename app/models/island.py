from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.region import Region


class Island(Base):
    __tablename__ = "islands"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id"),
        nullable=False,
    )

    region: Mapped["Region"] = relationship(
        back_populates="islands",
    )
