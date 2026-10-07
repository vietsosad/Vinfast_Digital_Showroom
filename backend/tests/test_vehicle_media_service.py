from uuid import uuid4

import pytest

from src.services.vehicle_media import (
    MediaDraft,
    MediaNotFoundError,
    MediaRecord,
    MediaValidationError,
    VehicleMediaService,
)


class InMemoryMediaRepository:
    def __init__(self, *, vehicle_exists: bool = True):
        self.exists = vehicle_exists
        self.records: list[MediaRecord] = []

    async def vehicle_exists(self, vehicle_type, vehicle_id):
        return self.exists

    async def list_media(self, vehicle_type, vehicle_id):
        return list(self.records)

    async def create_media(self, vehicle_type, vehicle_id, drafts):
        self.records = [
            MediaRecord(
                **draft.__dict__,
                media_id=uuid4(),
                vehicle_type=vehicle_type,
                vehicle_id=vehicle_id,
            )
            for draft in drafts
        ]
        return list(self.records)

    async def update_media(self, media_id, changes):
        return None

    async def delete_media(self, media_id):
        return False


async def test_first_media_becomes_primary_and_metadata_is_normalized():
    repository = InMemoryMediaRepository()
    service = VehicleMediaService(repository)
    vehicle_id = uuid4()

    records = await service.add_media(
        "car",
        vehicle_id,
        [
            MediaDraft(
                url="  /static/uploads/cars/vf6.webp  ",
                angle="  front  ",
                alt_text="  VF 6 mặt trước  ",
            )
        ],
    )

    assert records[0].is_primary is True
    assert records[0].url == "/static/uploads/cars/vf6.webp"
    assert records[0].angle == "front"
    assert records[0].alt_text == "VF 6 mặt trước"


async def test_media_rejects_invalid_vehicle_type_and_url():
    service = VehicleMediaService(InMemoryMediaRepository())

    with pytest.raises(MediaValidationError, match="vehicle_type"):
        await service.list_media("truck", uuid4())

    with pytest.raises(MediaValidationError, match="URL ảnh"):
        await service.add_media("car", uuid4(), [MediaDraft(url="file:///tmp/car.png")])


async def test_media_requires_existing_vehicle_and_single_primary_image():
    missing_service = VehicleMediaService(InMemoryMediaRepository(vehicle_exists=False))
    with pytest.raises(MediaNotFoundError):
        await missing_service.add_media("motorbike", uuid4(), [MediaDraft(url="https://cdn/x.webp")])

    service = VehicleMediaService(InMemoryMediaRepository())
    with pytest.raises(MediaValidationError, match="một ảnh chính"):
        await service.add_media(
            "car",
            uuid4(),
            [
                MediaDraft(url="https://cdn/one.webp", is_primary=True),
                MediaDraft(url="https://cdn/two.webp", is_primary=True),
            ],
        )
