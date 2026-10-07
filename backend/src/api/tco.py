from fastapi import APIRouter

from src.services.tco_calculator import (
    TCOCalculationRequest,
    TCOCalculationResponse,
    calculate_tco,
)

router = APIRouter()


@router.post("/calculate", response_model=TCOCalculationResponse)
async def calculate_tco_endpoint(request: TCOCalculationRequest) -> TCOCalculationResponse:
    """Gọi Python Tool tính TCO lăn bánh & chi phí sạc/tháng."""
    return calculate_tco(request)
