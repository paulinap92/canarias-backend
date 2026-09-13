from typing import Any
from fastapi import APIRouter
import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
router=APIRouter(prefix="/api/regions/canarias/volcanic",tags=["volcanic"]); source=get_data_source("live","volcanic")
@router.get("")
async def get_volcanic_activity()->dict[str,Any]: return source.read(island="canarias")
@router.post("")
async def refresh_volcanic_activity()->dict[str,Any]: return await source.refresh(island="canarias")
