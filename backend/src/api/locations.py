from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.domain import Account
from src.services.database import get_db
from src.services.security import require_roles
from src.services.vinfast_locations_service import (
    get_all_locations,
    sync_vinfast_locations_dataset,
)

router = APIRouter()


@router.get("", response_model=dict[str, Any])
async def list_locations(
    demand_type: str | None = Query(None, description="Lọc theo loại hình (e.g. showroom_car,charging_car)"),
    province: str | None = Query(None, description="Lọc theo Tỉnh/Thành phố"),
    search: str | None = Query(None, description="Từ khóa tìm kiếm theo tên hoặc địa chỉ"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách các Showroom, Xưởng dịch vụ và Trạm sạc VinFast / V-GREEN chính thức từ Database.
    """
    data = await get_all_locations(db, demand_type=demand_type, province=province, search=search)
    return {
        "status": "success",
        "total": len(data),
        "data": data,
    }


@router.post("/sync", response_model=dict[str, Any])
async def sync_locations(
    current_user: Account = Depends(require_roles(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Đồng bộ lại tập dữ liệu Showroom & Trạm sạc VinFast chính xác vào Database.
    """
    result = await sync_vinfast_locations_dataset(db)
    return result
