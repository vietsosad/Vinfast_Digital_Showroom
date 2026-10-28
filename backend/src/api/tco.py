from fastapi import APIRouter

from src.services.tco_calculator import (
    TCOCalculationRequest,
    TCOCalculationResponse,
    calculate_tco,
)

# Nhóm các endpoint API liên quan đến tính toán tổng chi phí sở hữu xe.
router = APIRouter()


# Nhận tham số tính TCO, gọi bộ tính toán và trả kết quả theo response schema.
@router.post("/calculate", response_model=TCOCalculationResponse)
async def calculate_tco_endpoint(request: TCOCalculationRequest) -> TCOCalculationResponse:
    """Gọi Python Tool tính TCO lăn bánh & chi phí sạc/tháng."""
    return calculate_tco(request)
