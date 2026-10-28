from uuid import uuid4

import pytest

from src.application.vehicle_media import VehicleMediaService
from src.domain.errors import FileTooLargeError, NotFoundError, ValidationError
from src.domain.files import UploadedFile
from src.domain.media import MediaDraft
from tests.unit.fakes import FakeUnitOfWork, InMemoryFileStorage, InMemoryMediaRepository

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def make_service(repository=None, storage=None, max_bytes=1024):
    uow = FakeUnitOfWork(media=repository or InMemoryMediaRepository())
    return VehicleMediaService(uow, storage or InMemoryFileStorage(), max_bytes), uow


async def test_first_media_becomes_primary_and_metadata_is_normalized():
    service, uow = make_service()
    records = await service.add_media(
        "car",
        uuid4(),
        [MediaDraft(url="  /static/uploads/cars/vf6.webp  ", angle="  front  ", alt_text="  VF 6 mặt trước  ")],
    )
    assert records[0].is_primary is True
    assert records[0].url == "/static/uploads/cars/vf6.webp"
    assert records[0].angle == "front"
    assert records[0].alt_text == "VF 6 mặt trước"
    assert uow.commits == 1


async def test_media_rejects_invalid_vehicle_type_and_url():
    service, _ = make_service()
    with pytest.raises(ValidationError, match="vehicle_type"):
        await service.list_media("truck", uuid4())
    with pytest.raises(ValidationError, match="URL ảnh"):
        await service.add_media("car", uuid4(), [MediaDraft(url="file:///tmp/car.png")])


async def test_media_requires_existing_vehicle_and_single_primary_image():
    missing, _ = make_service(InMemoryMediaRepository(vehicle_exists=False))
    with pytest.raises(NotFoundError):
        await missing.add_media("motorbike", uuid4(), [MediaDraft(url="https://cdn/x.webp")])

    service, _ = make_service()
    with pytest.raises(ValidationError, match="một ảnh chính"):
        await service.add_media(
            "car",
            uuid4(),
            [MediaDraft(url="https://cdn/one.webp", is_primary=True), MediaDraft(url="https://cdn/two.webp", is_primary=True)],
        )


async def test_upload_validates_every_file_before_storing_any():
    storage = InMemoryFileStorage()
    service, _ = make_service(storage=storage)
    uploads = [UploadedFile("ok.png", "image/png", PNG), UploadedFile("bad.png", "image/png", b"GIF89a....")]
    with pytest.raises(ValidationError):
        await service.upload_media("car", uuid4(), uploads)
    assert storage.files == {}


async def test_upload_enforces_size_limit():
    service, _ = make_service(max_bytes=8)
    with pytest.raises(FileTooLargeError):
        await service.upload_media("car", uuid4(), [UploadedFile("big.png", "image/png", PNG)])


async def test_stored_files_are_removed_when_the_database_write_fails():
    storage = InMemoryFileStorage()
    service, _ = make_service(InMemoryMediaRepository(fail_on_create=True), storage)
    with pytest.raises(RuntimeError):
        await service.upload_media("car", uuid4(), [UploadedFile("a.png", "image/png", PNG)] * 2)
    assert storage.files == {}


async def test_successful_upload_records_checksum_and_url():
    storage = InMemoryFileStorage()
    service, uow = make_service(storage=storage)
    vehicle_id = uuid4()
    [record] = await service.upload_media("motorbike", vehicle_id, [UploadedFile("Evo 200.PNG", "image/png", PNG)])
    assert record.url in storage.files
    assert record.url.startswith(f"/static/uploads/motorbikes/gallery/{vehicle_id}/Evo-200-")
    assert len(record.checksum) == 64
    assert uow.commits == 1
