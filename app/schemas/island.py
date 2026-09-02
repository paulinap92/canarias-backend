from pydantic import BaseModel, ConfigDict


class IslandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    region_id: int
