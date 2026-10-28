from __future__ import annotations

import hashlib
from uuid import UUID

from src.application.uploads import DEFAULT_MAX_IMAGE_BYTES, storage_filename, validate_image
from src.domain.errors import NotFoundError, ValidationError
from src.domain.files import FileStorage, UploadedFile
from src.domain.media import MEDIA_TYPES, VEHICLE_TYPES, MediaDraft, MediaRecord
from src.domain.unit_of_work import UnitOfWork

# Giới hạn số liên kết ảnh và số tệp tải lên trong một request.
# Tải tệp có giới hạn thấp hơn vì còn phải đọc và ghi nội dung ảnh.
MAX_LINKS_PER_REQUEST = 100
MAX_UPLOADS_PER_REQUEST = 20

# Chỉ những trường này được phép sửa qua update_media.
# Các trường định danh như media_id, vehicle_id và checksum không nằm trong danh sách.
EDITABLE_FIELDS = {
    "media_type",
    "angle",
    "color_code",
    "alt_text",
    "sort_order",
    "is_primary",
    "source_url",
    "source_label",
}


class VehicleMediaService:
    """Điều phối các thao tác nghiệp vụ với ảnh xe."""

    def __init__(
        self,
        uow: UnitOfWork,
        storage: FileStorage | None = None,
        max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
    ):
        # UnitOfWork gom repository và điều khiển transaction cơ sở dữ liệu.
        # Storage được tiêm từ bên ngoài để use case không phụ thuộc cách lưu tệp cụ thể.
        self.uow = uow
        self.storage = storage
        self.max_image_bytes = max_image_bytes

    @property
    def repository(self):
        # Rút gọn truy cập repository ảnh mà UnitOfWork cung cấp.
        return self.uow.media

    async def list_media(self, vehicle_type: str, vehicle_id: UUID) -> list[MediaRecord]:
        # Chỉ cho phép loại xe đã biết và không trả danh sách cho xe không tồn tại.
        self._validate_vehicle_type(vehicle_type)
        if not await self.repository.vehicle_exists(vehicle_type, vehicle_id):
            raise NotFoundError("Không tìm thấy mẫu xe")
        return await self.repository.list_media(vehicle_type, vehicle_id)

    async def add_media(self, vehicle_type: str, vehicle_id: UUID, drafts: list[MediaDraft]) -> list[MediaRecord]:
        # Kiểm tra đầu vào trước khi gọi repository để tránh ghi dữ liệu sai.
        self._validate_vehicle_type(vehicle_type)
        if not drafts or len(drafts) > MAX_LINKS_PER_REQUEST:
            raise ValidationError("Mỗi lần nhập từ 1 đến 100 ảnh")
        if sum(1 for draft in drafts if draft.is_primary) > 1:
            raise ValidationError("Mỗi xe chỉ được có một ảnh chính")
        if not await self.repository.vehicle_exists(vehicle_type, vehicle_id):
            raise NotFoundError("Không tìm thấy mẫu xe")

        existing = await self.repository.list_media(vehicle_type, vehicle_id)
        # Chuẩn hóa khoảng trắng/độ dài và kiểm tra URL, loại ảnh, thứ tự hiển thị.
        normalized = [self._normalize(draft) for draft in drafts]
        # Nếu xe chưa có ảnh, ảnh đầu tiên mặc định là ảnh chính.
        if not existing and not any(draft.is_primary for draft in normalized):
            first = normalized[0]
            normalized[0] = MediaDraft(**{**first.__dict__, "is_primary": True})
        records = await self.repository.create_media(vehicle_type, vehicle_id, normalized)
        # Repository thực hiện thao tác dữ liệu; UnitOfWork chốt transaction.
        await self.uow.commit()
        return records

    async def upload_media(
        self,
        vehicle_type: str,
        vehicle_id: UUID,
        uploads: list[UploadedFile],
        media_type: str = "exterior",
        angle: str | None = None,
        color_code: str | None = None,
    ) -> list[MediaRecord]:
        """Kiểm tra ảnh, lưu tệp và xóa các tệp vừa lưu nếu ghi dữ liệu thất bại."""
        # Không có adapter lưu tệp thì không thể thực hiện luồng upload.
        if self.storage is None:
            raise RuntimeError("File storage is not configured")
        self._validate_vehicle_type(vehicle_type)
        if not 1 <= len(uploads) <= MAX_UPLOADS_PER_REQUEST:
            raise ValidationError(f"Mỗi lần tải từ 1 đến {MAX_UPLOADS_PER_REQUEST} ảnh")
        if not await self.repository.vehicle_exists(vehicle_type, vehicle_id):
            raise NotFoundError("Không tìm thấy mẫu xe")
        # Xác thực toàn bộ ảnh trước khi lưu bất kỳ tệp nào.
        extensions = [validate_image(upload, self.max_image_bytes) for upload in uploads]

        # Tách thư mục ảnh theo loại xe và mã xe để dễ phục vụ qua /static/uploads.
        folder = f"uploads/{'cars' if vehicle_type == 'car' else 'motorbikes'}/gallery/{vehicle_id}"
        saved_urls: list[str] = []
        try:
            drafts = []
            for index, (upload, extension) in enumerate(zip(uploads, extensions)):
                # Tên an toàn được tạo từ tên gốc đã làm sạch, đuôi lấy từ nội dung đã xác thực.
                url = self.storage.save(folder, storage_filename(upload.filename, extension), upload.content)
                saved_urls.append(url)
                drafts.append(
                    MediaDraft(
                        url=url,
                        media_type=media_type,
                        angle=angle,
                        color_code=color_code,
                        sort_order=index,
                        checksum=hashlib.sha256(upload.content).hexdigest(),
                    )
                )
            # add_media sẽ kiểm tra quy tắc nghiệp vụ và ghi metadata ảnh vào database.
            return await self.add_media(vehicle_type, vehicle_id, drafts)
        except BaseException:
            # Bù trừ các tệp đã ghi nếu bước tạo metadata/database bị lỗi.
            for url in saved_urls:
                self.storage.delete(url)
            raise

    async def update_media(self, media_id: UUID, changes: dict) -> MediaRecord:
        # Bỏ mọi khóa ngoài allowlist để không cho request sửa trường hệ thống.
        clean = {key: value for key, value in changes.items() if key in EDITABLE_FIELDS}
        if "media_type" in clean and clean["media_type"] not in MEDIA_TYPES:
            raise ValidationError("Loại media không hợp lệ")
        record = await self.repository.update_media(media_id, clean)
        if record is None:
            raise NotFoundError("Không tìm thấy ảnh")
        await self.uow.commit()
        return record

    async def delete_media(self, media_id: UUID) -> None:
        # Repository trả False nếu không tìm thấy ảnh; trường hợp đó được báo thành 404.
        if not await self.repository.delete_media(media_id):
            raise NotFoundError("Không tìm thấy ảnh")
        await self.uow.commit()

    @staticmethod
    def _validate_vehicle_type(vehicle_type: str) -> None:
        # Dùng chung cho cả ô tô và xe máy; ID xe được truyền riêng.
        if vehicle_type not in VEHICLE_TYPES:
            raise ValidationError("vehicle_type phải là car hoặc motorbike")

    @staticmethod
    def _normalize(draft: MediaDraft) -> MediaDraft:
        # Chuẩn hóa URL và siêu dữ liệu trước khi lưu để dữ liệu nhất quán.
        url = draft.url.strip()
        if not (url.startswith("/static/uploads/") or url.startswith("https://") or url.startswith("http://")):
            raise ValidationError("URL ảnh phải thuộc /static/uploads hoặc dùng HTTP(S)")
        if draft.media_type not in MEDIA_TYPES:
            raise ValidationError("Loại media không hợp lệ")
        if not -10_000 <= draft.sort_order <= 10_000:
            raise ValidationError("sort_order nằm ngoài giới hạn")
        return MediaDraft(
            url=url,
            media_type=draft.media_type,
            angle=(draft.angle or "").strip() or None,
            color_code=(draft.color_code or "").strip() or None,
            alt_text=(draft.alt_text or "").strip()[:255] or None,
            sort_order=draft.sort_order,
            is_primary=draft.is_primary,
            source_url=(draft.source_url or "").strip() or None,
            source_label=(draft.source_label or "").strip()[:120] or None,
            checksum=draft.checksum,
        )
