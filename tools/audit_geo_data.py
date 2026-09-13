from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.utils.islands import VALID_ISLANDS, normalize_island, point_is_on_island

DATA = ROOT / "data"

STATIC_FILES = [
    DATA / "weather_points.json",
    DATA / "air_quality_points.json",
    DATA / "coastal_points.json",
    DATA / "monuments.json",
]

EXPECTED_CONTENT_SECTIONS = {
    "explore",
    "food",
    "culture",
    "music",
    "fiestas",
    "products",
    "stories",
    "crafts",
    "heritage",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_record(record: dict[str, Any], source: str, errors: list[str]) -> None:
    name = record.get("name") or record.get("id") or "<unnamed>"
    island = normalize_island(record.get("island"))
    if island is None:
        errors.append(f"{source}: {name}: invalid/missing island={record.get('island')!r}")
        return

    latitude = record.get("latitude")
    longitude = record.get("longitude")
    if latitude is None and longitude is None:
        return
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        errors.append(f"{source}: {name}: invalid coordinate types")
        return

    if not point_is_on_island(float(longitude), float(latitude), island):
        errors.append(
            f"{source}: {name}: ({latitude}, {longitude}) outside {island} bounds"
        )


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for path in STATIC_FILES:
        rows = _load(path)
        if not isinstance(rows, list):
            errors.append(f"{path.relative_to(ROOT)}: expected list")
            continue
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                errors.append(f"{path.relative_to(ROOT)}: non-object row")
                continue
            key = str(row.get("id") or "")
            if key and key in seen:
                errors.append(f"{path.relative_to(ROOT)}: duplicate id {key}")
            seen.add(key)
            _check_record(row, str(path.relative_to(ROOT)), errors)

    content_root = DATA / "guide" / "content"
    for island in VALID_ISLANDS:
        island_dir = content_root / island
        if not island_dir.exists():
            warnings.append(f"content/{island}: directory missing")
            continue

        existing = {path.stem for path in island_dir.glob("*.json")}
        missing = sorted(EXPECTED_CONTENT_SECTIONS - existing)
        if missing:
            warnings.append(f"content/{island}: missing sections: {', '.join(missing)}")

        explore = island_dir / "explore.json"
        if not explore.exists():
            continue
        rows = _load(explore)
        if not isinstance(rows, list):
            errors.append(f"content/{island}/explore.json: expected list")
            continue
        for row in rows:
            if isinstance(row, dict):
                _check_record(row, f"content/{island}/explore.json", errors)

    print("GEO AUDIT")
    print("=========")
    print(f"errors: {len(errors)}")
    for error in errors:
        print(f"ERROR: {error}")
    print(f"warnings: {len(warnings)}")
    for warning in warnings:
        print(f"WARN: {warning}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
