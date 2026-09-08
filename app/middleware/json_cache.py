from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp


logger = logging.getLogger(__name__)


def get_cache_dir() -> Path:
    explicit = os.getenv("CACHE_DIR")
    if explicit:
        return Path(explicit)

    railway_mount = os.getenv(
        "RAILWAY_VOLUME_MOUNT_PATH"
    )
    if railway_mount:
        return Path(
            railway_mount
        ) / "cache"

    return Path("data/cache")


CACHE_DIR = get_cache_dir()


CACHE_RULES: tuple[tuple[str, int], ...] = (
    ("/weather", 30 * 60),
    ("/air-quality", 15 * 60),
    ("/seismic", 10 * 60),
    ("/marine", 30 * 60),
    ("/tides", 60 * 60),
    ("/alerts", 10 * 60),
    ("/news", 10 * 60),
    ("/volcanic", 6 * 60 * 60),
    ("/places", 24 * 60 * 60),
    ("/beaches", 24 * 60 * 60),
    ("/trails", 24 * 60 * 60),
    ("/wildlife", 6 * 60 * 60),
    ("/transport/", 24 * 60 * 60),
    ("/events", 60 * 60),
    ("/webcams", 6 * 60 * 60),
)


def _ttl_for_path(
    path: str,
) -> int | None:
    for marker, ttl_seconds in CACHE_RULES:
        if marker in path:
            return ttl_seconds
    return None


def _canonical_request_key(
    request: Request,
) -> str:
    query_items = sorted(
        request.query_params.multi_items()
    )
    query = urlencode(query_items)

    if query:
        return (
            f"{request.url.path}?{query}"
        )

    return request.url.path


def _cache_file_for(
    request: Request,
) -> Path:
    canonical = _canonical_request_key(
        request
    )

    readable = (
        request.url.path.strip("/")
        or "root"
    )
    readable = re.sub(
        r"[^a-zA-Z0-9._-]+",
        "_",
        readable,
    )
    readable = readable[-120:]

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()[:12]

    return (
        CACHE_DIR
        / f"{readable}__{digest}.json"
    )


def _is_fresh(
    path: Path,
    ttl_seconds: int,
) -> bool:
    if not path.exists():
        return False

    age = (
        time.time()
        - path.stat().st_mtime
    )

    return age <= ttl_seconds


def _read_cached_response(
    path: Path,
    cache_state: str,
) -> Response:
    body = path.read_bytes()

    return Response(
        content=body,
        status_code=200,
        headers={
            "X-Canarias-Cache": (
                cache_state
            ),
        },
        media_type="application/json",
    )


def _write_atomic(
    path: Path,
    body: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = path.with_suffix(
        f"{path.suffix}.tmp"
    )

    temp_path.write_bytes(body)
    temp_path.replace(path)


class JsonDiskCacheMiddleware(
    BaseHTTPMiddleware
):
    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        super().__init__(app)

        try:
            CACHE_DIR.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError:
            logger.exception(
                "Could not create cache directory: %s",
                CACHE_DIR,
            )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method != "GET":
            return await call_next(
                request
            )

        ttl_seconds = _ttl_for_path(
            request.url.path
        )

        if ttl_seconds is None:
            return await call_next(
                request
            )

        cache_file = _cache_file_for(
            request
        )
        cache_exists = (
            cache_file.exists()
        )

        if _is_fresh(
            cache_file,
            ttl_seconds,
        ):
            try:
                return _read_cached_response(
                    cache_file,
                    "HIT",
                )
            except OSError:
                logger.exception(
                    "Could not read cache file: %s",
                    cache_file,
                )

        try:
            response = await call_next(
                request
            )
        except Exception:
            if cache_exists:
                try:
                    return _read_cached_response(
                        cache_file,
                        "STALE",
                    )
                except OSError:
                    logger.exception(
                        "Could not read stale cache file: %s",
                        cache_file,
                    )
            raise

        if (
            response.status_code == 429
            or response.status_code >= 500
        ):
            if cache_exists:
                try:
                    return _read_cached_response(
                        cache_file,
                        "STALE",
                    )
                except OSError:
                    logger.exception(
                        "Could not read stale cache file: %s",
                        cache_file,
                    )

            return response

        content_type = (
            response.headers.get(
                "content-type",
                "",
            ).lower()
        )

        if (
            response.status_code != 200
            or "application/json"
            not in content_type
        ):
            return response

        body = b"".join(
            [
                chunk
                async for chunk
                in response.body_iterator
            ]
        )

        cache_state = (
            "REFRESH"
            if cache_exists
            else "MISS"
        )

        try:
            _write_atomic(
                cache_file,
                body,
            )
        except OSError:
            logger.exception(
                "Could not write cache file: %s",
                cache_file,
            )

        headers = dict(
            response.headers
        )
        headers.pop(
            "content-length",
            None,
        )
        headers[
            "X-Canarias-Cache"
        ] = cache_state

        return Response(
            content=body,
            status_code=(
                response.status_code
            ),
            headers=headers,
            media_type=None,
        )
