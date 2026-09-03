from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.air_quality import router as air_quality_router
from app.api.alerts import router as alerts_router
from app.api.beaches import router as beaches_router
from app.api.cache import router as cache_router
from app.api.cities import router as cities_router
from app.api.marine import router as marine_router
from app.api.monuments import router as monuments_router
from app.api.news import router as news_router
from app.api.places import router as places_router
from app.api.seismic import router as seismic_router
from app.api.tides import router as tides_router
from app.api.trails import router as trails_router
from app.api.volcanic import router as volcanic_router
from app.api.weather import router as weather_router
from app.api.wildlife import router as wildlife_router
from app.middleware.json_cache import JsonDiskCacheMiddleware

# Na razie wyłączone — wymagają PostgreSQL.
# from app.api.islands import router as islands_router
# from app.api.regions import router as regions_router


app = FastAPI(
    title="Canarias API",
)


# Add cache first and CORS second so CORS remains the outer middleware.
app.add_middleware(
    JsonDiskCacheMiddleware,
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
app.include_router(cache_router)

# Na razie wyłączone — wymagają PostgreSQL.
# app.include_router(regions_router)
# app.include_router(islands_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Canarias API",
    }
