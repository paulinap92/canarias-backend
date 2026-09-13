from typing import Any

from app.utils.islands import filter_records_by_island


PORTS: list[dict[str, Any]] = [
    {"id": "santa-cruz-tenerife", "name": "Puerto de Santa Cruz de Tenerife", "island": "tenerife", "latitude": 28.4723, "longitude": -16.2414},
    {"id": "los-cristianos", "name": "Puerto de Los Cristianos", "island": "tenerife", "latitude": 28.0494, "longitude": -16.7177},
    {"id": "las-palmas", "name": "Puerto de Las Palmas", "island": "gran-canaria", "latitude": 28.1400, "longitude": -15.4255},
    {"id": "agaete", "name": "Puerto de Las Nieves (Agaete)", "island": "gran-canaria", "latitude": 28.1007, "longitude": -15.7102},
    {"id": "morro-jable", "name": "Puerto de Morro Jable", "island": "fuerteventura", "latitude": 28.0490, "longitude": -14.3617},
    {"id": "puerto-del-rosario", "name": "Puerto de Puerto del Rosario", "island": "fuerteventura", "latitude": 28.4977, "longitude": -13.8560},
    {"id": "corralejo", "name": "Puerto de Corralejo", "island": "fuerteventura", "latitude": 28.7390, "longitude": -13.8638},
    {"id": "playa-blanca", "name": "Puerto de Playa Blanca", "island": "lanzarote", "latitude": 28.8578, "longitude": -13.8333},
    {"id": "arrecife", "name": "Puerto de Arrecife", "island": "lanzarote", "latitude": 28.9674, "longitude": -13.5265},
    {"id": "santa-cruz-la-palma", "name": "Puerto de Santa Cruz de La Palma", "island": "la-palma", "latitude": 28.6776, "longitude": -17.7657},
    {"id": "san-sebastian-gomera", "name": "Puerto de San Sebastián de La Gomera", "island": "la-gomera", "latitude": 28.0872, "longitude": -17.1067},
    {"id": "la-estaca", "name": "Puerto de La Estaca", "island": "el-hierro", "latitude": 27.7858, "longitude": -17.9017},
    {"id": "caleta-sebo", "name": "Puerto de Caleta de Sebo", "island": "la-graciosa", "latitude": 29.2317, "longitude": -13.5020},
    {"id": "orzola", "name": "Puerto de Órzola", "island": "lanzarote", "latitude": 29.2227, "longitude": -13.4521},
]


def get_ports(
    island: str | None = None,
) -> dict[str, Any]:
    selected = filter_records_by_island(
        PORTS,
        island,
    )

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        port["longitude"],
                        port["latitude"],
                    ],
                },
                "properties": {
                    key: value
                    for key, value in port.items()
                    if key not in {
                        "latitude",
                        "longitude",
                    }
                },
            }
            for port in selected
        ],
    }
