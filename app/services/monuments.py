import json
from pathlib import Path
from typing import Any


DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "monuments.json"
)


def load_monuments() -> list[dict[str, Any]]:
    with DATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)