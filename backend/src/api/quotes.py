import uuid

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_current_user, get_quote_service, require_staff
from src.api.schemas.common import errors
from src.api.schemas.workflow import QuoteCreate, QuoteResponse, QuoteReviewRequest
from src.application.quotes import QuoteReview, QuoteService
from src.domain.accounts import Account
from src.domain.quotes import Quote, QuoteFilter, QuoteStatus

router = APIRouter()


@router.get(
    "",
    response_model=list[QuoteResponse],
    summary="Danh sách báo giá",
    description="Customer luôn chỉ nhận báo giá của chính mình (bộ lọc bị bỏ qua); nhân viên lọc theo các tham số.",
    responses=errors(401),
)
async def list_quotes(
    user_id: uuid.UUID | None = Query(None),
    email: str | None = Query(None, max_length=255),
    phone: str | None = Query(None, max_length=20),
    quote_status: QuoteStatus | None = Query(None, alias="status"),
    current_user: Account = Depends(get_current_user),
    service: QuoteService = Depends(get_quote_service),
) -> list[Quote]:
    criteria = QuoteFilter(user_id=user_id, email=email or None, phone=phone or None, status=quote_status)
    return await service.list_quotes(current_user.actor, criteria)


@router.post(
    "",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yêu cầu báo giá",
    description="Tên xe và giá được backend lấy từ catalog; danh tính lấy từ token.",
    responses=errors(401, 404),
)
async def create_quote(
    payload: QuoteCreate,
    current_user: Account = Depends(get_current_user),
    service: QuoteService = Depends(get_quote_service),
) -> Quote:
    return await service.request_quote(current_user, payload.vehicle_id, payload.request_note)


@router.put(
    "/{quote_id}",
    response_model=QuoteResponse,
    summary="Nhân viên xử lý báo giá",
    responses=errors(401, 403, 404, 409),
)
async def review_quote(
    quote_id: uuid.UUID,
    payload: QuoteReviewRequest,
    current_user: Account = Depends(require_staff),
    service: QuoteService = Depends(get_quote_service),
) -> Quote:
    review = QuoteReview(
        status=payload.status, notes=payload.notes, discount=payload.discount, final_price=payload.final_price
    )
    return await service.review(current_user.actor, quote_id, review)
