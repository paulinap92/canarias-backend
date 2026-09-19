import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.air_quality import router as air_quality_router
from app.api.alerts import router as alerts_router
from app.api.beaches import router as beaches_router
from app.api.capabilities import router as capabilities_router
from app.api.cities import router as cities_router
from app.api.events import router as events_router
from app.api.editor import router as editor_router
from app.api.ferries import router as ferries_router
from app.api.health import router as health_router
from app.api.live import router as live_router
from app.api.marine import router as marine_router
from app.api.monuments import router as monuments_router
from app.api.news import router as news_router
from app.api.places import router as places_router
from app.api.ports import router as ports_router
from app.api.seismic import router as seismic_router
from app.api.tides import router as tides_router
from app.api.trails import router as trails_router
from app.api.transport import router as transport_router
from app.api.today import router as today_router
from app.api.volcanic import router as volcanic_router
from app.api.weather import router as weather_router
from app.api.webcams import router as webcams_router
from app.api.wildlife import router as wildlife_router
from app.api.content import router as content_router
from app.api.data import router as data_router
from app.api.flora import router as flora_router
from app.api.explore import router as explore_router

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Canarias API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cities_router)
app.include_router(weather_router)
app.include_router(air_quality_router)
app.include_router(seismic_router)
app.include_router(monuments_router)
app.include_router(marine_router)
app.include_router(wildlife_router)
app.include_router(places_router)
app.include_router(trails_router)
app.include_router(alerts_router)
app.include_router(news_router)
app.include_router(tides_router)
app.include_router(volcanic_router)
app.include_router(beaches_router)
app.include_router(transport_router)
app.include_router(today_router)
app.include_router(events_router)
app.include_router(editor_router)
app.include_router(webcams_router)
app.include_router(ports_router)
app.include_router(ferries_router)
app.include_router(capabilities_router)
app.include_router(live_router)
app.include_router(health_router)
app.include_router(content_router)
app.include_router(explore_router)
app.include_router(flora_router)
app.include_router(data_router)


async def _refresh_all_islands_once() -> None:
    """Optional maintenance pass against the mounted runtime volume."""
    try:
        from app.tools.refresh_all_islands import run

        logger.info("[DATA MAINTENANCE] full refresh started")
        result = await run(audit_only=False)
        logger.info("[DATA MAINTENANCE] full refresh finished result=%s", result)
    except Exception:
        logger.exception("[DATA MAINTENANCE] full refresh crashed")


async def _refresh_calendar_once() -> None:
    """Refresh only current-month calendars for every island."""
    try:
        import app.data_sources.bootstrap  # noqa: F401
        from app.data_sources import get_data_source
        from app.services.events import current_month
        from app.utils.islands import VALID_ISLANDS

        source = get_data_source("calendar", "events")
        month = current_month()
        logger.info("[DATA MAINTENANCE] calendar refresh started month=%s", month)

        failures = 0
        for island in VALID_ISLANDS:
            payload = await source.refresh(
                island=island,
                month=month,
                refresh_limit=200,
            )
            items = payload.get("items", []) if isinstance(payload, dict) else []
            status = payload.get("status") if isinstance(payload, dict) else "invalid"
            error = payload.get("refresh_error") if isinstance(payload, dict) else None
            if not items:
                failures += 1
            logger.info(
                "[CALENDAR REFRESH] island=%s status=%s count=%s error=%s",
                island,
                status,
                len(items),
                error,
            )

        logger.info("[DATA MAINTENANCE] calendar refresh finished failures=%s", failures)
    except Exception:
        logger.exception("[DATA MAINTENANCE] calendar refresh crashed")


async def _refresh_news_once() -> None:
    """Refresh the merged official news snapshot without running all datasets."""
    try:
        import app.data_sources.bootstrap  # noqa: F401
        from app.data_sources import get_data_source

        source = get_data_source("news", "latest")
        logger.info("[DATA MAINTENANCE] news refresh started")
        payload = await source.refresh(refresh_limit=200)
        items = payload.get("items", []) if isinstance(payload, dict) else []
        status = payload.get("status") if isinstance(payload, dict) else "invalid"
        error = payload.get("refresh_error") if isinstance(payload, dict) else None
        logger.info(
            "[NEWS REFRESH] status=%s count=%s error=%s",
            status,
            len(items),
            error,
        )
    except Exception:
        logger.exception("[DATA MAINTENANCE] news refresh crashed")


@app.on_event("startup")
async def schedule_optional_maintenance() -> None:
    if os.environ.get("CANARIAS_REFRESH_ON_START") == "1":
        asyncio.create_task(_refresh_all_islands_once())
    if os.environ.get("CANARIAS_CALENDAR_REFRESH_ON_START") == "1":
        asyncio.create_task(_refresh_calendar_once())
    if os.environ.get("CANARIAS_NEWS_REFRESH_ON_START") == "1":
        asyncio.create_task(_refresh_news_once())


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Canarias API"}
