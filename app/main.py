from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.air_quality import router as air_quality_router
from app.api.islands import router as islands_router
from app.api.regions import router as regions_router
from app.api.weather import router as weather_router
from app.api.seismic import router as seismic_router
from app.api.cities import router as cities_router
# Główna aplikacja FastAPI
app = FastAPI(title="Canarias API")


# CORS pozwala frontendowi działającemu pod innym adresem/portem
# komunikować się z backendem.
#
# Na development:
# frontend może być np. na http://127.0.0.1:5500
# backend na http://127.0.0.1:8000
#
# "*" oznacza: pozwól każdemu originowi.
# Na produkcji zawęzimy to do konkretnej domeny.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Podpinamy moduły API
app.include_router(regions_router)
app.include_router(islands_router)
app.include_router(weather_router)
app.include_router(air_quality_router)
app.include_router(seismic_router)
app.include_router(cities_router)

# Najprostszy endpoint kontrolny
@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Canarias API"}