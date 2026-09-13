from typing import Any
from fastapi import APIRouter, Query
import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
router=APIRouter(prefix="/api/regions/canarias/live",tags=["live"])
def src(name): return get_data_source("live",name)
@router.get("/weather")
async def live_weather(island:str|None=Query(None))->dict[str,Any]: return src("weather").read(island=island)
@router.post("/weather")
async def refresh_live_weather(island:str|None=Query(None))->dict[str,Any]: return await src("weather").refresh(island=island)
@router.get("/air-quality")
async def live_air_quality(island:str|None=Query(None))->dict[str,Any]: return src("air-quality").read(island=island)
@router.post("/air-quality")
async def refresh_live_air_quality(island:str|None=Query(None))->dict[str,Any]: return await src("air-quality").refresh(island=island)
@router.get("/marine")
async def live_marine(island:str|None=Query(None))->dict[str,Any]: return src("marine").read(island=island)
@router.post("/marine")
async def refresh_live_marine(island:str|None=Query(None))->dict[str,Any]: return await src("marine").refresh(island=island)
@router.get("/tides")
async def live_tides(island:str|None=Query(None),hours:int=Query(48,ge=12,le=96))->dict[str,Any]: return src("tides").read(island=island,hours=hours)
@router.post("/tides")
async def refresh_live_tides(island:str|None=Query(None),hours:int=Query(48,ge=12,le=96))->dict[str,Any]: return await src("tides").refresh(island=island,hours=hours)
