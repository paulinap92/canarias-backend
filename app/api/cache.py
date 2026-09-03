import os
import time
from typing import Any

from fastapi import APIRouter

from app.middleware.json_cache import CACHE_DIR


router = APIRouter(
    prefix="/api/cache",
    tags=["cache"],
)


@router.get("/status")
async def cache_status() -> dict[str, Any]:
    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = sorted(
        CACHE_DIR.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    entries = []

    for path in files[:100]:
        stat = path.stat()

        entries.append(
            {
                "file": path.name,
                "size_bytes": stat.st_size,
                "age_seconds": round(
                    time.time() - stat.st_mtime,
                    1,
                ),
            }
        )

    return {
        "cache_dir": str(CACHE_DIR),
        "railway_volume_mount_path": os.getenv(
            "RAILWAY_VOLUME_MOUNT_PATH"
        ),
        "files_count": len(files),
        "total_size_bytes": sum(
            path.stat().st_size
            for path in files
        ),
        "files": entries,
    }
