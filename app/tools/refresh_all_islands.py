from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
from app.services.events import current_month
from app.utils.islands import VALID_ISLANDS


@dataclass(frozen=True)
class ResourceSpec:
    label: str
    section: str
    resource: str
    per_island: bool = True
    require_nonempty: bool = False


RESOURCE_SPECS: tuple[ResourceSpec, ...] = (
    ResourceSpec("Rutas", "explore", "routes", require_nonempty=True),
    ResourceSpec("Fauna", "explore", "fauna", require_nonempty=True),
    ResourceSpec("Flora", "explore", "flora", require_nonempty=True),
    ResourceSpec("Weather", "live", "weather", require_nonempty=True),
    ResourceSpec("Air", "live", "air-quality", require_nonempty=True),
    ResourceSpec("Marine", "live", "marine", require_nonempty=True),
    ResourceSpec("Tides", "live", "tides", require_nonempty=True),
    ResourceSpec("Seismic", "live", "seismic"),
    ResourceSpec("Alerts", "live", "alerts"),
    ResourceSpec("Calendar", "calendar", "events", require_nonempty=True),
    ResourceSpec("Volcanic", "live", "volcanic", per_island=False),
    ResourceSpec("News", "news", "latest", per_island=False),
)


def _count_payload(payload: Any) -> int | None:
    if isinstance(payload, list):
        return len(payload)
    if not isinstance(payload, dict):
        return None
    for key in ("features", "items", "data", "points", "reports"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    return None


def _is_ok(payload: Any, *, require_nonempty: bool) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "invalid payload"

    status = str(payload.get("status") or "").lower()
    available = payload.get("available")
    count = _count_payload(payload)

    if status in {"error", "not_initialized"}:
        return False, status
    if status == "stale":
        return False, "stale"
    if available is False:
        return False, "not available"
    if require_nonempty and (count is None or count <= 0):
        return False, "empty"

    return True, "ok"


def _params_for(spec: ResourceSpec, island: str | None, month: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if island is not None:
        params["island"] = island
    if spec.resource == "tides":
        params["hours"] = 48
    if spec.section == "calendar":
        params["month"] = month
        params["refresh_limit"] = 200
    if spec.section == "news":
        params["refresh_limit"] = 200
    return params


async def _run_one(
    spec: ResourceSpec,
    *,
    island: str | None,
    month: str,
    audit_only: bool,
) -> tuple[bool, int | None, str]:
    source = get_data_source(spec.section, spec.resource)
    params = _params_for(spec, island, month)
    payload = source.read(**params) if audit_only else await source.refresh(**params)
    ok, reason = _is_ok(payload, require_nonempty=spec.require_nonempty)
    return ok, _count_payload(payload), reason


async def run(*, audit_only: bool = False, month: str | None = None) -> int:
    month = month or current_month()
    mode = "AUDIT" if audit_only else "REFRESH"
    print(f"CANARIAS CERCA — ALL ISLANDS {mode}")
    print(f"month={month} generated={datetime.now().isoformat(timespec='seconds')}")
    print()

    failures = 0

    for spec in RESOURCE_SPECS:
        print(spec.label.upper())
        targets: tuple[str | None, ...]
        if spec.per_island:
            targets = tuple(VALID_ISLANDS)
        else:
            targets = (None,)

        for island in targets:
            label = island or "canarias"
            try:
                ok, count, reason = await _run_one(
                    spec,
                    island=island,
                    month=month,
                    audit_only=audit_only,
                )
            except Exception as exc:  # defensive CLI boundary
                ok = False
                count = None
                reason = str(exc)

            if not ok:
                failures += 1

            count_text = "-" if count is None else str(count)
            state = "OK" if ok else "FAIL"
            print(f"  {label:<15} {state:<4} count={count_text:<4} {reason}")
        print()

    if failures:
        print(f"RESULT: FAILED ({failures} checks failed)")
        return 1

    print("RESULT: ALL ISLAND DATA READY")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh or audit stored Canarias Cerca data for all islands.",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Do not call external sources; only inspect currently stored snapshots.",
    )
    parser.add_argument(
        "--month",
        default=None,
        help="Calendar month in YYYY-MM format. Defaults to the current month.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    raise SystemExit(asyncio.run(run(audit_only=args.audit_only, month=args.month)))


if __name__ == "__main__":
    main()
