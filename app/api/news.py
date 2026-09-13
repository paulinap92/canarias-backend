from typing import Any
from fastapi import APIRouter, Query
import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
from app.utils.islands import filter_records_by_island
router=APIRouter(prefix="/api/regions/canarias/news",tags=["news"]); source=get_data_source("news","latest")
def items(payload,island,limit): return filter_records_by_island(payload.get("items",[]),island,include_regional=True)[:limit]
@router.get("")
async def get_news(limit:int=Query(20,ge=1,le=200),island:str|None=Query(None))->list[dict[str,Any]]: return items(source.read(),island,limit)
@router.post("")
async def refresh_news(limit:int=Query(20,ge=1,le=200),island:str|None=Query(None))->list[dict[str,Any]]: return items(await source.refresh(refresh_limit=200),island,limit)
