"""Database operations for the lightweight customer CRM.

This module only maintains facts produced by account registration and test-drive
bookings. Human staff can add a note from the CRM screen; no generated profile
or conversation analysis is performed.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.domain import Account, CustomerProfile, TestDriveBooking

logger = logging.getLogger(__name__)


async def sync_from_account_register(
    db: AsyncSession,
    account: Account,
) -> CustomerProfile:
    """Create the customer's CRM profile once after account registration."""
    result = await db.execute(
        select(CustomerProfile).where(CustomerProfile.user_id == account.user_id)
    )
    existing = result.scalars().first()
    if existing:
        return existing

    profile = CustomerProfile(
        user_id=account.user_id,
        lead_score="WARM",
        lead_status="NEW",
        all_interested_models=[],
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def sync_from_test_drive_booking(
    db: AsyncSession,
    booking: TestDriveBooking,
    user_id: uuid.UUID | None = None,
) -> CustomerProfile | None:
    """Update CRM counters when an authenticated customer books a test drive."""
    target_user_id = user_id
    if not target_user_id and booking.customer_phone:
        result = await db.execute(
            select(Account).where(Account.phone == booking.customer_phone.strip())
        )
        account = result.scalars().first()
        target_user_id = account.user_id if account else None

    if not target_user_id:
        logger.info("Guest booking stored without a CRM profile")
        return None

    result = await db.execute(
        select(CustomerProfile).where(CustomerProfile.user_id == target_user_id)
    )
    profile = result.scalars().first()
    vehicle_name = (booking.vehicle_name or "").strip()

    if not profile:
        profile = CustomerProfile(
            user_id=target_user_id,
            all_interested_models=[vehicle_name] if vehicle_name else [],
            total_test_drives=1,
            lead_score="HOT",
            lead_status="TEST_DRIVEN",
        )
        db.add(profile)
    else:
        models = list(profile.all_interested_models or [])
        if vehicle_name and vehicle_name not in models:
            models.append(vehicle_name)
        profile.all_interested_models = models
        profile.total_test_drives = (profile.total_test_drives or 0) + 1
        profile.lead_score = "HOT"
        profile.lead_status = "TEST_DRIVEN"
        profile.last_interaction_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(profile)
    return profile


async def get_customer_profiles_list(
    db: AsyncSession,
    lead_score: str | None = None,
    lead_status: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[CustomerProfile]:
    """List CRM profiles for staff with optional filters."""
    statement = (
        select(CustomerProfile)
        .options(selectinload(CustomerProfile.account))
        .join(CustomerProfile.account)
    )
    if lead_score:
        statement = statement.where(CustomerProfile.lead_score == lead_score)
    if lead_status:
        statement = statement.where(CustomerProfile.lead_status == lead_status)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Account.full_name.ilike(pattern),
                Account.phone.ilike(pattern),
                Account.email.ilike(pattern),
            )
        )

    result = await db.execute(
        statement.order_by(desc(CustomerProfile.last_interaction_at))
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().unique().all())


async def get_customer_profile_by_id(
    db: AsyncSession,
    profile_id: uuid.UUID,
) -> CustomerProfile | None:
    """Load one CRM profile and its account details."""
    result = await db.execute(
        select(CustomerProfile)
        .options(selectinload(CustomerProfile.account))
        .where(CustomerProfile.profile_id == profile_id)
    )
    return result.scalars().first()
