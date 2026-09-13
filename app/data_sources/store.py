from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data"
STATE_FILE = DATA_ROOT / "state" / "sources.json"
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
def read_json(path: Path, default: Any) -> Any:
    if not path.exists(): return default
    return json.loads(path.read_text(encoding="utf-8"))
def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
def update_source_state(key: str, *, success: bool, error: str | None = None, count: int | None = None) -> None:
    state = read_json(STATE_FILE, {})
    item = dict(state.get(key, {}))
    if success:
        item["last_success"] = utc_now(); item["last_error"] = None
        if count is not None: item["count"] = count
    else:
        item["last_error"] = error; item["last_error_at"] = utc_now()
    state[key] = item
    write_json_atomic(STATE_FILE, state)
