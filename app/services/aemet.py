from typing import Any

import httpx

from app.config import AEMET_API_KEY
import json

AEMET_BASE_URL = "https://opendata.aemet.es/opendata/api"


async def fetch_daily_forecast(
    municipality_code: str,
) -> Any:
    if not AEMET_API_KEY:
        raise RuntimeError("AEMET_API_KEY is not configured")

    url = (
        f"{AEMET_BASE_URL}/prediccion/especifica/"
        f"municipio/diaria/{municipality_code}"
    )

    headers = {
        "api_key": AEMET_API_KEY,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            url,
            headers=headers,
        )
        response.raise_for_status()

        metadata = response.json()

        data_url = metadata["datos"]

        data_response = await client.get(data_url)
        data_response.raise_for_status()

        text = data_response.content.decode("latin-1")
        return json.loads(text)