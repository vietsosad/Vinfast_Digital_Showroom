from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.catalog_specs import is_ebus
from src.infrastructure.orm import CarRow, MotorbikeRow

logger = logging.getLogger(__name__)
SNAPSHOT_FILENAME = "vehicles.json"


def load_catalog_snapshot(seed_dir: Path) -> dict[str, list[dict[str, Any]]]:
    path = seed_dir / SNAPSHOT_FILENAME
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("cars"), list) or not isinstance(payload.get("motorbikes"), list):
        raise ValueError(f"{path} must contain 'cars' and 'motorbikes' arrays")
    return payload


def car_row(values: dict[str, Any]) -> CarRow:
    data = {**values, "car_id": UUID(values["car_id"])}
    if is_ebus(data.get("model_name"), data.get("vehicle_line")):
        data["colors"] = None
    return CarRow(**data)


def motorbike_row(values: dict[str, Any]) -> MotorbikeRow:
    data = {**values, "motorbike_id": UUID(values["motorbike_id"])}
    data["colors"] = data.get("colors") or []
    return MotorbikeRow(**data)


async def seed_catalog_if_empty(session: AsyncSession, seed_dir: Path) -> dict[str, int]:
    """Load the reviewed snapshot into empty catalog tables; never overwrite edits."""
    path = seed_dir / SNAPSHOT_FILENAME
    if not path.is_file():
        logger.warning("Catalog seed file %s not found; catalog stays as is", path)
        return {"cars": 0, "motorbikes": 0}

    snapshot = load_catalog_snapshot(seed_dir)
    inserted = {"cars": 0, "motorbikes": 0}
    if not await session.scalar(select(func.count()).select_from(CarRow)):
        session.add_all(car_row(values) for values in snapshot["cars"])
        inserted["cars"] = len(snapshot["cars"])
    if not await session.scalar(select(func.count()).select_from(MotorbikeRow)):
        session.add_all(motorbike_row(values) for values in snapshot["motorbikes"])
        inserted["motorbikes"] = len(snapshot["motorbikes"])
    await session.commit()
    return inserted


async def upsert_catalog(session: AsyncSession, seed_dir: Path) -> dict[str, int]:
    """Overwrite catalog rows that exist in the snapshot (used by scripts/seed_catalog.py)."""
    snapshot = load_catalog_snapshot(seed_dir)
    counts = {"inserted": 0, "updated": 0}
    for rows, factory, model in (
        (snapshot["cars"], car_row, CarRow),
        (snapshot["motorbikes"], motorbike_row, MotorbikeRow),
    ):
        for values in rows:
            row = factory(values)
            key = row.car_id if model is CarRow else row.motorbike_id
            if await session.get(model, key) is None:
                counts["inserted"] += 1
            else:
                counts["updated"] += 1
            await session.merge(row)
    await session.commit()
    return counts
