from __future__ import annotations

from dataclasses import asdict, fields
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.catalog import Car, Motorbike
from src.infrastructure.orm import CarRow, MotorbikeRow, VehicleMediaRow

EntityT = TypeVar("EntityT", Car, Motorbike)
RowT = TypeVar("RowT", CarRow, MotorbikeRow)


class _SqlAlchemyVehicleRepository(Generic[EntityT, RowT]):
    entity: type[EntityT]
    row_type: type[RowT]
    id_field: str
    media_column: str

    def __init__(self, session: AsyncSession):
        self.session = session
        self._fields = [field.name for field in fields(self.entity)]

    @property
    def _id_column(self):
        return getattr(self.row_type, self.id_field)

    def _to_entity(self, row: RowT) -> EntityT:
        return self.entity(**{name: getattr(row, name) for name in self._fields})

    def _copy_to_row(self, vehicle: EntityT, row: RowT) -> None:
        for name, value in asdict(vehicle).items():
            if name in {"created_at", "updated_at"}:
                continue
            setattr(row, name, value)

    async def list(self, category: str | None = None) -> list[EntityT]:
        statement = select(self.row_type)
        if category:
            statement = statement.where(self.row_type.category.ilike(f"%{category}%"))
        rows = await self.session.scalars(statement.order_by(self.row_type.list_price.asc(), self.row_type.model_name))
        return [self._to_entity(row) for row in rows]

    async def get(self, vehicle_id: UUID) -> EntityT | None:
        row = await self.session.get(self.row_type, vehicle_id)
        return self._to_entity(row) if row else None

    async def find_by_code_or_name(self, term: str) -> EntityT | None:
        term = term.strip()
        if not term:
            return None
        exact = await self.session.scalar(
            select(self.row_type).where(self.row_type.vehicle_line.ilike(term)).order_by(self.row_type.list_price)
        )
        if exact is not None:
            return self._to_entity(exact)
        partial = await self.session.scalar(
            select(self.row_type)
            .where(or_(self.row_type.model_name.ilike(f"%{term}%"), self.row_type.vehicle_line.ilike(f"%{term}%")))
            .order_by(self.row_type.list_price)
        )
        return self._to_entity(partial) if partial else None

    async def add(self, vehicle: EntityT) -> EntityT:
        row = self.row_type()
        self._copy_to_row(vehicle, row)
        self.session.add(row)
        await self.session.flush()
        return self._to_entity(row)

    async def save(self, vehicle: EntityT) -> EntityT:
        row = await self.session.get(self.row_type, getattr(vehicle, self.id_field))
        if row is None:
            raise LookupError("Vehicle does not exist")
        self._copy_to_row(vehicle, row)
        await self.session.flush()
        return self._to_entity(row)

    async def delete(self, vehicle_id: UUID) -> bool:
        await self.session.execute(
            delete(VehicleMediaRow).where(getattr(VehicleMediaRow, self.media_column) == vehicle_id)
        )
        result = await self.session.execute(delete(self.row_type).where(self._id_column == vehicle_id))
        return bool(result.rowcount)


class SqlAlchemyCarRepository(_SqlAlchemyVehicleRepository[Car, CarRow]):
    entity = Car
    row_type = CarRow
    id_field = "car_id"
    media_column = "car_id"


class SqlAlchemyMotorbikeRepository(_SqlAlchemyVehicleRepository[Motorbike, MotorbikeRow]):
    entity = Motorbike
    row_type = MotorbikeRow
    id_field = "motorbike_id"
    media_column = "motorbike_id"
