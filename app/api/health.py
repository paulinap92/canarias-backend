from typing import Any

from fastapi import APIRouter

from app.data_sources.store import DATA_ROOT


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    try:
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
        probe = DATA_ROOT / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        writable = True
        storage_error = None
    except OSError as error:
        writable = False
        storage_error = str(error)

    json_files = list(DATA_ROOT.rglob("*.json")) if DATA_ROOT.exists() else []

    return {
        "status": "ok" if writable else "degraded",
        "api": "ok",
        "storage": {
            "data_root": str(DATA_ROOT),
            "writable": writable,
            "error": storage_error,
        },
        "snapshots": {
            "files_count": len(json_files),
            "total_size_bytes": sum(path.stat().st_size for path in json_files),
        },
    }
