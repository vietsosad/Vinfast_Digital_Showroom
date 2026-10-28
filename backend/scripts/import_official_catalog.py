"""Upsert verified catalog extensions from a reviewable CSV file."""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
DEFAULT_CSV = REPOSITORY_ROOT / "data" / "catalog" / "official_catalog_extensions.csv"
sys.path.insert(0, str(BACKEND_ROOT))


def optional_number(value: str, cast):
    return cast(value) if value.strip() else None




async def import_catalog(csv_path: Path) -> None:
    from sqlalchemy import select

    from src.infrastructure.bootstrap import create_schema
    from src.infrastructure.database import SessionLocal, engine
    from src.infrastructure.orm import CarRow as CarCatalog
    from src.infrastructure.orm import MotorbikeRow as MotorbikeCatalog

    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8-sig").splitlines()))
    required = {"vehicle_type", "model_name", "vehicle_line", "category", "list_price", "source_url"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"CSV thiếu cột bắt buộc: {sorted(required)}")

    await create_schema()

    inserted = updated = 0
    async with SessionLocal() as session:
        for line_number, row in enumerate(rows, start=2):
            vehicle_type = row["vehicle_type"].strip().lower()
            if vehicle_type not in {"car", "motorbike"}:
                raise ValueError(f"Dòng {line_number}: vehicle_type không hợp lệ")
            if not row["model_name"].strip() or int(row["list_price"] or 0) < 0:
                raise ValueError(f"Dòng {line_number}: tên hoặc giá không hợp lệ")

            model = CarCatalog if vehicle_type == "car" else MotorbikeCatalog
            result = await session.execute(
                select(model).where(
                    model.model_name == row["model_name"].strip(),
                    model.version == (row["version"].strip() or None),
                )
            )
            record = result.scalars().first()
            common = {
                "model_name": row["model_name"].strip(),
                "vehicle_line": row["vehicle_line"].strip(),
                "version": row["version"].strip() or None,
                "category": row["category"].strip(),
                "list_price": int(row["list_price"] or 0),
                "image_url": row["image_url"].strip() or None,
                "is_active": row["is_active"].strip().lower() == "true",
                "additional_specs": {
                    "provenance": {
                        "source_url": row["source_url"].strip(),
                        "source_checked_at": row["source_checked_at"].strip(),
                        "status": "verified-official",
                    },
                    "lifecycle": row["lifecycle"].strip(),
                },
            }
            if vehicle_type == "car":
                common.update(
                    seat_count=optional_number(row["seat_count"], int),
                    usable_battery_capacity=optional_number(row["battery_capacity_kwh"], float),
                )
            else:
                common.update(
                    battery_type=row["battery_type"].strip() or None,
                    battery_capacity_kwh=optional_number(row["battery_capacity_kwh"], float),
                    colors=[],
                )

            if record is None:
                key = f"{vehicle_type}:{common['model_name']}:{common['version'] or ''}"
                primary_key = "car_id" if vehicle_type == "car" else "motorbike_id"
                common[primary_key] = uuid.uuid5(uuid.NAMESPACE_URL, f"vinfast-catalog:{key}")
                session.add(model(**common))
                inserted += 1
            else:
                for field, value in common.items():
                    setattr(record, field, value)
                updated += 1
        await session.commit()

    print(f"Official catalog import complete: inserted={inserted}, updated={updated}, total={len(rows)}")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--database-url")
    args = parser.parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    asyncio.run(import_catalog(args.csv))


if __name__ == "__main__":
    main()
