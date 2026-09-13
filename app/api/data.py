from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException, Query
import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
router=APIRouter(prefix="/api/regions/canarias/data",tags=["data"])
def _source(section:str,resource:str):
    try:return get_data_source(section,resource)
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
@router.get("/{section}/{resource}")
async def read_data(section:str,resource:str,island:str|None=Query(None),month:str|None=Query(None),hours:int=Query(48,ge=12,le=120))->Any:
    return _source(section,resource).read(island=island,month=month,hours=hours)
@router.post("/{section}/{resource}")
async def refresh_data(section:str,resource:str,island:str|None=Query(None),month:str|None=Query(None),hours:int=Query(48,ge=12,le=120))->Any:
    return await _source(section,resource).refresh(island=island,month=month,hours=hours)
