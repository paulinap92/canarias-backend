from typing import Any
from fastapi import APIRouter, Query
import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
router=APIRouter(prefix="/api/regions/canarias/wildlife",tags=["wildlife"]); source=get_data_source("explore","fauna")
def trim(data,limit): return {**data,"features":data.get("features",[])[:limit]} if isinstance(data,dict) else data
@router.get("")
async def get_wildlife(limit:int=Query(50,ge=1,le=300),island:str|None=Query(None))->dict[str,Any]: return trim(source.read(island=island),limit)
@router.post("")
async def refresh_wildlife(limit:int=Query(300,ge=1,le=300),island:str|None=Query(None))->dict[str,Any]: return trim(await source.refresh(island=island),limit)
