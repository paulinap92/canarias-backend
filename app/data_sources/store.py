from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("uvicorn.error")

ROOT = Path(__file__).resolve().parents[2]
PACKAGED_DATA_ROOT = ROOT / "data"
DATA_ROOT = Path(
    os.environ.get("CANARIAS_DATA_ROOT", str(PACKAGED_DATA_ROOT))
).expanduser()
STATE_FILE = DATA_ROOT / "state" / "sources.json"


def _seed_runtime_data_root() -> int:
    """Seed an external runtime data directory without overwriting it.

    In production Railway mounts a persistent volume at /data. The repository
    data tree is only the initial seed. Existing runtime files always win, so a
    deploy can never replace refreshed JSON with an older copy from GitHub.
    """
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    try:
        same_root = DATA_ROOT.resolve() == PACKAGED_DATA_ROOT.resolve()
    except OSError:
        same_root = DATA_ROOT == PACKAGED_DATA_ROOT

    if same_root or not PACKAGED_DATA_ROOT.exists():
        return 0

    copied = 0
    for source in PACKAGED_DATA_ROOT.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(PACKAGED_DATA_ROOT)
        target = DATA_ROOT / relative
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1

    return copied


SEEDED_FILES = _seed_runtime_data_root()
logger.info(
    "[DATA STORE] packaged_root=%s runtime_root=%s seeded_files=%s",
    PACKAGED_DATA_ROOT,
    DATA_ROOT,
    SEEDED_FILES,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def update_source_state(
    key: str,
    *,
    success: bool,
    error: str | None = None,
    count: int | None = None,
) -> None:
    state = read_json(STATE_FILE, {})
    item = dict(state.get(key, {}))
    if success:
        item["last_success"] = utc_now()
        item["last_error"] = None
        if count is not None:
            item["count"] = count
    else:
        item["last_error"] = error
        item["last_error_at"] = utc_now()
    state[key] = item
    write_json_atomic(STATE_FILE, state)
