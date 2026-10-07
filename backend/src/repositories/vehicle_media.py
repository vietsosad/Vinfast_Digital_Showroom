from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.domain import CarCatalog, MotorbikeCatalog, VehicleMedia
from src.services.vehicle_media import MediaDraft, MediaRecord


class SqlAlchemyVehicleMediaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def vehicle_exists(self, vehicle_type: str, vehicle_id: UUID) -> bool:
        model = CarCatalog if vehicle_type == "car" else MotorbikeCatalog
        return await self.session.get(model, vehicle_id) is not None

    async def list_media(self, vehicle_type: str, vehicle_id: UUID) -> list[MediaRecord]:
        column = VehicleMedia.car_id if vehicle_type == "car" else VehicleMedia.motorbike_id
        rows = (
            await self.session.scalars(
                select(VehicleMedia)
                .where(column == vehicle_id)
                .order_by(VehicleMedia.is_primary.desc(), VehicleMedia.sort_order, VehicleMedia.created_at)
            )
        ).all()
        return [self._record(row) for row in rows]

    async def create_media(
        self, vehicle_type: str, vehicle_id: UUID, drafts: list[MediaDraft]
    ) -> list[MediaRecord]:
        if any(draft.is_primary for draft in drafts):
            column = VehicleMedia.car_id if vehicle_type == "car" else VehicleMedia.motorbike_id
            await self.session.execute(
                update(VehicleMedia).where(column == vehicle_id).values(is_primary=False)
            )

        rows = []
        for draft in drafts:
            values = draft.__dict__.copy()
            values["car_id" if vehicle_type == "car" else "motorbike_id"] = vehicle_id
            row = VehicleMedia(**values)
            self.session.add(row)
            rows.append(row)
        await self.session.commit()
        for row in rows:
            await self.session.refresh(row)
        return [self._record(row) for row in rows]

    async def update_media(self, media_id: UUID, changes: dict) -> MediaRecord | None:
        row = await self.session.get(VehicleMedia, media_id)
        if row is None:
            return None
        if changes.get("is_primary"):
            column = VehicleMedia.car_id if row.car_id else VehicleMedia.motorbike_id
            vehicle_id = row.car_id or row.motorbike_id
            await self.session.execute(
                update(VehicleMedia).where(column == vehicle_id).values(is_primary=False)
            )
        for key, value in changes.items():
            setattr(row, key, value)
        await self.session.commit()
        await self.session.refresh(row)
        return self._record(row)

    async def delete_media(self, media_id: UUID) -> bool:
        result = await self.session.execute(delete(VehicleMedia).where(VehicleMedia.media_id == media_id))
        await self.session.commit()
        return bool(result.rowcount)

    @staticmethod
    def _record(row: VehicleMedia) -> MediaRecord:
        vehicle_type = "car" if row.car_id else "motorbike"
        return MediaRecord(
            media_id=row.media_id,
            vehicle_type=vehicle_type,
            vehicle_id=row.car_id or row.motorbike_id,
            url=row.url,
            media_type=row.media_type,
            angle=row.angle,
            color_code=row.color_code,
            alt_text=row.alt_text,
            sort_order=row.sort_order,
            is_primary=row.is_primary,
            source_url=row.source_url,
            source_label=row.source_label,
            checksum=row.checksum,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
