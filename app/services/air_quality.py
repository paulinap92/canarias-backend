import csv
import io
from typing import Any

import httpx


BASE_URL = "https://www3.gobiernodecanarias.org"
STATION_ID = "37"  # Tome Cano

PM10_TABLE = "987792"
PM25_TABLE = "987793"


async def _fetch_csv(
    client: httpx.AsyncClient,
    table_id: str,
) -> list[dict[str, str]]:
    url = (
        f"{BASE_URL}/medioambiente/calidaddelaire/"
        f"datosOnLineEstacion.jsp"
        f"?ides={STATION_ID}"
        f"&d-{table_id}-e=1"
        f"&6578706f7274=1"
    )

    response = await client.get(url)
    response.raise_for_status()

    text = response.content.decode("iso-8859-1")

    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def latest_value(
    rows: list[dict[str, str]],
    column: str,
) -> tuple[str, str, str] | None:
    for row in rows:
        value = row.get(column, "").strip()

        if value:
            return row["Fecha"], row["Hora"], value

    return None


def get_calima_status(
    pm10: float | None,
) -> dict[str, str]:
    # To jest nasz uproszczony wskaźnik oparty na PM10,
    # a nie oficjalny alert calimy.
    if pm10 is None:
        return {
            "level": "unknown",
            "color": "gray",
        }

    if pm10 < 40:
        return {
            "level": "low",
            "color": "green",
        }

    if pm10 < 80:
        return {
            "level": "moderate",
            "color": "orange",
        }

    return {
        "level": "high",
        "color": "red",
    }


async def fetch_air_quality() -> dict[str, Any]:
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=20.0,
    ) as client:
        # 1. Otwieramy stronę główną, żeby dostać sesję.
        await client.get(
            f"{BASE_URL}/medioambiente/calidaddelaire/datosOnLine.do"
        )

        # 2. Wybieramy tryb "por estación".
        await client.post(
            f"{BASE_URL}/medioambiente/calidaddelaire/"
            "seleccionDatosOnLine.do",
            data={"seleccion": "0"},
        )

        # 3. Wybieramy stację Tome Cano.
        await client.post(
            f"{BASE_URL}/medioambiente/calidaddelaire/"
            "datosOnLineEstacion.do",
            data={"ides": STATION_ID},
        )

        # 4. Pobieramy tabele CSV.
        pm10_rows = await _fetch_csv(
            client,
            PM10_TABLE,
        )

        pm25_rows = await _fetch_csv(
            client,
            PM25_TABLE,
        )

        # 5. Bierzemy najnowszą niepustą wartość
        # dla każdego parametru.
        pm10 = latest_value(
            pm10_rows,
            "PM10 (µg/m³)",
        )

        pm25 = latest_value(
            pm25_rows,
            "PM2.5 (µg/m³)",
        )

        o3 = latest_value(
            pm10_rows,
            "O3 (µg/m³)",
        )

        co = latest_value(
            pm10_rows,
            "CO (mg/m³)",
        )

        so2 = latest_value(
            pm25_rows,
            "SO2 (µg/m³)",
        )

        no2 = latest_value(
            pm25_rows,
            "NO2 (µg/m³)",
        )

        # PM10 konwertujemy na liczbę,
        # żeby wyznaczyć nasz prosty status calimy.
        pm10_value = (
            float(pm10[2].replace(",", "."))
            if pm10
            else None
        )

        calima = get_calima_status(
            pm10_value
        )

        return {
            "station": "Tome Cano",
            "date": pm10[0] if pm10 else None,
            "time": pm10[1] if pm10 else None,
            "pm10": pm10[2] if pm10 else None,
            "pm25": pm25[2] if pm25 else None,
            "o3": o3[2] if o3 else None,
            "co": co[2] if co else None,
            "so2": so2[2] if so2 else None,
            "no2": no2[2] if no2 else None,
            "calima": calima,
        }