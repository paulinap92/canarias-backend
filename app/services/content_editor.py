from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from app.services.content import CONTENT_ROOT, VALID_SECTIONS
from app.utils.islands import normalize_island


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ContentEditorError(ValueError):
    pass


def content_root() -> Path:
    override = os.environ.get("CANARIAS_CONTENT_ROOT", "").strip()
    return Path(override) if override else CONTENT_ROOT


def content_path(island: str, section: str) -> Path:
    normalized = normalize_island(island)
    if normalized is None:
        raise ContentEditorError(f"Unknown island: {island}")
    if section not in VALID_SECTIONS:
        raise ContentEditorError(f"Unknown section: {section}")
    return content_root() / normalized / f"{section}.json"


def read_items(island: str, section: str) -> list[dict[str, Any]]:
    path = content_path(island, section)
    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ContentEditorError(f"Expected a JSON array in {path}")

    return [dict(item) for item in payload if isinstance(item, dict)]


def _validate_item(item: dict[str, Any]) -> dict[str, Any]:
    clean = dict(item)
    slug = str(clean.get("slug") or "").strip()

    if not slug or not SLUG_RE.fullmatch(slug):
        raise ContentEditorError(
            "slug must use lowercase letters, numbers and hyphens only"
        )

    name = str(clean.get("name") or clean.get("title") or "").strip()
    if not name:
        raise ContentEditorError("name or title is required")

    clean["slug"] = slug
    if clean.get("order") not in (None, ""):
        try:
            clean["order"] = int(clean["order"])
        except (TypeError, ValueError) as exc:
            raise ContentEditorError("order must be an integer") from exc

    for key in ("latitude", "longitude"):
        if clean.get(key) in (None, ""):
            clean.pop(key, None)
            continue
        try:
            clean[key] = float(clean[key])
        except (TypeError, ValueError) as exc:
            raise ContentEditorError(f"{key} must be numeric") from exc

    if "tags" in clean and not isinstance(clean["tags"], list):
        raise ContentEditorError("tags must be an array")

    return clean


def _write_items(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def create_item(island: str, section: str, item: dict[str, Any]) -> dict[str, Any]:
    clean = _validate_item(item)
    items = read_items(island, section)

    if any(str(existing.get("slug")) == clean["slug"] for existing in items):
        raise ContentEditorError(f"slug already exists: {clean['slug']}")

    if not clean.get("id"):
        clean["id"] = f"{section}-{normalize_island(island)}-{clean['slug']}"

    items.append(clean)
    _write_items(content_path(island, section), items)
    return clean


def update_item(
    island: str,
    section: str,
    original_slug: str,
    item: dict[str, Any],
) -> dict[str, Any]:
    clean = _validate_item(item)
    if clean["slug"] != original_slug:
        raise ContentEditorError(
            "slug is a stable identity and cannot be changed in the editor"
        )

    items = read_items(island, section)
    for index, existing in enumerate(items):
        if str(existing.get("slug")) == original_slug:
            if not clean.get("id") and existing.get("id"):
                clean["id"] = existing["id"]
            items[index] = clean
            _write_items(content_path(island, section), items)
            return clean

    raise ContentEditorError(f"item not found: {original_slug}")


def delete_item(island: str, section: str, slug: str) -> None:
    items = read_items(island, section)
    filtered = [item for item in items if str(item.get("slug")) != slug]
    if len(filtered) == len(items):
        raise ContentEditorError(f"item not found: {slug}")
    _write_items(content_path(island, section), filtered)
