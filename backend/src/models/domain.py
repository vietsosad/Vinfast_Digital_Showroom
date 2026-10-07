import uuid
from datetime import date, datetime

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


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


class Base(DeclarativeBase):
    pass


# 1. Accounts Table (Khớp chính xác tên trường với bảng users cũ + tên bảng accounts mới)
class Account(Base):
    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="customer", nullable=False)  # "customer", "consultant", "admin"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Compatibility alias for code expecting id or password_hash
    @property
    def id(self) -> uuid.UUID:
        return self.user_id

    @property
    def password_hash(self) -> str:
        return self.hashed_password

    @password_hash.setter
    def password_hash(self, value: str):
        self.hashed_password = value

    @property
    def status(self) -> str:
        return "active" if self.is_active else "inactive"

    @status.setter
    def status(self, value: str):
        self.is_active = (value == "active")


# Alias for legacy references to User
User = Account


# 2. Car Catalog Table (bảng car_catalog theo DB mới + image_url, version, category)
class CarCatalog(Base):
    __tablename__ = "car_catalog"

    car_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_line: Mapped[str] = mapped_column(String(50), nullable=False)  # "VF 5", "VF 8"
    version: Mapped[str | None] = mapped_column(String(50))  # "Plus", "Eco", "Base"
    category: Mapped[str] = mapped_column(String(50), default="Personal", nullable=False)  # "Personal", "Service", "Bus"
    image_url: Mapped[str | None] = mapped_column(String)  # Đường dẫn ảnh chính top-level
    # NULL is intentional for EBus: no verified exterior-color catalog exists.
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    media = relationship("VehicleMedia", back_populates="car", cascade="all, delete-orphan", lazy="selectin")

    # Compatibility properties for legacy code expecting id, name, code, base_price, specs
    @property
    def id(self) -> uuid.UUID:
        return self.car_id

    @property
    def name(self) -> str:
        return self.model_name

    @name.setter
    def name(self, value: str):
        self.model_name = value

    @property
    def code(self) -> str:
        return self.vehicle_line

    @code.setter
    def code(self, value: str):
        self.vehicle_line = value

    @property
    def base_price(self) -> int:
        return self.list_price or 0

    @base_price.setter
    def base_price(self, value: int):
        self.list_price = value

    @property
    def specs(self) -> dict:
        return self.additional_specs

    @specs.setter
    def specs(self, value: dict):
        self.additional_specs = value

    @property
    def is_available(self) -> bool:
        return self.is_active

    @is_available.setter
    def is_available(self, value: bool):
        self.is_active = value


# Alias for legacy references to Car
Car = CarCatalog


# 3. Motorbike Catalog Table (bảng motorbike_catalog theo DB mới + image_url, version, category)
class MotorbikeCatalog(Base):
    __tablename__ = "motorbike_catalog"

    motorbike_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_line: Mapped[str] = mapped_column(String(50), nullable=False)  # "Evo", "Feliz", "Klara"
    version: Mapped[str | None] = mapped_column(String(50))  # "Kèm pin", "Thuê pin"
    category: Mapped[str] = mapped_column(String(50), default="Scooter", nullable=False)
    image_url: Mapped[str | None] = mapped_column(String)  # Đường dẫn ảnh chính top-level
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    media = relationship("VehicleMedia", back_populates="motorbike", cascade="all, delete-orphan", lazy="selectin")

    # Compatibility properties for legacy code expecting id, name, code, base_price, specs
    @property
    def id(self) -> uuid.UUID:
        return self.motorbike_id

    @property
    def name(self) -> str:
        return self.model_name

    @name.setter
    def name(self, value: str):
        self.model_name = value

    @property
    def code(self) -> str:
        return self.vehicle_line

    @code.setter
    def code(self, value: str):
        self.vehicle_line = value

    @property
    def base_price(self) -> int:
        return self.list_price or 0

    @base_price.setter
    def base_price(self, value: int):
        self.list_price = value

    @property
    def specs(self) -> dict:
        return self.additional_specs

    @specs.setter
    def specs(self, value: dict):
        self.additional_specs = value

    @property
    def is_available(self) -> bool:
        return self.is_active

    @is_available.setter
    def is_available(self, value: bool):
        self.is_active = value


class VehicleMedia(Base):
    """Normalized product media for cars and motorbikes.

    Exactly one catalog foreign key is populated. Files live in static/object
    storage; the database stores only URLs and searchable metadata.
    """

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    car = relationship("CarCatalog", back_populates="media")
    motorbike = relationship("MotorbikeCatalog", back_populates="media")


# Alias for legacy references to EScooter
EScooter = MotorbikeCatalog


# Business workflow tables
class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TestDriveBooking(Base):
    __tablename__ = "test_drive_bookings"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    customer_name: Mapped[str] = mapped_column(String, nullable=False)
    customer_phone: Mapped[str] = mapped_column(String, nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String, nullable=False)
    vehicle_name: Mapped[str] = mapped_column(String, nullable=False)
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_time: Mapped[str] = mapped_column(String, default="09:00")
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Human support chat
class SupportConversation(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SupportMessage(Base):
    __tablename__ = "support_messages"

    message_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("support_conversations.conversation_id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("accounts.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# 9. VinFast Showrooms & Charging Stations Table
class VinfastLocation(Base):
    __tablename__ = "vinfast_locations"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    types: Mapped[list] = mapped_column(JSON, nullable=False)  # ['showroom_car', 'charging_car', etc.]
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# 10. Customer Profiles Table (Chân dung khách hàng 360° Tổng thể - Quan hệ 1-1 với accounts)
class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    profile_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)

    # Khóa ngoại duy nhất nối sang bảng accounts (Quan hệ 1 - 1, không lưu trùng lặp Họ tên, SĐT, Email)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("accounts.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Đánh giá phân loại khách hàng (CRM Lead Scoring)
    lead_score: Mapped[str] = mapped_column(String(20), default="WARM", nullable=False)  # "HOT", "WARM", "COLD"
    lead_status: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False)  # "NEW", "CONTACTED", "TEST_DRIVEN", "QUOTED", "WON", "LOST"
    all_interested_models: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # Tích lũy tất cả các xe từng quan tâm
    customer_note: Mapped[str | None] = mapped_column("ai_customer_portrait", Text)

    # Thống kê hoạt động tổng quan
    total_demands: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_quotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_test_drives: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_interaction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ORM Relationship tới bảng accounts
    account = relationship("Account", backref="customer_profile", lazy="joined")


# 11. Customer Demands Table (Lưu vết từng đợt nhu cầu tìm mua xe riêng biệt của khách hàng - Quan hệ 1 - Nhiều)
class CustomerDemand(Base):
    __tablename__ = "customer_demands"

    demand_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)

    # Khóa ngoại nối sang accounts (1 Account có thể có nhiều Demands qua các đợt)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("accounts.user_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    session_id: Mapped[str | None] = mapped_column(String(255), index=True)

    # Nhu cầu riêng biệt của đợt này
    vehicle_type: Mapped[str] = mapped_column(String(50), default="CAR", nullable=False)  # "CAR", "MOTORBIKE", "BOTH"
    target_models: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    budget_min: Mapped[int | None] = mapped_column(BigInteger)
    budget_max: Mapped[int | None] = mapped_column(BigInteger)
    usage_purpose: Mapped[str | None] = mapped_column(String(100))
    battery_preference: Mapped[str | None] = mapped_column(String(50))
    charging_condition: Mapped[str | None] = mapped_column(String(100))
    demand_summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)  # "ACTIVE", "QUOTED", "TEST_DRIVEN", "PURCHASED", "CLOSED"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ORM Relationship
    account = relationship("Account", backref="demands", lazy="joined")

