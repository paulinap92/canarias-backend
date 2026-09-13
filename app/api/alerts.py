from typing import Any
from fastapi import APIRouter, Query
import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
router=APIRouter(prefix="/api/regions/canarias/alerts",tags=["alerts"]); source=get_data_source("live","alerts")
@router.get("")
async def get_alerts(island:str|None=Query(None))->list[dict[str,Any]]: return source.read(island=island).get("items",[])
@router.post("")
async def refresh_alerts(island:str|None=Query(None))->list[dict[str,Any]]: return (await source.refresh(island=island)).get("items",[])
