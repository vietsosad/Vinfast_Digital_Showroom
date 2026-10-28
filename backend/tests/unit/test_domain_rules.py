from datetime import date, timedelta
from uuid import uuid4

import pytest

from src.application.uploads import detect_image_format, validate_image
from src.domain.accounts import normalize_email, normalize_phone
from src.domain.bookings import Booking, BookingStatus, validate_schedule
from src.domain.errors import FileTooLargeError, InvalidStateTransitionError, ValidationError
from src.domain.files import UploadedFile
from src.domain.identity import Actor, Role, parse_role
from src.domain.quotes import Quote, QuoteStatus


def make_quote(status=QuoteStatus.PENDING, base_price=1_000):
    return Quote(uuid4(), uuid4(), "A", None, "0900000000", "v", "VF", base_price, 0, base_price, None, status)


def test_phone_and_email_normalization():
    assert normalize_phone(" 0912.345-678 ") == "0912345678"
    assert normalize_phone("+84912345678") == "+84912345678"
    with pytest.raises(ValidationError):
        normalize_phone("12ab")
    assert normalize_email("  User@Example.COM ") == "user@example.com"


def test_roles_and_actor_capabilities():
    assert Actor(uuid4(), Role.CONSULTANT).is_staff
    assert not Actor(uuid4(), Role.CUSTOMER).is_staff
    assert Actor(uuid4(), Role.ADMIN).is_admin
    assert parse_role("superuser") is Role.CUSTOMER


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (QuoteStatus.PENDING, QuoteStatus.APPROVED),
        (QuoteStatus.PENDING, QuoteStatus.CONTACTED),
        (QuoteStatus.CONTACTED, QuoteStatus.REJECTED),
        (QuoteStatus.APPROVED, QuoteStatus.COMPLETED),
        (QuoteStatus.APPROVED, QuoteStatus.APPROVED),
    ],
)
def test_allowed_quote_transitions(start, target):
    quote = make_quote(start)
    quote.change_status(target)
    assert quote.status is target


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (QuoteStatus.APPROVED, QuoteStatus.PENDING),
        (QuoteStatus.REJECTED, QuoteStatus.APPROVED),
        (QuoteStatus.COMPLETED, QuoteStatus.CANCELLED),
        (QuoteStatus.PENDING, QuoteStatus.COMPLETED),
    ],
)
def test_forbidden_quote_transitions(start, target):
    with pytest.raises(InvalidStateTransitionError):
        make_quote(start).change_status(target)


def test_discount_bounds_and_final_price():
    quote = make_quote(base_price=1_000)
    quote.apply_discount(250)
    assert quote.final_price == 750
    with pytest.raises(ValidationError):
        quote.apply_discount(1_001)
    with pytest.raises(ValidationError):
        quote.apply_discount(-1)


def test_booking_transitions():
    booking = Booking(uuid4(), uuid4(), "A", "0900000000", "v", "VF", date.today(), "09:00", BookingStatus.PENDING)
    with pytest.raises(InvalidStateTransitionError):
        booking.change_status(BookingStatus.COMPLETED)
    booking.change_status(BookingStatus.CONFIRMED)
    booking.change_status(BookingStatus.COMPLETED)
    with pytest.raises(InvalidStateTransitionError):
        booking.change_status(BookingStatus.CANCELLED)


def test_booking_schedule_rules():
    today = date(2026, 10, 15)
    validate_schedule(today, "08:30", today)
    for bad_date, bad_time in [(today - timedelta(days=1), "09:00"), (today, "9:00"), (today, "24:00"), (today + timedelta(days=181), "09:00")]:
        with pytest.raises(ValidationError):
            validate_schedule(bad_date, bad_time, today)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"\xff\xd8\xff\xe0rest", ".jpg"),
        (b"\x89PNG\r\n\x1a\nrest", ".png"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", ".webp"),
        (b"\x00\x00\x00\x1cftypavif", ".avif"),
        (b"GIF89a", None),
        (b"<svg xmlns=", None),
    ],
)
def test_image_signature_detection(content, expected):
    assert detect_image_format(content) == expected


def test_image_validation_checks_extension_mime_and_size():
    jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 10
    assert validate_image(UploadedFile("a.JPEG", "image/jpeg", jpeg)) == ".jpg"
    with pytest.raises(ValidationError):
        validate_image(UploadedFile("a.png", "image/png", jpeg))
    with pytest.raises(ValidationError):
        validate_image(UploadedFile("a.jpg", "text/html", jpeg))
    with pytest.raises(ValidationError):
        validate_image(UploadedFile("a.jpg", "image/jpeg", b""))
    with pytest.raises(FileTooLargeError):
        validate_image(UploadedFile("a.jpg", "image/jpeg", jpeg), max_bytes=4)


def test_showroom_day_uses_vietnam_time():
    from datetime import datetime, timezone

    from src.domain.bookings import showroom_today

    # 20:00 UTC on the 15th is already 03:00 on the 16th in Vietnam.
    late_utc = datetime(2026, 10, 15, 20, 0, tzinfo=timezone.utc)
    assert showroom_today(late_utc) == date(2026, 10, 16)
    with pytest.raises(ValidationError):
        validate_schedule(date(2026, 10, 15), "09:00", showroom_today(late_utc))
