from typing import Any

from fastapi import APIRouter, HTTPException

from app.utils.islands import normalize_island


router = APIRouter(
    prefix="/api/regions/canarias/islands",
    tags=["capabilities"],
)


@router.get("/{island}/capabilities")
async def island_capabilities(
    island: str,
) -> dict[str, Any]:
    normalized = normalize_island(island)

    if normalized is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown island",
        )

    return {
        "island": normalized,
        "features": {
            "cities": True,
            "weather": True,
            "air_quality": True,
            "seismic": True,
            "marine": True,
            "tides": True,
            "monuments": normalized != "la-graciosa",
            "places": True,
            "beaches": True,
            "trails": True,
            "wildlife": True,
            "flora": True,
            "news": True,
            "alerts": True,
            "volcanic": True,
            "events": True,
            "webcams": normalized == "tenerife",
            "airports": normalized != "la-graciosa",
            "titsa": normalized == "tenerife",
            "ports": True,
            "ferries": True,
        },
        "notes": {
            "news": (
                "Regional Gobierno de Canarias news may appear "
                "for every island."
            ),
            "events": (
                "Official island tourism agendas are supported for all eight islands; empty months are valid."
            ),
            "webcams": (
                "Current webcam source covers Tenerife only."
            ),
        },
    }
