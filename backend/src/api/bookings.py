import uuid

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_booking_service, get_current_user, require_staff
from src.api.schemas.common import errors
from src.api.schemas.workflow import BookingCreate, BookingResponse, BookingStatusUpdate
from src.application.bookings import BookingRequest, BookingService
from src.domain.accounts import Account
from src.domain.bookings import Booking, BookingFilter, BookingStatus

router = APIRouter()


@router.get(
    "",
    response_model=list[BookingResponse],
    summary="Danh sách lịch lái thử",
    description="Customer chỉ thấy lịch thuộc tài khoản của mình (theo user_id trong token).",
    responses=errors(401),
)
async def list_bookings(
    phone: str | None = Query(None, max_length=20),
    booking_status: BookingStatus | None = Query(None, alias="status"),
    current_user: Account = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
) -> list[Booking]:
    return await service.list_bookings(current_user.actor, BookingFilter(phone=phone or None, status=booking_status))


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đặt lịch lái thử",
    responses=errors(401, 404),
)
async def create_booking(
    payload: BookingCreate,
    current_user: Account = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
) -> Booking:
    request = BookingRequest(
        vehicle_id=payload.vehicle_id,
        preferred_date=payload.preferred_date,
        preferred_time=payload.preferred_time,
        notes=payload.notes,
    )
    return await service.book_test_drive(current_user, request)


@router.put(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Nhân viên cập nhật trạng thái lịch",
    responses=errors(401, 403, 404, 409),
)
async def update_booking_status(
    booking_id: uuid.UUID,
    payload: BookingStatusUpdate,
    current_user: Account = Depends(require_staff),
    service: BookingService = Depends(get_booking_service),
) -> Booking:
    return await service.change_status(current_user.actor, booking_id, payload.status, payload.notes)
