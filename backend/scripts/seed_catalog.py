"""Upsert the reviewed catalog snapshot (data/catalog/vehicles.json) into the database.

The application already seeds an *empty* catalog on start-up. Use this script to
refresh existing rows after the snapshot changes; it overwrites matching ids and
never deletes rows that are not in the snapshot.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


async def run(seed_dir: Path | None) -> None:
    from src.config import get_settings
    from src.infrastructure.bootstrap import create_schema
    from src.infrastructure.database import SessionLocal, engine
    from src.infrastructure.seed.catalog import upsert_catalog

    await create_schema()
    async with SessionLocal() as session:
        counts = await upsert_catalog(session, seed_dir or get_settings().seed_data_dir)
    print(f"Catalog upsert complete: inserted={counts['inserted']}, updated={counts['updated']}")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", help="Override DATABASE_URL")
    parser.add_argument("--seed-dir", type=Path, help="Directory containing vehicles.json")
    args = parser.parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    asyncio.run(run(args.seed_dir))


if __name__ == "__main__":
    main()
