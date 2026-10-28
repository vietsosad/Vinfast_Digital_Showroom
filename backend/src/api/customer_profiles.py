"""REST endpoints for the staff-managed customer CRM."""

import uuid

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_current_user, get_customer_profile_service, require_staff
from src.api.schemas.common import errors
from src.api.schemas.workflow import CustomerProfileResponse, CustomerProfileUpdate
from src.application.customer_profiles import CustomerProfileService, ProfileChanges
from src.domain.accounts import Account
from src.domain.customers import CustomerProfile, CustomerProfileFilter, LeadScore, LeadStatus

router = APIRouter()


@router.get("", response_model=list[CustomerProfileResponse], summary="Tra cứu hồ sơ CRM", responses=errors(401, 403))
async def list_profiles(
    lead_score: LeadScore | None = Query(None),
    lead_status: LeadStatus | None = Query(None),
    search: str | None = Query(None, max_length=100, description="Tên, số điện thoại hoặc email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Account = Depends(require_staff),
    service: CustomerProfileService = Depends(get_customer_profile_service),
) -> list[CustomerProfile]:
    criteria = CustomerProfileFilter(
        lead_score=lead_score, lead_status=lead_status, search=search or None, skip=skip, limit=limit
    )
    return await service.list_profiles(current_user.actor, criteria)


@router.get("/me", response_model=CustomerProfileResponse, summary="Hồ sơ CRM của tôi", responses=errors(401, 404))
async def get_my_profile(
    current_user: Account = Depends(get_current_user),
    service: CustomerProfileService = Depends(get_customer_profile_service),
) -> CustomerProfile:
    return await service.get_own_profile(current_user.actor)


@router.get(
    "/{profile_id}", response_model=CustomerProfileResponse, summary="Chi tiết hồ sơ CRM", responses=errors(401, 403, 404)
)
async def get_profile(
    profile_id: uuid.UUID,
    current_user: Account = Depends(require_staff),
    service: CustomerProfileService = Depends(get_customer_profile_service),
) -> CustomerProfile:
    return await service.get_profile(current_user.actor, profile_id)


@router.put(
    "/{profile_id}",
    response_model=CustomerProfileResponse,
    summary="Cập nhật lead hoặc ghi chú thủ công",
    responses=errors(401, 403, 404),
)
async def update_profile(
    profile_id: uuid.UUID,
    payload: CustomerProfileUpdate,
    current_user: Account = Depends(require_staff),
    service: CustomerProfileService = Depends(get_customer_profile_service),
) -> CustomerProfile:
    changes = ProfileChanges(
        lead_score=payload.lead_score,
        lead_status=payload.lead_status,
        all_interested_models=payload.all_interested_models,
        customer_note=payload.customer_note,
        clear_note="customer_note" in payload.model_fields_set and payload.customer_note is None,
    )
    return await service.update_profile(current_user.actor, profile_id, changes)
