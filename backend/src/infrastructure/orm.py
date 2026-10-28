"""SQLAlchemy table mappings. Only repositories and seeders use these classes."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR, TypeDecorator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GUID(TypeDecorator):
    """Platform-independent UUID: native UUID on PostgreSQL, CHAR(36) elsewhere."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID

            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        return str(value if isinstance(value, uuid.UUID) else uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class Base(DeclarativeBase):
    pass


def created_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())


def updated_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now())


class AccountRow(Base):
    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="customer", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_column()
    updated_at: Mapped[datetime] = updated_column()


class CarRow(Base):
    __tablename__ = "car_catalog"

    car_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_line: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(50), default="Personal", nullable=False)
    image_url: Mapped[str | None] = mapped_column(String)
    colors: Mapped[list | None] = mapped_column(JSON, default=None, nullable=True)
    list_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seat_count: Mapped[int | None] = mapped_column(Integer)
    length_mm: Mapped[int | None] = mapped_column(Integer)
    width_mm: Mapped[int | None] = mapped_column(Integer)
    height_mm: Mapped[int | None] = mapped_column(Integer)
    wheelbase_mm: Mapped[int | None] = mapped_column(Integer)
    range_km: Mapped[float | None] = mapped_column(Float)
    maximum_power_kw: Mapped[float | None] = mapped_column(Float)
    maximum_torque_nm: Mapped[float | None] = mapped_column(Float)
    usable_battery_capacity: Mapped[float | None] = mapped_column(Float)
    additional_specs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_column()
    updated_at: Mapped[datetime] = updated_column()


class MotorbikeRow(Base):
    __tablename__ = "motorbike_catalog"

    motorbike_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_line: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(50), default="Scooter", nullable=False)
    image_url: Mapped[str | None] = mapped_column(String)
    colors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    list_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    range_km: Mapped[float | None] = mapped_column(Float)
    charging_time_minutes: Mapped[int | None] = mapped_column(Integer)
    battery_type: Mapped[str | None] = mapped_column(String(100))
    battery_quantity: Mapped[int | None] = mapped_column(Integer, default=1)
    battery_capacity_kwh: Mapped[float | None] = mapped_column(Float)
    motor_type: Mapped[str | None] = mapped_column(String(100))
    maximum_power_w: Mapped[float | None] = mapped_column(Float)
    maximum_speed_kmh: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    length_mm: Mapped[int | None] = mapped_column(Integer)
    width_mm: Mapped[int | None] = mapped_column(Integer)
    height_mm: Mapped[int | None] = mapped_column(Integer)
    front_brake: Mapped[str | None] = mapped_column(String(100))
    rear_brake: Mapped[str | None] = mapped_column(String(100))
    front_suspension: Mapped[str | None] = mapped_column(String(100))
    rear_suspension: Mapped[str | None] = mapped_column(String(100))
    additional_specs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_column()
    updated_at: Mapped[datetime] = updated_column()


class VehicleMediaRow(Base):
    """Normalized product media; exactly one catalog foreign key is populated."""

    __tablename__ = "vehicle_media"
    __table_args__ = (
        CheckConstraint(
            "(car_id IS NOT NULL AND motorbike_id IS NULL) OR "
            "(car_id IS NULL AND motorbike_id IS NOT NULL)",
            name="ck_vehicle_media_exactly_one_vehicle",
        ),
        UniqueConstraint("car_id", "motorbike_id", "url", name="uq_vehicle_media_vehicle_url"),
    )

    media_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    car_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("car_catalog.car_id", ondelete="CASCADE"), index=True
    )
    motorbike_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("motorbike_catalog.motorbike_id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(String(30), default="exterior", index=True, nullable=False)
    angle: Mapped[str | None] = mapped_column(String(50))
    color_code: Mapped[str | None] = mapped_column(String(80), index=True)
    alt_text: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_label: Mapped[str | None] = mapped_column(String(120))
    checksum: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = created_column()
    updated_at: Mapped[datetime] = updated_column()


class QuoteRow(Base):
    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # Stored as text for compatibility with databases created before Phase 1 hardening.
    user_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    customer_name: Mapped[str] = mapped_column(String, nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String)
    customer_phone: Mapped[str] = mapped_column(String, nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String, nullable=False)
    vehicle_name: Mapped[str] = mapped_column(String, nullable=False)
    base_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    final_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    request_note: Mapped[str | None] = mapped_column("ai_summary", Text)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_column()
    updated_at: Mapped[datetime] = updated_column()


class TestDriveBookingRow(Base):
    __tablename__ = "test_drive_bookings"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # Ownership key. Added by migration 0001 for databases created earlier.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("accounts.user_id", ondelete="SET NULL"), index=True, nullable=True
    )
    customer_name: Mapped[str] = mapped_column(String, nullable=False)
    customer_phone: Mapped[str] = mapped_column(String, nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String, nullable=False)
    vehicle_name: Mapped[str] = mapped_column(String, nullable=False)
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_time: Mapped[str] = mapped_column(String, default="09:00")
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_column()


class SupportConversationRow(Base):
    __tablename__ = "support_conversations"

    conversation_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("accounts.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("accounts.user_id", ondelete="SET NULL"), index=True, nullable=True
    )
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True, nullable=False)
    created_at: Mapped[datetime] = created_column()
    updated_at: Mapped[datetime] = updated_column()


class SupportMessageRow(Base):
    __tablename__ = "support_messages"

    message_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("support_conversations.conversation_id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("accounts.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = created_column()


class LocationRow(Base):
    __tablename__ = "vinfast_locations"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    types: Mapped[list] = mapped_column(JSON, nullable=False)
    type_label: Mapped[str] = mapped_column(String(255), default="Trạm Sạc & Showroom VinFast")
    province: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    ward: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hotline_service: Mapped[str | None] = mapped_column(String(50), nullable=True)
    opening_hours: Mapped[str] = mapped_column(String(100), default="08:00 - 22:00 (Trạm sạc 24/7)")
    charging_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="vinfast_official")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_column()
    updated_at: Mapped[datetime] = updated_column()


class CustomerProfileRow(Base):
    """One CRM profile per account (1-1)."""

    __tablename__ = "customer_profiles"

    profile_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("accounts.user_id", ondelete="CASCADE"), unique=True, nullable=False
    )
    lead_score: Mapped[str] = mapped_column(String(20), default="WARM", nullable=False)
    lead_status: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False)
    all_interested_models: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    customer_note: Mapped[str | None] = mapped_column("ai_customer_portrait", Text)
    total_demands: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_quotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_test_drives: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_interaction_at: Mapped[datetime] = created_column()
    created_at: Mapped[datetime] = created_column()
    updated_at: Mapped[datetime] = updated_column()

    account: Mapped[AccountRow] = relationship(AccountRow, lazy="joined")


class CustomerDemandRow(Base):
    """Historical demand rounds per account (1-N). Kept for schema compatibility."""

    __tablename__ = "customer_demands"

    demand_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("accounts.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    session_id: Mapped[str | None] = mapped_column(String(255), index=True)
    vehicle_type: Mapped[str] = mapped_column(String(50), default="CAR", nullable=False)
    target_models: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    budget_min: Mapped[int | None] = mapped_column(BigInteger)
    budget_max: Mapped[int | None] = mapped_column(BigInteger)
    usage_purpose: Mapped[str | None] = mapped_column(String(100))
    battery_preference: Mapped[str | None] = mapped_column(String(50))
    charging_condition: Mapped[str | None] = mapped_column(String(100))
    demand_summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = created_column()
    updated_at: Mapped[datetime] = updated_column()
