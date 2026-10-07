import inspect
import uuid

import pytest

from src.api.cars import create_car, delete_car, update_car
from src.api.motorbikes import update_motorbike
from src.models.domain import CarCatalog, MotorbikeCatalog


def arguments(function, **overrides):
    values = {}
    for name, parameter in inspect.signature(function).parameters.items():
        if name in overrides:
            values[name] = overrides[name]
            continue
        default = parameter.default
        if hasattr(default, "default"):
            values[name] = default.default
        elif default is not inspect.Parameter.empty:
            values[name] = default
    return values


class ScalarResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self, model=None):
        self.model = model
        self.added = []
        self.deleted = []
        self.statements = []

    def add(self, model):
        self.added.append(model)

    async def execute(self, statement, params=None):
        self.statements.append((str(statement), params))
        return ScalarResult(self.model)

    async def commit(self):
        return None

    async def refresh(self, model):
        return None

    async def delete(self, model):
        self.deleted.append(model)


@pytest.mark.asyncio
async def test_create_car_persists_catalog_record():
    db = FakeDB()
    car = await create_car(
        **arguments(
            create_car,
            current_user=object(),
            db=db,
            model_name="VinFast Test",
            vehicle_line="Test",
            version="Plus",
            category="Personal",
            list_price=500_000_000,
        )
    )

    assert db.added == [car]
    assert car.model_name == "VinFast Test"
    assert car.list_price == 500_000_000


@pytest.mark.asyncio
async def test_update_car_changes_requested_fields_only():
    car_id = uuid.UUID("00000000-0000-0000-0000-000000000301")
    car = CarCatalog(
        car_id=car_id,
        model_name="VinFast VF 8 Plus",
        vehicle_line="VF 8",
        version="Plus",
        category="Personal",
        list_price=1_200_000_000,
        range_km=457,
        additional_specs={},
        is_active=True,
    )
    db = FakeDB(car)
    updated = await update_car(
        **arguments(
            update_car,
            car_id=car_id,
            current_user=object(),
            db=db,
            range_km=500,
        )
    )

    assert updated.range_km == 500
    assert updated.model_name == "VinFast VF 8 Plus"


@pytest.mark.asyncio
async def test_deactivate_motorbike_updates_only_catalog_table():
    motorbike_id = uuid.UUID("00000000-0000-0000-0000-000000000302")
    motorbike = MotorbikeCatalog(
        motorbike_id=motorbike_id,
        model_name="VinFast Evo",
        vehicle_line="Evo",
        version="Kèm pin",
        category="motorbike",
        list_price=25_000_000,
        additional_specs={},
        is_active=True,
    )
    db = FakeDB(motorbike)
    updated = await update_motorbike(
        **arguments(
            update_motorbike,
            motorbike_id=motorbike_id,
            current_user=object(),
            db=db,
            is_active=False,
        )
    )

    assert updated.is_active is False
    assert all("catalog_vectors" not in sql for sql, _ in db.statements)


@pytest.mark.asyncio
async def test_delete_car_removes_catalog_record():
    car_id = uuid.UUID("00000000-0000-0000-0000-000000000303")
    car = CarCatalog(
        car_id=car_id,
        model_name="VinFast Delete Test",
        vehicle_line="Test",
        version="Base",
        category="Personal",
        list_price=1,
        additional_specs={},
        is_active=True,
    )
    db = FakeDB(car)
    response = await delete_car(car_id=car_id, current_user=object(), db=db)

    assert db.deleted == [car]
    assert "Đã xóa" in response["message"]
    assert all("catalog_vectors" not in sql for sql, _ in db.statements)
