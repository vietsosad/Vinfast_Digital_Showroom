from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.media import MediaDraft, MediaRecord
from src.infrastructure.orm import CarRow, MotorbikeRow, VehicleMediaRow


class SqlAlchemyVehicleMediaRepository:
    """Lớp repository nối hợp đồng media của domain với SQLAlchemy.

    Đây là adapter của nhánh kiến trúc mới (src.domain và src.infrastructure),
    khác với repository cũ trong src.repositories.vehicle_media. Các thay đổi
    được flush vào transaction hiện tại; UnitOfWork mới là nơi commit/rollback.
    """

    def __init__(self, session: AsyncSession):
        # Dùng chung AsyncSession với các repository khác trong UnitOfWork,
        # để các thao tác có thể nằm trong cùng một transaction.
        self.session = session

    async def vehicle_exists(self, vehicle_type: str, vehicle_id: UUID) -> bool:
        # Chọn bảng catalog theo loại xe. Tầng application/domain cần kiểm tra
        # vehicle_type trước khi gọi; nếu không phải "car", nhánh này chọn xe máy.
        model = CarRow if vehicle_type == "car" else MotorbikeRow
        return await self.session.get(model, vehicle_id) is not None

    async def list_media(self, vehicle_type: str, vehicle_id: UUID) -> list[MediaRecord]:
        # Mỗi ảnh liên kết với một trong hai cột khóa ngoại; chỉ truy vấn cột
        # tương ứng với loại xe và sắp xếp ảnh chính lên trước.
        column = VehicleMediaRow.car_id if vehicle_type == "car" else VehicleMediaRow.motorbike_id
        rows = await self.session.scalars(
            select(VehicleMediaRow)
            .where(column == vehicle_id)
            .order_by(VehicleMediaRow.is_primary.desc(), VehicleMediaRow.sort_order, VehicleMediaRow.created_at)
        )
        # Không để lớp ORM thoát ra khỏi infrastructure; trả về record của domain.
        return [self._record(row) for row in rows.all()]

    async def create_media(self, vehicle_type: str, vehicle_id: UUID, drafts: list[MediaDraft]) -> list[MediaRecord]:
        # Nếu batch có ảnh chính, hạ các ảnh hiện tại của cùng xe xuống trước.
        # Service nghiệp vụ cần đảm bảo batch không có hơn một ảnh chính.
        if any(draft.is_primary for draft in drafts):
            column = VehicleMediaRow.car_id if vehicle_type == "car" else VehicleMediaRow.motorbike_id
            await self.session.execute(update(VehicleMediaRow).where(column == vehicle_id).values(is_primary=False))

        rows = []
        for draft in drafts:
            # Chuyển dữ liệu draft thành các cột của bảng, đồng thời gắn khóa
            # ngoại vào đúng cột car_id hoặc motorbike_id.
            values = draft.__dict__.copy()
            values["car_id" if vehicle_type == "car" else "motorbike_id"] = vehicle_id
            row = VehicleMediaRow(**values)
            self.session.add(row)
            rows.append(row)
        # Flush gửi các thay đổi xuống database để tạo các giá trị mặc định
        # (ví dụ media_id), nhưng vẫn chưa commit transaction.
        await self.session.flush()
        return [self._record(row) for row in rows]

    async def update_media(self, media_id: UUID, changes: dict) -> MediaRecord | None:
        # Tìm ảnh theo khóa chính; None cho service biết để trả lời không tìm thấy.
        row = await self.session.get(VehicleMediaRow, media_id)
        if row is None:
            return None
        # Khi đặt ảnh này làm ảnh chính, bỏ cờ ảnh chính của các ảnh cùng xe.
        # Danh sách trường được phép sửa cần được giới hạn ở tầng service.
        if changes.get("is_primary"):
            column = VehicleMediaRow.car_id if row.car_id else VehicleMediaRow.motorbike_id
            vehicle_id = row.car_id or row.motorbike_id
            await self.session.execute(update(VehicleMediaRow).where(column == vehicle_id).values(is_primary=False))
        for key, value in changes.items():
            setattr(row, key, value)
        # Flush rồi refresh để đồng bộ lại trạng thái của dòng từ database
        # trước khi chuyển dòng ORM thành MediaRecord trả về.
        await self.session.flush()
        await self.session.refresh(row)
        return self._record(row)

    async def delete_media(self, media_id: UUID) -> bool:
        # Xóa bằng câu lệnh SQL trực tiếp; rowcount cho biết có bản ghi nào bị xóa.
        # Repository không commit, việc đó thuộc UnitOfWork.
        result = await self.session.execute(delete(VehicleMediaRow).where(VehicleMediaRow.media_id == media_id))
        return bool(result.rowcount)

    @staticmethod
    def _record(row: VehicleMediaRow) -> MediaRecord:
        # Ảnh thuộc về ô tô nếu car_id có giá trị, ngược lại là xe máy.
        # Ràng buộc database trong VehicleMediaRow đảm bảo chỉ một cột ID có giá trị.
        return MediaRecord(
            media_id=row.media_id,
            vehicle_type="car" if row.car_id else "motorbike",
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
