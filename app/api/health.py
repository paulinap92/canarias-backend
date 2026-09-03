import os
from typing import Any

from fastapi import APIRouter

from app.middleware.json_cache import CACHE_DIR


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    try:
        CACHE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        probe = CACHE_DIR / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)

        writable = True
        storage_error = None

    except OSError as error:
        writable = False
        storage_error = str(error)

    files = (
        list(CACHE_DIR.glob("*.json"))
        if CACHE_DIR.exists()
        else []
    )

    return {
        "status": "ok" if writable else "degraded",
        "api": "ok",
        "storage": {
            "cache_dir": str(CACHE_DIR),
            "railway_volume_mount_path": os.getenv(
                "RAILWAY_VOLUME_MOUNT_PATH"
            ),
            "writable": writable,
            "error": storage_error,
        },
        "cache": {
            "files_count": len(files),
            "total_size_bytes": sum(
                path.stat().st_size
                for path in files
            ),
        },
    }
