"""Index existing catalog images into the normalized vehicle_media table."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
UPLOAD_ROOT = REPOSITORY_ROOT / "static" / "uploads"
sys.path.insert(0, str(BACKEND_ROOT))


# Chuẩn hóa tên thành slug ASCII để so khớp tên thư mục ảnh trong kho uploads.
def slugify(value: str) -> str:
    value = value.lower().replace("đ", "d")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value


# Tạo slug thư mục theo dòng xe và tên mẫu; ưu tiên ánh xạ tường minh cho tên đặc biệt.
def catalog_slug(vehicle_line: str, model_name: str) -> str:
    identity = f"{vehicle_line} {model_name}".lower()
    explicit = {
        "vf mpv 7": "vf-mpv-7",
        "minio green": "minio-green",
        "herio green": "herio-green",
        "nerio green": "nerio-green",
        "limo green": "limo-green",
        "ec van": "ec-van",
        "vf drgnfly": "vf-drgnfly",
    }
    for needle, slug in explicit.items():
        if needle in identity:
            return slug
    if "vf 8" in identity and "all new" in identity:
        return "vf8-the-all-new"
    compact_vf = re.search(r"vf\s*(\d+)", identity)
    if compact_vf:
        return f"vf{compact_vf.group(1)}"
    return slugify(vehicle_line)


# Tính SHA-256 theo từng khối để tránh nạp toàn bộ tệp ảnh lớn vào bộ nhớ.
def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# Đồng bộ ảnh có sẵn của danh mục xe vào bảng vehicle_media, tránh thêm URL trùng.
async def seed_media() -> None:
    from sqlalchemy import select

    from src.models.domain import Base, CarCatalog, MotorbikeCatalog, VehicleMedia
    from src.services.database import SessionLocal, engine

    # Đảm bảo các bảng cần thiết tồn tại trước khi tạo bản ghi ảnh.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    inserted = skipped = 0
    async with SessionLocal() as session:
        # Dùng chung quy trình cho ô tô và xe máy với bảng, thư mục và khóa tương ứng.
        groups = (
            ("car", CarCatalog, "cars", "car_id"),
            ("motorbike", MotorbikeCatalog, "motorbikes", "motorbike_id"),
        )
        for vehicle_type, model, folder, key_name in groups:
            vehicles = list((await session.scalars(select(model))).all())
            for vehicle in vehicles:
                vehicle_id = getattr(vehicle, key_name)
                # Thu thập URL đã có để script có thể chạy lặp mà không tạo bản ghi trùng.
                existing_urls = set(
                    await session.scalars(
                        select(VehicleMedia.url).where(
                            (VehicleMedia.car_id == vehicle_id)
                            if vehicle_type == "car"
                            else (VehicleMedia.motorbike_id == vehicle_id)
                        )
                    )
                )
                drafts: list[dict] = []
                # Ảnh đại diện trong danh mục được đưa vào làm ảnh hero/chính nếu chưa tồn tại.
                if vehicle.image_url and vehicle.image_url not in existing_urls:
                    drafts.append(
                        {
                            "url": vehicle.image_url,
                            "media_type": "hero",
                            "angle": "catalog",
                            "alt_text": vehicle.model_name,
                            "sort_order": 0,
                            "is_primary": True,
                        }
                    )

                slug = catalog_slug(vehicle.vehicle_line, vehicle.model_name)
                color_root = UPLOAD_ROOT / folder / "colors" / slug
                # Quét ảnh màu theo từng mẫu xe, bỏ qua tệp không phải ảnh và URL đã được nhập.
                if color_root.exists():
                    for order, path in enumerate(sorted(color_root.rglob("*")), start=1):
                        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
                            continue
                        url = "/" + path.relative_to(REPOSITORY_ROOT).as_posix()
                        if url in existing_urls:
                            skipped += 1
                            continue
                        stem = path.stem.lower().removesuffix("-swatch")
                        color_code = stem.removeprefix(f"{slug}-")
                        drafts.append(
                            {
                                "url": url,
                                "media_type": "color",
                                "angle": "full" if path.parent.name == "full" else "swatch",
                                "color_code": color_code,
                                "alt_text": f"{vehicle.model_name} - {color_code}",
                                "sort_order": order,
                                "is_primary": False,
                                "checksum": checksum(path),
                            }
                        )

                # Gắn khóa xe vào từng bản ghi ảnh trước khi thêm vào giao dịch hiện tại.
                for values in drafts:
                    values[key_name] = vehicle_id
                    session.add(VehicleMedia(**values))
                    inserted += 1
        # Ghi toàn bộ dữ liệu một lần để các thay đổi được lưu trong cùng giao dịch.
        await session.commit()

    print(f"Vehicle media seed complete: inserted={inserted}, skipped={skipped}")
    # Đóng connection pool khi script chạy độc lập kết thúc.
    await engine.dispose()


# Chuyển URL PostgreSQL mặc định sang dialect async mà ứng dụng sử dụng.
def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    return url


# Đọc tùy chọn dòng lệnh và khởi chạy seed bất đồng bộ.
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    args = parser.parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = normalize_database_url(args.database_url)
    asyncio.run(seed_media())


if __name__ == "__main__":
    main()
