"""Kiểm tra ảnh đại diện của xe trước khi lưu vào danh mục.

CarCatalogService và MotorbikeCatalogService dùng các hàm ở đây. Luồng tải
nhiều ảnh vào thư viện ảnh (API vehicle_media) hiện có kiểm tra riêng, chưa
gọi module này.
"""

from __future__ import annotations

import re
from pathlib import PurePath
from uuid import uuid4

from src.domain.errors import FileTooLargeError, ValidationError
from src.domain.files import UploadedFile

DEFAULT_MAX_IMAGE_BYTES = 8 * 1024 * 1024

# Khóa là phần mở rộng chuẩn sẽ lưu; giá trị là các phần mở rộng và MIME được chấp nhận.
IMAGE_FORMATS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    ".jpg": (frozenset({".jpg", ".jpeg"}), frozenset({"image/jpeg", "image/jpg", "image/pjpeg"})),
    ".png": (frozenset({".png"}), frozenset({"image/png"})),
    ".webp": (frozenset({".webp"}), frozenset({"image/webp"})),
    ".avif": (frozenset({".avif"}), frozenset({"image/avif"})),
}


def detect_image_format(content: bytes) -> str | None:
    """Nhận diện định dạng bằng chữ ký đầu tệp, không dựa riêng vào tên tệp."""
    # Mỗi định dạng có một chuỗi byte đặc trưng ở đầu (thường gọi là magic bytes).
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    if len(content) >= 12 and content[4:8] == b"ftyp" and content[8:12] in (b"avif", b"avis"):
        return ".avif"
    return None


def validate_image(upload: UploadedFile, max_bytes: int = DEFAULT_MAX_IMAGE_BYTES) -> str:
    """Kiểm tra tệp tải lên; trả về phần mở rộng chuẩn hoặc báo lỗi nghiệp vụ.

    Hàm kiểm tra chữ ký đầu tệp, không giải mã toàn bộ ảnh để chứng minh tệp
    có thể hiển thị hoàn chỉnh.
    """
    # Từ chối tệp rỗng và tệp vượt giới hạn trước khi làm các bước kiểm tra khác.
    if not upload.content:
        raise ValidationError("Tệp ảnh rỗng")
    if len(upload.content) > max_bytes:
        raise FileTooLargeError(f"Mỗi ảnh tối đa {max_bytes // (1024 * 1024)} MB")

    # Tên và MIME do phía gửi cung cấp nên được đối chiếu với chữ ký thực của nội dung.
    extension = PurePath(upload.filename or "").suffix.lower()
    detected = detect_image_format(upload.content)
    if detected is None:
        raise ValidationError("Nội dung tệp không phải ảnh JPG, PNG, WebP hoặc AVIF hợp lệ")

    # Bắt trường hợp nội dung là một định dạng nhưng tên tệp lại khai báo định dạng khác.
    extensions, mime_types = IMAGE_FORMATS[detected]
    if extension not in extensions:
        raise ValidationError("Phần mở rộng tệp không khớp với nội dung ảnh")

    # MIME có thể bị bỏ trống hoặc gửi dạng chung; nếu có MIME cụ thể thì phải khớp.
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type != "application/octet-stream" and content_type not in mime_types:
        raise ValidationError("Kiểu MIME không khớp với nội dung ảnh")
    # Dùng định dạng đã nhận diện làm đuôi chuẩn, không dùng trực tiếp đuôi do người gửi đặt.
    return detected


def storage_filename(original: str, extension: str) -> str:
    """Tạo tên lưu an toàn hơn: giữ phần tên dễ đọc, bỏ ký tự lạ và thêm mã ngẫu nhiên.

    ``extension`` nên là kết quả từ ``validate_image`` để khớp với nội dung ảnh.
    """
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", PurePath(original or "image").stem).strip("-")
    return f"{(stem or 'image')[:60]}-{uuid4().hex[:10]}{extension}"
