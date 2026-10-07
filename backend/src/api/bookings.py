import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.domain import Account, TestDriveBooking, User
from src.models.schemas import BookingCreate, BookingResponse, BookingUpdateStatus
from src.services.customer_profile_service import sync_from_test_drive_booking
from src.services.database import get_db
from src.services.security import get_current_user, require_roles

router = APIRouter()


async def list_bookings(
    db: AsyncSession,
    phone: str | None = None,
    email: str | None = None,
    booking_status: str | None = None,
) -> list[TestDriveBooking]:
    stmt = select(TestDriveBooking).order_by(TestDriveBooking.created_at.desc())
    if phone and phone.strip():
        stmt = stmt.where(TestDriveBooking.customer_phone == phone.strip())
    if email and email.strip():
        stmt = stmt.where(TestDriveBooking.notes.ilike(f"%{email.strip()}%"))
    if booking_status and booking_status.strip():
        stmt = stmt.where(TestDriveBooking.status == booking_status.strip())
    result = await db.scalars(stmt)
    return list(result.all())


async def create_booking(db: AsyncSession, payload: BookingCreate) -> TestDriveBooking:
    booking = TestDriveBooking(**payload.model_dump())
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    # Tự động tạo / cập nhật hồ sơ khách hàng 360°
    await sync_from_test_drive_booking(db, booking)

    return booking


@router.get("", response_model=list[BookingResponse])
async def get_bookings(
    phone: str | None = None,
    email: str | None = None,
    status: str | None = None,
    current_user: Account = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "customer":
        phone = current_user.phone
        email = None
        status = None
    return await list_bookings(db, phone=phone, email=email, booking_status=status)


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def post_booking(
    payload: BookingCreate,
    current_user: Account = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    owned_payload = payload.model_copy(update={
        "customer_name": current_user.full_name,
        "customer_phone": current_user.phone,
    })
    return await create_booking(db, owned_payload)


@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking_status(
    booking_id: uuid.UUID,
    payload: BookingUpdateStatus,
    current_user: User = Depends(require_roles(["admin", "consultant"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TestDriveBooking).where(TestDriveBooking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch hẹn lái thử này!")

    booking.status = payload.status
    if payload.notes is not None:
        booking.notes = payload.notes

    await db.commit()
    await db.refresh(booking)
    return booking
