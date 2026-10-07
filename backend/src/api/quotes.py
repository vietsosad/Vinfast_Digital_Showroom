import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.domain import Account, Quote, User
from src.models.schemas import QuoteCreate, QuoteResponse, QuoteUpdateStatus
from src.services.database import get_db
from src.services.security import get_current_user, require_roles

router = APIRouter()


async def list_quotes(db: AsyncSession) -> list[Quote]:
    result = await db.scalars(select(Quote).order_by(Quote.created_at.desc()))
    return list(result.all())


async def create_quote(db: AsyncSession, payload: QuoteCreate) -> Quote:
    quote = Quote(**payload.model_dump())
    db.add(quote)
    await db.commit()
    await db.refresh(quote)

    # Đồng bộ số lượng báo giá & dòng xe vào Customer Profile 360°
    try:
        if payload.user_id:
            import datetime

            from src.models.domain import CustomerProfile
            stmt = select(CustomerProfile).where(CustomerProfile.user_id == payload.user_id)
            res = await db.execute(stmt)
            prof = res.scalars().first()
            if prof:
                prof.total_quotes = (prof.total_quotes or 0) + 1
                prof.lead_status = "QUOTED"
                prof.lead_score = "HOT"
                if payload.vehicle_name:
                    cur_m = list(prof.all_interested_models or [])
                    if payload.vehicle_name not in cur_m:
                        cur_m.append(payload.vehicle_name)
                    prof.all_interested_models = cur_m
                prof.last_interaction_at = datetime.datetime.utcnow()
                await db.commit()
    except Exception as e:
        print(f"[Quote] Error syncing customer profile: {e}")

    return quote


@router.get("", response_model=list[QuoteResponse])
async def get_quotes(
    user_id: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    current_user: Account = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import or_

    query = select(Quote)
    conditions = []
    if current_user.role == "customer":
        conditions.append(Quote.user_id == str(current_user.user_id))
    else:
        if user_id and user_id.strip():
            conditions.append(Quote.user_id == user_id.strip())
        if email and email.strip():
            conditions.append(Quote.customer_email.ilike(email.strip()))
        if phone and phone.strip():
            conditions.append(Quote.customer_phone == phone.strip())

    if conditions:
        query = query.where(or_(*conditions))

    query = query.order_by(Quote.created_at.desc())
    result = await db.scalars(query)
    return list(result.all())



@router.post("", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def post_quote(
    payload: QuoteCreate,
    current_user: Account = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    owned_payload = payload.model_copy(update={
        "user_id": str(current_user.user_id),
        "customer_name": current_user.full_name,
        "customer_email": current_user.email,
        "customer_phone": current_user.phone,
    })
    return await create_quote(db, owned_payload)


@router.put("/{quote_id}", response_model=QuoteResponse)
async def update_quote_status(
    quote_id: uuid.UUID,
    payload: QuoteUpdateStatus,
    current_user: User = Depends(require_roles(["admin", "consultant"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo giá này!")

    quote.status = payload.status
    if payload.notes is not None:
        quote.notes = payload.notes
    if payload.discount is not None:
        quote.discount = payload.discount
    if payload.final_price is not None:
        quote.final_price = payload.final_price

    await db.commit()
    await db.refresh(quote)
    return quote
