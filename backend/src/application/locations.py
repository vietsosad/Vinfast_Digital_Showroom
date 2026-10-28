from __future__ import annotations

from collections.abc import Callable, Sequence

from src.domain.errors import PermissionDeniedError
from src.domain.identity import Actor
from src.domain.locations import Location
from src.domain.unit_of_work import UnitOfWork

ALL_PROVINCES_LABEL = "tất cả tỉnh thành"

# Kiểu hàm cung cấp danh sách địa điểm tham chiếu đã được rà soát để đồng bộ.
LocationDataset = Callable[[], Sequence[Location]]


# Áp dụng quy tắc truy vấn và đồng bộ dữ liệu điểm tư vấn/địa điểm.
class LocationService:
    def __init__(self, uow: UnitOfWork, dataset: LocationDataset):
        # UnitOfWork cung cấp repository và transaction; dataset là nguồn dữ liệu chuẩn.
        self.uow = uow
        self.dataset = dataset

    # Trả danh sách địa điểm đang hoạt động, có thể lọc theo tỉnh, từ khóa và loại nhu cầu.
    async def list_locations(
        self,
        demand_type: str | None = None,
        province: str | None = None,
        search: str | None = None,
    ) -> list[Location]:
        # Loại bỏ khoảng trắng; lựa chọn "tất cả tỉnh thành" được chuyển thành bộ lọc rỗng.
        province = (province or "").strip()
        if province.lower() == ALL_PROVINCES_LABEL:
            province = ""
        # Repository lọc trạng thái hoạt động, tỉnh và từ khóa trước khi trả kết quả.
        locations = await self.uow.locations.list_active(province or None, (search or "").strip() or None)

        # Một yêu cầu có thể chọn nhiều loại nhu cầu, ngăn cách bằng dấu phẩy.
        wanted = [item.strip() for item in (demand_type or "").split(",") if item.strip()]
        # Không áp dụng lọc loại nếu người gọi không truyền loại nhu cầu nào.
        if not wanted:
            return locations
        # Giữ địa điểm nếu ít nhất một loại được yêu cầu nằm trong các loại địa điểm hỗ trợ.
        return [location for location in locations if any(kind in location.types for kind in wanted)]

    # Thay thế/cập nhật dữ liệu địa điểm bằng bộ dữ liệu tham chiếu; chỉ admin được thực hiện.
    async def synchronize(self, actor: Actor) -> int:
        """Reload the reviewed reference dataset into the database (idempotent upsert)."""
        if not actor.is_admin:
            raise PermissionDeniedError("Chỉ quản trị viên được đồng bộ dữ liệu địa điểm")
        # Nạp danh sách từ nguồn chuẩn; upsert cho phép chạy lại mà không nhân bản bản ghi.
        total = await self.uow.locations.upsert_many(list(self.dataset()))
        # Chốt thay đổi trong transaction và trả số lượng địa điểm đã đồng bộ.
        await self.uow.commit()
        return total
