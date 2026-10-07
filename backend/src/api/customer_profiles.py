"""REST endpoints for the staff-managed customer CRM."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.domain import CustomerProfile, User
from src.models.schemas import CustomerProfileResponse, CustomerProfileUpdate
from src.services.customer_profile_service import (
    get_customer_profile_by_id,
    get_customer_profiles_list,
)
from src.services.database import get_db
from src.services.security import get_current_user, require_roles

router = APIRouter()


@router.get("", response_model=list[CustomerProfileResponse])
async def list_profiles(
    lead_score: str | None = Query(None, description="HOT, WARM or COLD"),
    lead_status: str | None = Query(None, description="Current sales status"),
    search: str | None = Query(None, description="Name, phone or email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _: User = Depends(require_roles(["admin", "consultant"])),
    db: AsyncSession = Depends(get_db),
):
    """List customer profiles. Staff and administrators only."""
    return await get_customer_profiles_list(
        db, lead_score, lead_status, search, skip, limit
    )


@router.get("/me", response_model=CustomerProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated customer's own profile."""
    result = await db.execute(
        select(CustomerProfile)
        .options(selectinload(CustomerProfile.account))
        .where(CustomerProfile.user_id == current_user.user_id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy hồ sơ khách hàng.")
    return profile


@router.get("/{profile_id}", response_model=CustomerProfileResponse)
async def get_profile_detail(
    profile_id: uuid.UUID,
    _: User = Depends(require_roles(["admin", "consultant"])),
    db: AsyncSession = Depends(get_db),
):
    """Return one customer profile. Staff and administrators only."""
    profile = await get_customer_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy hồ sơ khách hàng.")
    return profile


@router.put("/{profile_id}", response_model=CustomerProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    payload: CustomerProfileUpdate,
    _: User = Depends(require_roles(["admin", "consultant"])),
    db: AsyncSession = Depends(get_db),
):
    """Update lead status, interested models or a human-written note."""
    profile = await get_customer_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy hồ sơ khách hàng.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile
