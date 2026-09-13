from __future__ import annotations

import argparse
import asyncio
import json

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source


async def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh one persisted Canarias Cerca data resource")
    parser.add_argument("section", choices=["explore", "live", "news", "calendar"])
    parser.add_argument("resource")
    parser.add_argument("--island")
    parser.add_argument("--month")
    parser.add_argument("--hours", type=int, default=48)
    args = parser.parse_args()

    source = get_data_source(args.section, args.resource)
    payload = await source.refresh(island=args.island, month=args.month, hours=args.hours, refresh_limit=200)
    count = source.count(payload)
    print(json.dumps({
        "section": args.section,
        "resource": args.resource,
        "island": args.island,
        "status": payload.get("status") if isinstance(payload, dict) else "ok",
        "updated_at": payload.get("updated_at") if isinstance(payload, dict) else None,
        "count": count,
        "refresh_error": payload.get("refresh_error") if isinstance(payload, dict) else None,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
