from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.air_quality import router as air_quality_router
from app.api.cities import router as cities_router
from app.api.seismic import router as seismic_router
from app.api.weather import router as weather_router

# Na razie WYŁĄCZONE — wymagają PostgreSQL.
# from app.api.islands import router as islands_router
# from app.api.regions import router as regions_router


app = FastAPI(title="Canarias API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Aktualny MVP bez bazy danych
app.include_router(weather_router)
app.include_router(air_quality_router)
app.include_router(seismic_router)
app.include_router(cities_router)

# Na razie WYŁĄCZONE — wymagają PostgreSQL.
# app.include_router(regions_router)
# app.include_router(islands_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Canarias API"}