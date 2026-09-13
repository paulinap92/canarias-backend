from typing import Any
from fastapi import APIRouter, Query
import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
from app.utils.islands import normalize_island
router=APIRouter(tags=["webcams"])
source=get_data_source("live","webcams")
def unsupported(island): return {"island":island,"available":False,"supported_islands":["tenerife"],"items":[]}
@router.get("/api/regions/canarias/webcams")
async def get_webcams(island:str|None=Query(None),limit:int=Query(100,ge=1,le=200))->dict[str,Any]:
    normalized=normalize_island(island)
    if island is not None and normalized!="tenerife": return unsupported(normalized or island)
    payload=source.read(island="tenerife"); return {**payload,"items":payload.get("items",[])[:limit],"supported_islands":["tenerife"]}
@router.post("/api/regions/canarias/webcams")
async def refresh_webcams(island:str|None=Query(None),limit:int=Query(100,ge=1,le=200))->dict[str,Any]:
    normalized=normalize_island(island)
    if island is not None and normalized!="tenerife": return unsupported(normalized or island)
    payload=await source.refresh(island="tenerife"); return {**payload,"items":payload.get("items",[])[:limit],"supported_islands":["tenerife"]}
@router.get("/api/regions/canarias/islands/tenerife/webcams")
async def legacy(limit:int=Query(100,ge=1,le=200))->dict[str,Any]: return await get_webcams(island="tenerife",limit=limit)
