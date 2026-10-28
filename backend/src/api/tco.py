from fastapi import APIRouter

from src.api.schemas.tco import TCOCalculationRequest, TCOCalculationResponse
from src.application import tco

router = APIRouter()


@router.post("/calculate", response_model=TCOCalculationResponse, summary="Ước tính chi phí lăn bánh và vận hành")
async def calculate_tco(payload: TCOCalculationRequest) -> TCOCalculationResponse:
    result = tco.calculate_tco(tco.TCOCalculationRequest(**payload.model_dump()))
    return TCOCalculationResponse.model_validate(result)
