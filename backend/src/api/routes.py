"""Application route registry.

Feature modules own their request/response schemas. This file only composes the
public API and contains no business logic.
"""

from fastapi import APIRouter

from src.api.auth import router as auth_router
from src.api.bookings import router as bookings_router
from src.api.cars import router as cars_router
from src.api.customer_profiles import router as customer_profiles_router
from src.api.locations import router as locations_router
from src.api.motorbikes import router as motorbikes_router
from src.api.quotes import router as quotes_router
from src.api.support_chat import router as support_chat_router
from src.api.tco import router as tco_router
from src.api.vehicle_media import router as vehicle_media_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(cars_router, prefix="/cars", tags=["Car catalog"])
router.include_router(motorbikes_router, prefix="/motorbikes", tags=["Motorbike catalog"])
router.include_router(locations_router, prefix="/locations", tags=["Showrooms and charging"])
router.include_router(quotes_router, prefix="/quotes", tags=["Quotes"])
router.include_router(bookings_router, prefix="/bookings", tags=["Test-drive bookings"])
router.include_router(customer_profiles_router, prefix="/customer-profiles", tags=["Customer CRM"])
router.include_router(tco_router, prefix="/tco", tags=["Ownership cost"])
router.include_router(support_chat_router, prefix="/conversations", tags=["Human support chat"])
router.include_router(vehicle_media_router, prefix="/catalog-media", tags=["Catalog media"])
