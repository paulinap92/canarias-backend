from pydantic import BaseModel, ConfigDict


class RegionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
