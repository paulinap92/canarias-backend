from typing import Any
from fastapi import APIRouter, Query
import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
router=APIRouter(prefix="/api/regions/canarias/seismic",tags=["seismic"]); source=get_data_source("live","seismic")
@router.get("")
async def get_canary_earthquakes(island:str|None=Query(None))->dict[str,Any]: return source.read(island=island)
@router.post("")
async def refresh_canary_earthquakes(island:str|None=Query(None))->dict[str,Any]: return await source.refresh(island=island)
