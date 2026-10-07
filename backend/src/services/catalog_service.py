"""Supabase Catalog Query Service for VinFast Vehicles & Motorbikes.

Dynamically queries `public.car_catalog` and `public.motorbike_catalog`
from Supabase Cloud DB with resilient offline fallback.
"""

import re
import time
import unicodedata
from typing import Any

import requests

from src.config import get_settings

settings = get_settings()

_CATALOG_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
CACHE_TTL_SECONDS = 86400.0  # 24 hours in-memory RAM cache for catalog


def get_catalog_aggregation(
    aggregation: str | None,
    vehicle_type: str = "CAR",
    seat_count: int | None = None,
    seat_counts: list[int] | None = None,
    category: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    body_type: str | None = None,
    drivetrain: str | None = None,
) -> dict[str, Any] | None:
    """Calculate aggregation (most_expensive, cheapest, longest_range, most_powerful, largest_trunk)
    directly by delegating to the unified catalog search function with full filter support.
    """
    if not aggregation:
        return None

    v_type = (vehicle_type or "CAR").upper()
    if v_type == "MOTORBIKE":
        res = fetch_motorbikes_from_supabase(
            budget_min=budget_min,
            budget_max=budget_max,
            aggregation=aggregation,
        )
        return res[0] if res else None
    elif v_type == "BOTH":
        c_res = fetch_cars_from_supabase(
            budget_min=budget_min,
            budget_max=budget_max,
            seat_count=seat_count,
            seat_counts=seat_counts,
            category=category,
            body_type=body_type,
            drivetrain=drivetrain,
            aggregation=aggregation,
        )
        b_res = fetch_motorbikes_from_supabase(
            budget_min=budget_min,
            budget_max=budget_max,
            aggregation=aggregation,
        )
        combined = c_res + b_res
        if not combined:
            return None
        agg = aggregation.lower().strip()
        if agg in ("most_expensive", "highest_price", "dat_nhat", "max_price"):
            return max(combined, key=lambda x: x.get("base_price", 0))
        elif agg in ("cheapest", "lowest_price", "re_nhat", "min_price"):
            valid = [x for x in combined if x.get("base_price", 0) > 0]
            return min(valid, key=lambda x: x.get("base_price", 0)) if valid else combined[0]
        elif agg in ("longest_range", "xa_nhat", "pin_trau_nhat", "max_range"):
            return max(combined, key=lambda x: x.get("range_km") or x.get("range_per_charge_km") or 0)
        return combined[0]
    else:
        res = fetch_cars_from_supabase(
            budget_min=budget_min,
            budget_max=budget_max,
            seat_count=seat_count,
            seat_counts=seat_counts,
            category=category,
            body_type=body_type,
            drivetrain=drivetrain,
            aggregation=aggregation,
        )
        return res[0] if res else None


def _generate_model_aliases(item: dict[str, Any], is_car: bool = True) -> dict[str, str]:
    """Generate smart, robust aliases for a vehicle record from catalog."""
    aliases: dict[str, str] = {}
    if is_car:
        formatted = format_car_record(item)
    else:
        formatted = format_motorbike_record(item)

    code = str(item.get("model_code") or item.get("code") or formatted.get("code") or "").lower().strip()
    name = str(item.get("model_name") or item.get("name") or formatted.get("name") or "").lower().strip()
    line = str(item.get("vehicle_line") or formatted.get("vehicle_line") or "").lower().strip()
    ver = str(item.get("version") or formatted.get("version") or "").lower().strip()

    if not code:
        return aliases

    def add(alias: str):
        a = " ".join(alias.strip().split())
        if a and len(a) >= 2 and not a.isdigit():
            aliases[a] = code

    # If code has complex suffixes like -awd---trần-kính-toàn-cảnh
    clean_code = code.split("-awd")[0].split("---")[0]
    add(code)
    add(clean_code)

    # Sub-variant / sub-trim extraction (e.g. "trần kính toàn cảnh", "trần thép")
    # from code (e.g. "---trần-kính-toàn-cảnh") or name (e.g. " - Trần thép")
    tails: list[str] = []
    if "---" in code:
        tail_part = code.split("---")[-1].replace("-", " ").strip()
        if tail_part:
            tails.append(tail_part)
    if " - " in name:
        tail_part = name.split(" - ")[-1].strip().lower()
        if tail_part and tail_part not in tails:
            tails.append(tail_part)
    if ver and ver not in tails and ver not in (line, code):
        tails.append(ver.lower())

    generic_trims = {"plus", "eco", "base", "tiêu chuẩn", "tieu chuan", "nâng cao", "nang cao", "cao cấp", "cao cap", "premium", "lite", "s", "s2"}
    for t in tails:
        if t not in generic_trims:
            add(t)
            add(f"bản {t}")
            add(f"bản {t.replace('-', ' ')}")
        if clean_code:
            c_spaced = clean_code.replace("-", " ")
            add(f"{c_spaced} {t}")
            add(f"{c_spaced} bản {t}")
            if "plus" in c_spaced:
                base_c = c_spaced.replace("plus", "").strip()
                add(f"{base_c} {t}")
                add(f"{base_c} bản {t}")
        if "toàn cảnh" in t:
            short_t = t.replace("toàn cảnh", "").strip()
            if len(short_t) >= 3:
                add(short_t)
                add(f"bản {short_t}")
                if clean_code:
                    c_spaced = clean_code.replace("-", " ")
                    add(f"{c_spaced} {short_t}")
                    add(f"{c_spaced} bản {short_t}")
                    if "plus" in c_spaced:
                        base_c = c_spaced.replace("plus", "").strip()
                        add(f"{base_c} {short_t}")
                        add(f"{base_c} bản {short_t}")

    # VF 5 is colloquially and commercially marketed as VF 5 Plus
    if "vf-5" in code or "vf 5" in name:
        add("vf 5 plus")
        add("vf5 plus")
        add("vf5plus")
        add("vf 5-plus")

    for raw in (code, clean_code, line, name):
        if not raw:
            continue
        cl = raw.replace("vinfast", "").strip()
        add(cl)
        add(cl.replace("-", " "))
        add(cl.replace("-", ""))
        add(cl.replace(" ", ""))

        # Strip "vf " or "vf" prefix if longer than 3 chars (e.g. "vf mpv 7" -> "mpv 7", "mpv7")
        if cl.startswith("vf ") and len(cl) > 3:
            sub = cl[3:].strip()
            if len(sub) >= 2 and not sub.isdigit():
                add(sub)
                add(sub.replace(" ", ""))
        elif cl.startswith("vf") and len(cl) > 2 and not cl[2:3].isdigit():
            sub = cl[2:].strip()
            if len(sub) >= 2 and not sub.isdigit():
                add(sub)
                add(sub.replace(" ", ""))

        # Strip common trims/suffixes only if NOT a specialized sub-trim:
        if not tails:
            for trim in (
                " tiêu chuẩn gia đình", " tiêu chuẩn", " plus awd", " plus", " eco",
                " lite neo", " lite", " neo", " s2", " s", " green", " service",
                " kèm pin", " kèm ắc quy", "-tiêu-chuẩn-gia-đình", "-tiêu-chuẩn", "-plus", "-eco"
            ):
                if cl.endswith(trim):
                    base = cl[:-len(trim)].strip()
                    if len(base) >= 2:
                        add(base)
                        add(base.replace(" ", ""))
                        add(base.replace("-", " "))
                        add(base.replace("-", ""))
                        if base.startswith("vf ") and len(base) > 3:
                            b_sub = base[3:].strip()
                            if len(b_sub) >= 2 and not b_sub.isdigit():
                                add(b_sub)
                                add(b_sub.replace(" ", ""))

        # Separate adjacent letters and digits (e.g. "vf7" -> "vf 7", "lux a2.0" -> "lux a 2.0")
        spaced = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", cl)
        if spaced != cl:
            add(spaced)
            add(spaced.replace("-", " "))
            add(spaced.replace("-", ""))
            if "." in spaced:
                add(spaced.replace(".", ""))
                add(spaced.replace(".", " "))

        # Dot handling (e.g. "lux a2.0" -> "lux a20", "lux a 2.0", "lux a 20")
        if "." in cl:
            add(cl.replace(".", ""))
            add(cl.replace(".", " "))
            add(cl.replace(".", "").replace(" ", ""))

        # Engine capacity suffixes (e.g. "lux a2.0" -> "lux a", "lux sa2.0" -> "lux sa")
        for suffix in (" 2.0", "2.0", " 20", "20"):
            if cl.endswith(suffix):
                base_eng = cl[:-len(suffix)].strip()
                if len(base_eng) >= 2:
                    add(base_eng)

    # Generic colloquial terms for e-bike
    if "drgnfly" in code or "drgnfly" in name or "drgnfly" in line:
        add("drgnfly")
        add("dragonfly")
        add("xe dap tro luc")
        add("xe đạp trợ lực")
        add("xe dap dien")
        add("xe đạp điện")

    return aliases


def get_dynamic_model_keyword_map() -> dict[str, str]:
    """Dynamically build keyword-to-model_code mapping from database catalog."""
    cars = _get_cached_raw_cars()
    bikes = _get_cached_raw_motorbikes()

    mapping: dict[str, str] = {}

    # Dynamically generate aliases for all cars in database (both active and discontinued)
    for c in cars:
        c_aliases = _generate_model_aliases(c, is_car=True)
        mapping.update(c_aliases)

    # Dynamically generate aliases for all motorbikes in database (both active and discontinued)
    for b in bikes:
        b_aliases = _generate_model_aliases(b, is_car=False)
        mapping.update(b_aliases)

    return mapping


def get_dynamic_catalog_summary() -> str:
    """Dynamically generate compact catalog summary from database catalog, including is_active status."""
    cars = [format_car_record(c) for c in _get_cached_raw_cars()]
    bikes = [format_motorbike_record(b) for b in _get_cached_raw_motorbikes()]

    active_cars = [c for c in cars if c.get("is_active", True)]
    discontinued_cars = [c for c in cars if not c.get("is_active", True)]
    active_bikes = [b for b in bikes if b.get("is_active", True)]
    discontinued_bikes = [b for b in bikes if not b.get("is_active", True)]

    personal_cars = [c for c in active_cars if c.get("category") == "Personal"]
    service_cars = [c for c in active_cars if c.get("category") == "Service"]
    commercial_cars = [c for c in active_cars if c.get("category") == "Commercial"]
    bus_cars = [c for c in active_cars if c.get("category") == "Bus"]
    luxury_cars = [c for c in active_cars if c.get("category") == "Luxury"]

    def _fmt_cars(car_list: list[dict[str, Any]]) -> str:
        items = []
        for c in car_list:
            if not c.get("name"):
                continue
            price_val = c.get("base_price") or 0
            if "ebus" in c.get("code", "").lower() or price_val <= 0:
                items.append(f"{c['name']} ({c['seats']} chỗ - Giá: Liên hệ B2B, Không bán lẻ)")
            else:
                items.append(f"{c['name']} ({c['seats']} chỗ, {price_val // 1_000_000}tr)")
        return ", ".join(items)

    personal_str = _fmt_cars(personal_cars)
    service_str = _fmt_cars(service_cars)
    commercial_str = _fmt_cars(commercial_cars)
    bus_str = _fmt_cars(bus_cars)
    luxury_str = _fmt_cars(luxury_cars)

    bike_strs = []
    for b in active_bikes:
        if not b.get("name"):
            continue
        price_val = b.get("base_price") or 0
        if price_val <= 0:
            bike_strs.append(f"{b['name']} (Giá: Liên hệ)")
        else:
            bike_strs.append(f"{b['name']} ({price_val // 1_000_000}tr)")

    discontinued_car_strs = [f"{c['name']} (is_active=FALSE)" for c in discontinued_cars if c.get("name")]
    discontinued_bike_strs = [f"{b['name']} (is_active=FALSE)" for b in discontinued_bikes if b.get("name")]

    discontinued_info = ""
    if discontinued_car_strs or discontinued_bike_strs:
        discontinued_info = (
            f"- Ô tô ĐÃ NGỪNG SẢN XUẤT/BÁN TRÊN THỊ TRƯỜNG (is_active=FALSE): {', '.join(discontinued_car_strs) if discontinued_car_strs else 'Không có'}.\n"
            f"- Xe máy ĐÃ NGỪNG SẢN XUẤT/BÁN TRÊN THỊ TRƯỜNG (is_active=FALSE): {', '.join(discontinued_bike_strs) if discontinued_bike_strs else 'Không có'}.\n"
        )

    return (
        "DANH MỤC CÁC DÒNG XE CỦA VINFAST TRONG CSDL THEO PHÂN LOẠI & MỤC ĐÍCH SỬ DỤNG:\n"
        f"1. DÒNG XE DU LỊCH CÁ NHÂN & GIA ĐÌNH (Category: Personal): {personal_str}.\n"
        f"2. DÒNG XE DỊCH VỤ VẬN TẢI HÀNH KHÁCH / TAXI CHUYÊN DỤNG (Category: Service - Dải xe Green Series gồm 4 mẫu): {service_str}.\n"
        f"   * Lưu ý quan trọng: Ngoài 4 mẫu chuyên dụng Green Series trên, các mẫu xe cá nhân như VF 5 (VF 5 Plus), VF 6, VF 7, VF 8 cũng rất phổ biến được khách hàng và doanh nghiệp mua để chạy dịch vụ/taxi công nghệ (như taxi Xanh SM, GrabCar, BeCar).\n"
        f"3. DÒNG XE THƯƠNG MẠI CHỞ HÀNG / TẢI VAN ĐÔ THỊ (Category: Commercial): {commercial_str}.\n"
        f"4. DÒNG XE BUÝT ĐIỆN VẬN TẢI CÔNG CỘNG B2B (Category: Bus): {bus_str}.\n"
        f"5. DÒNG XE NGHI LỄ / BỌC THÉP CAO CẤP (Category: Luxury): {luxury_str}.\n"
        f"6. DÒNG XE MÁY ĐIỆN ĐANG KINH DOANH: {', '.join(bike_strs)}.\n"
        f"{discontinued_info}"
        "QUY TẮC QUAN TRỌNG VỀ DANH MỤC & GIÁ BÁN:\n"
        "1. Nếu khách hàng hỏi về dòng xe dịch vụ / taxi: BẮT BUỘC liệt kê ĐẦY ĐỦ 4 mẫu xe chuyên dụng Green Series (Minio Green 4 chỗ, Herio Green 5 chỗ, Nerio Green 5 chỗ, Limo Green 7 chỗ), đồng thời có thể tư vấn thêm các mẫu xe cá nhân chạy taxi rất phổ biến như VF 5 (VF 5 Plus).\n"
        "2. Nếu khách hàng hỏi về mẫu xe có is_active=FALSE (đã ngừng sản xuất/bán): LLM phải giải thích rõ mẫu xe này ĐÃ NGỪNG SẢN XUẤT/BÁN trên thị trường, đồng thời khéo léo gợi ý mẫu xe điện mới đang kinh doanh thay thế.\n"
        "3. VinFast KHÔNG CÓ xe lai hybrid, KHÔNG CÓ xe chạy bằng xăng, KHÔNG CÓ xe tải/container.\n"
        "4. VinFast EBus là xe buýt điện cỡ lớn dành cho doanh nghiệp / vận tải công cộng B2B, KHÔNG CÓ giá bán lẻ niêm yết phổ thông (Giá: Liên hệ trực tiếp VinFast). TUYỆT ĐỐI KHÔNG tự bịa ra giá bán lẻ cho EBus và KHÔNG BAO GIỜ gợi ý EBus khi khách hàng tìm mua xe cá nhân/gia đình hoặc tìm xe theo khoảng ngân sách (ví dụ 400-600 triệu)."
    )


import logging

logger = logging.getLogger(__name__)


def _get_cached_raw_cars() -> list[dict[str, Any]]:
    """Fetch or return cached raw car catalog records."""
    now = time.time()
    if "raw_cars" in _CATALOG_CACHE:
        ts, data = _CATALOG_CACHE["raw_cars"]
        if now - ts < CACHE_TTL_SECONDS:
            logger.info("[Catalog Cache HIT] Serving car_catalog from RAM memory cache (%d items, age=%.1fs)", len(data), now - ts)
            return data

    logger.info("[Catalog Cache MISS] Fetching car_catalog from Supabase Cloud REST API")
    url_base = get_supabase_url()
    headers = get_supabase_headers()
    url = f"{url_base}/rest/v1/car_catalog?select=*&order=list_price.asc"

    try:
        res = requests.get(url, headers=headers, timeout=1.5)
        if res.status_code == 200:
            raw_cars = res.json()
            if raw_cars:
                _CATALOG_CACHE["raw_cars"] = (now, raw_cars)
                return raw_cars
    except Exception as e:
        logger.warning("[Catalog Fetch Warning] Supabase REST API error: %s. Using offline fallback.", e)

    _CATALOG_CACHE["raw_cars"] = (now, OFFLINE_CARS_CATALOG)
    return OFFLINE_CARS_CATALOG


def _get_cached_raw_motorbikes() -> list[dict[str, Any]]:
    """Fetch or return cached raw motorbike catalog records."""
    now = time.time()
    if "raw_bikes" in _CATALOG_CACHE:
        ts, data = _CATALOG_CACHE["raw_bikes"]
        if now - ts < CACHE_TTL_SECONDS:
            logger.info("[Catalog Cache HIT] Serving motorbike_catalog from RAM memory cache (%d items, age=%.1fs)", len(data), now - ts)
            return data

    logger.info("[Catalog Cache MISS] Fetching motorbike_catalog from Supabase Cloud REST API")
    url_base = get_supabase_url()
    headers = get_supabase_headers()
    url = f"{url_base}/rest/v1/motorbike_catalog?select=*&order=list_price.asc"

    try:
        res = requests.get(url, headers=headers, timeout=1.5)
        if res.status_code == 200:
            raw_bikes = res.json()
            if raw_bikes:
                _CATALOG_CACHE["raw_bikes"] = (now, raw_bikes)
                return raw_bikes
    except Exception as e:
        logger.warning("[Catalog Fetch Warning] Supabase REST API error: %s. Using offline fallback.", e)

    _CATALOG_CACHE["raw_bikes"] = (now, OFFLINE_MOTORBIKES_CATALOG)
    return OFFLINE_MOTORBIKES_CATALOG


def _normalize_model_key(text: str) -> str:
    """Normalize model code / name for robust fuzzy matching without stripping trim identifiers."""
    if not text:
        return ""
    clean = str(text).lower().replace("vinfast", "").replace("-", "").replace(" ", "")
    return clean


def _normalize_color_value(value: Any) -> str:
    """Normalize color labels for accent/case/spacing-insensitive matching."""
    text = str(value or "").strip().casefold().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(text.replace("-", " ").split())


def _color_values(value: Any) -> list[str]:
    """Extract color values from strings or {name: ...} objects."""
    if isinstance(value, dict):
        values = []
        for key in ("name", "official_name", "color_code", "color", "label"):
            values.extend(_color_values(value.get(key)))
        return values
    if isinstance(value, (list, tuple, set)):
        values: list[str] = []
        for item in value:
            values.extend(_color_values(item))
        return values
    normalized = _normalize_color_value(value)
    return [normalized] if normalized else []


def _matches_requested_colors(vehicle_colors: Any, requested_colors: Any) -> bool:
    """Match a requested color against catalog labels such as 'Đỏ tươi' or 'Đỏ - Đen'."""
    requested = _color_values(requested_colors)
    available = _color_values(vehicle_colors)
    return bool(requested) and any(
        wanted in actual or actual in wanted
        for wanted in requested
        for actual in available
    )


def fetch_cars_from_supabase(
    budget_min: int | None = None,
    budget_max: int | None = None,
    seat_count: int | None = None,
    seat_counts: list[int] | None = None,
    target_model: str | None = None,
    colors: list[str] | str | None = None,
    usage_purpose: str | None = None,
    drivetrain: str | None = None,
    body_type: str | None = None,
    category: str | None = None,
    min_range_km: float | None = None,
    min_power_kw: float | None = None,
    aggregation: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch matching passenger cars from catalog with 0ms in-memory cache."""
    raw_cars = _get_cached_raw_cars()
    formatted = [format_car_record(c) for c in raw_cars]

    if target_model:
        t_str = str(target_model).strip()
        t_low = t_str.lower()
        # 1. Exact canonical match on code, id, or name
        exact_matched = [
            c for c in formatted
            if c["code"].lower() == t_low
            or str(c.get("id", "")).lower() == t_low
            or c["name"].lower() == t_low
        ]
        if exact_matched:
            if colors:
                exact_matched = [c for c in exact_matched if _matches_requested_colors(c.get("colors"), colors)]
            return exact_matched

        # 2. Exact normalized match or safe prefix match
        kw = _normalize_model_key(t_str)
        matched = []
        for c in formatted:
            c_code = _normalize_model_key(c["code"])
            c_name = _normalize_model_key(c["name"])
            if kw == c_code or kw == c_name:
                matched.append(c)
            elif len(kw) >= 4 and (kw in c_code or kw in c_name or (len(c_code) >= 4 and c_code in kw)):
                matched.append(c)
        if colors:
            matched = [c for c in matched if _matches_requested_colors(c.get("colors"), colors)]
        return matched

    formatted = [c for c in formatted if c.get("is_active", True)]

    # For general retail consumer discovery, exclude non-retail, ceremonial, or B2B vehicles
    # (e.g. Lạc Hồng 900 LX, EBus) unless explicitly queried by category
    if not category or category.lower() not in ("bus", "luxury"):
        formatted = [
            c for c in formatted
            if c.get("base_price", 0) > 0
            and c.get("category") not in ("Bus", "Luxury")
            and "ebus" not in c.get("code", "").lower()
            and "lạc hồng" not in c.get("name", "").lower()
        ]

    # Category filter
    if category:
        cat_lower = category.strip().lower()
        formatted = [c for c in formatted if str(c.get("category", "")).lower() == cat_lower]

    # If purpose is personal/family/commute/travel, exclude commercial cargo vans (e.g. EC Van)
    if usage_purpose:
        purpose_str = str(usage_purpose).lower()
        if any(p in purpose_str for p in ("family", "commute", "travel", "gia đình", "đi làm", "du lịch", "cá nhân")):
            formatted = [c for c in formatted if c.get("category") != "Commercial"]

    # Drivetrain filter (AWD, FWD, 2 cầu, 1 cầu)
    if drivetrain:
        dt_low = drivetrain.strip().lower()
        if any(k in dt_low for k in ("awd", "2 cầu", "4 bánh", "hai cầu")):
            formatted = [c for c in formatted if c.get("drivetrain") and any(k in str(c["drivetrain"]).lower() for k in ("awd", "2 cầu", "4 bánh"))]
        elif any(k in dt_low for k in ("fwd", "1 cầu", "cầu trước", "rwd", "cầu sau")):
            formatted = [c for c in formatted if not c.get("drivetrain") or any(k in str(c["drivetrain"]).lower() for k in ("fwd", "1 cầu", "cầu trước", "rwd", "cầu sau"))]

    # Body type filter (SUV, Sedan, MPV, Van, Hatchback)
    if body_type:
        bt_low = body_type.strip().lower()
        formatted = [c for c in formatted if str(c.get("body_type", "")).lower() == bt_low or bt_low in str(c.get("name", "")).lower()]

    # Min range (km)
    if min_range_km:
        formatted = [c for c in formatted if (c.get("range_km") or 0) >= min_range_km]

    # Min power (kW)
    if min_power_kw:
        formatted = [c for c in formatted if (c.get("power_kw") or 0) >= min_power_kw]

    # Budget filter
    if budget_min and budget_min > 0:
        formatted = [c for c in formatted if c.get("base_price", 0) >= int(budget_min * 0.85)]

    if budget_max and budget_max > 0:
        formatted = [c for c in formatted if c.get("base_price", 0) <= int(budget_max * 1.15)]

    # Seat count filter (supports single seat_count or multiple seat_counts like [4, 7])
    valid_seats = set()
    if seat_counts:
        valid_seats.update(int(s) for s in seat_counts if s is not None)
    elif seat_count is not None:
        valid_seats.add(int(seat_count))

    if valid_seats:
        formatted = [c for c in formatted if c.get("seats") in valid_seats]

    if colors:
        formatted = [c for c in formatted if _matches_requested_colors(c.get("colors"), colors)]

    # Aggregation sort
    if aggregation:
        agg = aggregation.lower().strip()
        if agg in ("most_expensive", "highest_price", "dat_nhat", "max_price"):
            formatted.sort(key=lambda x: x.get("base_price", 0), reverse=True)
        elif agg in ("cheapest", "lowest_price", "re_nhat", "min_price"):
            valid = [x for x in formatted if x.get("base_price", 0) > 0]
            zero_price = [x for x in formatted if x.get("base_price", 0) <= 0]
            valid.sort(key=lambda x: x.get("base_price", 0))
            formatted = valid + zero_price
        elif agg in ("longest_range", "xa_nhat", "pin_trau_nhat", "max_range"):
            formatted.sort(key=lambda x: x.get("range_km") or 0, reverse=True)
        elif agg in ("most_powerful", "manh_nhat", "max_power"):
            formatted.sort(key=lambda x: x.get("power_kw") or 0, reverse=True)
        elif agg in ("largest_trunk", "cop_rong_nhat", "cop_to_nhat", "max_trunk"):
            formatted.sort(
                key=lambda x: (
                    x.get("trunk_liters")
                    or x.get("specs", {}).get("trunk_capacity_liters")
                    or x.get("additional_specs", {}).get("trunk_capacity_liters")
                    or 0
                ),
                reverse=True,
            )

    return formatted


def get_fallback_recommendations(
    seat_count: int | None = None,
    seat_counts: list[int] | None = None,
    budget_max: int | None = None,
    category: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Provides nearest-match alternative recommendations when 0 cars match exact criteria.
    Two-Fork Pivot:
    1. same_budget_cars: cars within budget_max (highest seating capacity or best selling first)
    2. same_seats_cars: cars matching requested seat_count(s) with lowest base price
    """
    raw_cars = _get_cached_raw_cars()
    formatted = [format_car_record(c) for c in raw_cars]
    # Filter active retail vehicles
    formatted = [
        c for c in formatted
        if c.get("is_active", True)
        and c.get("base_price", 0) > 0
        and c.get("category") not in ("Bus", "Luxury")
        and "ebus" not in c.get("code", "").lower()
        and "lạc hồng" not in c.get("name", "").lower()
    ]
    if category:
        cat_low = category.strip().lower()
        formatted_cat = [c for c in formatted if str(c.get("category", "")).lower() == cat_low]
        if formatted_cat:
            formatted = formatted_cat

    same_budget_cars = []
    if budget_max and budget_max > 0:
        budget_matched = [c for c in formatted if c.get("base_price", 0) <= int(budget_max * 1.15)]
        # Sort by seat count descending then price descending to get the most spacious within budget
        budget_matched.sort(key=lambda x: (x.get("seats") or 0, x.get("base_price") or 0), reverse=True)
        # Deduplicate by line
        seen_lines = set()
        for c in budget_matched:
            name_low = c.get("name", "").lower()
            key = c.get("code", "").split("-")[0]
            for p in ("vf 3", "vf 5", "vf 6", "vf 7", "vf 8", "vf 9", "minio", "herio", "nerio", "limo"):
                if p in name_low:
                    key = p
                    break
            if key not in seen_lines:
                seen_lines.add(key)
                same_budget_cars.append(c)
            if len(same_budget_cars) >= 3:
                break

    same_seats_cars = []
    target_seats = set()
    if seat_counts:
        target_seats.update(int(s) for s in seat_counts if s is not None)
    elif seat_count is not None:
        target_seats.add(int(seat_count))

    if target_seats:
        seat_matched = [c for c in formatted if c.get("seats") in target_seats]
        # Sort by price ascending (cheapest first)
        seat_matched.sort(key=lambda x: x.get("base_price", 0))
        seen_lines = set()
        for c in seat_matched:
            name_low = c.get("name", "").lower()
            key = c.get("code", "").split("-")[0]
            for p in ("vf 3", "vf 5", "vf 6", "vf 7", "vf 8", "vf 9", "vf mpv 7", "minio", "herio", "nerio", "limo"):
                if p in name_low:
                    key = p
                    break
            if key not in seen_lines:
                seen_lines.add(key)
                same_seats_cars.append(c)
            if len(same_seats_cars) >= 3:
                break

    return {
        "same_budget_cars": same_budget_cars,
        "same_seats_cars": same_seats_cars,
    }


def fetch_cars_for_models(model_names: list[str], colors: list[str] | str | None = None) -> list[dict[str, Any]]:
    """Fetch exact matching passenger cars for a list of target model names or codes."""
    raw_cars = _get_cached_raw_cars()
    formatted = [format_car_record(c) for c in raw_cars]
    results = []
    seen = set()
    for name in model_names:
        name_str = str(name).strip()
        name_lower = name_str.lower()
        matched_car = None

        # 1. Exact canonical code, id, or full name match
        for c in formatted:
            if c["code"] in seen:
                continue
            if c["code"].lower() == name_lower or str(c.get("id", "")).lower() == name_lower or c["name"].lower() == name_lower:
                matched_car = c
                break

        # 2. Exact normalized match
        if not matched_car:
            kw = _normalize_model_key(name_str)
            for c in formatted:
                if c["code"] in seen:
                    continue
                c_code = _normalize_model_key(c["code"])
                c_name = _normalize_model_key(c["name"])
                if kw == c_code or kw == c_name:
                    matched_car = c
                    break

        # 3. Safe substring match (len >= 4 to avoid single character/digit matching like '7')
        if not matched_car:
            kw = _normalize_model_key(name_str)
            if len(kw) >= 4:
                for c in formatted:
                    if c["code"] in seen:
                        continue
                    c_code = _normalize_model_key(c["code"])
                    c_name = _normalize_model_key(c["name"])
                    if kw in c_code or kw in c_name or (len(c_code) >= 4 and c_code in kw) or (len(c_name) >= 4 and c_name in kw):
                        matched_car = c
                        break

        if matched_car:
            if not colors or _matches_requested_colors(matched_car.get("colors"), colors):
                results.append(matched_car)
            seen.add(matched_car["code"])

    return results


def fetch_motorbikes_for_models(model_names: list[str], colors: list[str] | str | None = None) -> list[dict[str, Any]]:
    """Fetch exact matching motorbikes for a list of target model names or codes."""
    raw_bikes = _get_cached_raw_motorbikes()
    formatted = [format_motorbike_record(b) for b in raw_bikes]
    results = []
    seen = set()
    for name in model_names:
        name_str = str(name).strip()
        name_lower = name_str.lower()
        matched_bike = None

        # 1. Exact canonical code, id, or full name match
        for b in formatted:
            if b["code"] in seen:
                continue
            if b["code"].lower() == name_lower or str(b.get("id", "")).lower() == name_lower or b["name"].lower() == name_lower:
                matched_bike = b
                break

        # 2. Exact normalized match
        if not matched_bike:
            kw = _normalize_model_key(name_str)
            for b in formatted:
                if b["code"] in seen:
                    continue
                b_code = _normalize_model_key(b["code"])
                b_name = _normalize_model_key(b["name"])
                if kw == b_code or kw == b_name:
                    matched_bike = b
                    break

        # 3. Safe substring match
        if not matched_bike:
            kw = _normalize_model_key(name_str)
            if len(kw) >= 4:
                for b in formatted:
                    if b["code"] in seen:
                        continue
                    b_code = _normalize_model_key(b["code"])
                    b_name = _normalize_model_key(b["name"])
                    if kw in b_code or kw in b_name or (len(b_code) >= 4 and b_code in kw) or (len(b_name) >= 4 and b_name in kw):
                        matched_bike = b
                        break

        if matched_bike:
            if not colors or _matches_requested_colors(matched_bike.get("colors"), colors):
                results.append(matched_bike)
            seen.add(matched_bike["code"])

    return results


def fetch_motorbikes_from_supabase(
    budget_min: int | None = None,
    budget_max: int | None = None,
    target_model: str | None = None,
    colors: list[str] | str | None = None,
    aggregation: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch matching motorbikes from catalog with 0ms in-memory cache."""
    raw_bikes = _get_cached_raw_motorbikes()
    formatted = [format_motorbike_record(b) for b in raw_bikes]

    if target_model:
        t_str = str(target_model).strip()
        t_low = t_str.lower()
        # 1. Exact canonical match on code, id, or name
        exact_matched = [
            b for b in formatted
            if b["code"].lower() == t_low
            or str(b.get("id", "")).lower() == t_low
            or b["name"].lower() == t_low
        ]
        if exact_matched:
            if colors:
                exact_matched = [b for b in exact_matched if _matches_requested_colors(b.get("colors"), colors)]
            return exact_matched

        # 2. Exact normalized match or safe prefix match
        kw = _normalize_model_key(t_str)
        matched = []
        for b in formatted:
            b_code = _normalize_model_key(b["code"])
            b_name = _normalize_model_key(b["name"])
            if kw == b_code or kw == b_name:
                matched.append(b)
            elif len(kw) >= 4 and (kw in b_code or kw in b_name or (len(b_code) >= 4 and b_code in kw)):
                matched.append(b)
        if colors:
            matched = [b for b in matched if _matches_requested_colors(b.get("colors"), colors)]
        return matched

    formatted = [b for b in formatted if b.get("is_active", True)]

    if budget_min and budget_min > 0:
        formatted = [b for b in formatted if b.get("base_price", 0) >= int(budget_min * 0.85)]

    if budget_max and budget_max > 0:
        formatted = [b for b in formatted if b.get("base_price", 0) <= int(budget_max * 1.15)]

    if colors:
        formatted = [b for b in formatted if _matches_requested_colors(b.get("colors"), colors)]

    if aggregation:
        agg = aggregation.lower().strip()
        if agg in ("most_expensive", "highest_price", "dat_nhat", "max_price"):
            formatted.sort(key=lambda x: x.get("base_price", 0), reverse=True)
        elif agg in ("cheapest", "lowest_price", "re_nhat", "min_price"):
            valid = [x for x in formatted if x.get("base_price", 0) > 0]
            zero_price = [x for x in formatted if x.get("base_price", 0) <= 0]
            valid.sort(key=lambda x: x.get("base_price", 0))
            formatted = valid + zero_price
        elif agg in ("longest_range", "xa_nhat", "pin_trau_nhat", "max_range"):
            formatted.sort(key=lambda x: x.get("range_km") or x.get("range_per_charge_km") or 0, reverse=True)
        elif agg in ("most_powerful", "manh_nhat", "max_power"):
            formatted.sort(key=lambda x: x.get("power_w") or x.get("specs", {}).get("maximum_power_w") or 0, reverse=True)
        elif agg in ("largest_trunk", "cop_rong_nhat", "cop_to_nhat", "max_trunk"):
            formatted.sort(key=lambda x: x.get("specs", {}).get("underseat_storage_liters") or 0, reverse=True)

    return formatted

OFFLINE_CARS_CATALOG = [
    {"model_code": "vf-2-tiêu-chuẩn", "model_name": "VinFast VF 2 Tiêu chuẩn", "seat_count": 4, "list_price": 188_000_000, "range_km": 210.0, "usable_battery_capacity": 18.3, "category": "Personal", "is_active": True},
    {"model_code": "ec-van-tiêu-chuẩn", "model_name": "VinFast EC Van Tiêu chuẩn", "seat_count": 2, "list_price": 268_000_000, "range_km": 175.0, "usable_battery_capacity": 18.3, "category": "Commercial", "is_active": True},
    {"model_code": "minio-green", "model_name": "VinFast Minio Green", "seat_count": 4, "list_price": 269_000_000, "range_km": 210.0, "usable_battery_capacity": 18.3, "category": "Service", "is_active": True},
    {"model_code": "vf-3-eco", "model_name": "VinFast VF 3 Eco", "seat_count": 4, "list_price": 285_000_000, "range_km": 215.0, "usable_battery_capacity": 18.64, "category": "Personal", "is_active": True},
    {"model_code": "vf-3-plus", "model_name": "VinFast VF 3 Plus", "seat_count": 4, "list_price": 296_000_000, "range_km": 215.0, "usable_battery_capacity": 18.64, "category": "Personal", "is_active": True},
    {"model_code": "vf-5", "model_name": "VinFast VF 5", "seat_count": 5, "list_price": 496_000_000, "range_km": 326.4, "usable_battery_capacity": 37.23, "category": "Personal", "is_active": True},
    {"model_code": "herio-green", "model_name": "VinFast Herio Green", "seat_count": 5, "list_price": 499_000_000, "range_km": 326.0, "usable_battery_capacity": 37.23, "category": "Service", "is_active": True},
    {"model_code": "vf-6-eco", "model_name": "VinFast VF 6 Eco", "seat_count": 5, "list_price": 646_000_000, "range_km": 485.0, "usable_battery_capacity": 59.6, "category": "Personal", "is_active": True},
    {"model_code": "nerio-green", "model_name": "VinFast Nerio Green", "seat_count": 5, "list_price": 668_000_000, "range_km": 318.6, "usable_battery_capacity": 41.9, "category": "Service", "is_active": True},
    {"model_code": "limo-green", "model_name": "VinFast Limo Green", "seat_count": 7, "list_price": 699_000_000, "range_km": 450.0, "usable_battery_capacity": 60.13, "category": "Service", "is_active": True},
    {"model_code": "vf-6-plus", "model_name": "VinFast VF 6 Plus", "seat_count": 5, "list_price": 699_000_000, "range_km": 460.0, "usable_battery_capacity": 59.6, "category": "Personal", "is_active": True},
    {"model_code": "vf-7-eco", "model_name": "VinFast VF 7 Eco", "seat_count": 5, "list_price": 740_000_000, "range_km": 440.0, "usable_battery_capacity": 59.6, "category": "Personal", "is_active": True},
    {"model_code": "vf-mpv-7-tiêu-chuẩn-gia-đình", "model_name": "VinFast VF MPV 7 Tiêu chuẩn gia đình", "seat_count": 7, "list_price": 819_000_000, "range_km": 450.0, "usable_battery_capacity": 60.13, "category": "Personal", "is_active": True},
    {"model_code": "vf-7-plus-awd---trần-thép", "model_name": "VinFast VF 7 Plus AWD - Trần thép", "seat_count": 5, "list_price": 830_000_000, "range_km": 500.5, "usable_battery_capacity": 70.0, "category": "Personal", "is_active": True},
    {"model_code": "vf-7-plus-awd---trần-kính-toàn-cảnh", "model_name": "VinFast VF 7 Plus AWD - Trần kính toàn cảnh", "seat_count": 5, "list_price": 850_000_000, "range_km": 500.5, "usable_battery_capacity": 70.0, "category": "Personal", "is_active": True},
    {"model_code": "vf-8-eco", "model_name": "VinFast VF 8 Eco", "seat_count": 5, "list_price": 898_000_000, "range_km": 562.0, "usable_battery_capacity": 87.7, "category": "Personal", "is_active": True},
    {"model_code": "vf-8-the-all-new", "model_name": "VinFast VF 8 The All New", "seat_count": 5, "list_price": 999_000_000, "range_km": 490.0, "usable_battery_capacity": 60.13, "category": "Personal", "is_active": True},
    {"model_code": "vf-8-plus", "model_name": "VinFast VF 8 Plus", "seat_count": 5, "list_price": 1_079_000_000, "range_km": 457.0, "usable_battery_capacity": 87.7, "category": "Personal", "is_active": True},
    {"model_code": "vf-9-eco", "model_name": "VinFast VF 9 Eco", "seat_count": 7, "list_price": 1_348_000_000, "range_km": 626.0, "usable_battery_capacity": 123.0, "category": "Personal", "is_active": True},
    {"model_code": "vf-9-plus", "model_name": "VinFast VF 9 Plus", "seat_count": 7, "list_price": 1_529_000_000, "range_km": 602.0, "usable_battery_capacity": 123.0, "category": "Personal", "is_active": True},
    {"model_code": "ebus", "model_name": "VinFast EBus", "seat_count": 30, "list_price": 0, "range_km": 260.0, "usable_battery_capacity": 281.0, "category": "Bus", "is_active": True},
    {"model_code": "lạc-hồng-900-lx", "model_name": "VinFast Lạc Hồng 900 LX", "seat_count": 4, "list_price": 0, "range_km": 450.0, "usable_battery_capacity": 123.0, "category": "Luxury", "is_active": True},
    {"model_code": "lux-a2.0-tiêu-chuẩn", "model_name": "VinFast Lux A2.0 Tiêu Chuẩn", "seat_count": 5, "list_price": 1_115_000_000, "range_km": None, "usable_battery_capacity": None, "category": "Personal", "is_active": False},
    {"model_code": "lux-a2.0-cao-cấp", "model_name": "VinFast Lux A2.0 Cao Cấp (Premium)", "seat_count": 5, "list_price": 1_358_000_000, "range_km": None, "usable_battery_capacity": None, "category": "Personal", "is_active": False},
    {"model_code": "lux-sa2.0-tiêu-chuẩn", "model_name": "VinFast Lux SA2.0 Tiêu Chuẩn", "seat_count": 7, "list_price": 1_552_000_000, "range_km": None, "usable_battery_capacity": None, "category": "Personal", "is_active": False},
    {"model_code": "president-v8", "model_name": "VinFast President V8 Limited", "seat_count": 7, "list_price": 4_600_000_000, "range_km": None, "usable_battery_capacity": None, "category": "Personal", "is_active": False},
]

OFFLINE_MOTORBIKES_CATALOG = [
    {"model_code": "amio", "model_name": "VinFast Amio Tiêu chuẩn", "list_price": 11_600_000, "range_km": 65, "is_active": True},
    {"model_code": "amio-s", "model_name": "VinFast Amio S", "list_price": 11_600_000, "range_km": 65, "is_active": True},
    {"model_code": "amio-s2", "model_name": "VinFast Amio S2", "list_price": 12_000_000, "range_km": 65, "is_active": True},
    {"model_code": "zgoo", "model_name": "VinFast ZGoo Tiêu chuẩn", "list_price": 13_300_000, "range_km": 70, "is_active": True},
    {"model_code": "evo-lite-neo", "model_name": "VinFast Evo Lite Neo Kèm ắc quy", "list_price": 14_400_000, "range_km": 78, "is_active": True},
    {"model_code": "flazz", "model_name": "VinFast Flazz Tiêu chuẩn", "list_price": 16_000_000, "range_km": 135, "is_active": True},
    {"model_code": "flazz-max", "model_name": "VinFast Flazz Max", "list_price": 17_300_000, "range_km": 87, "is_active": True},
    {"model_code": "vf-drgnfly", "model_name": "VinFast VF DrgnFly eBike", "list_price": 18_690_000, "range_km": 110, "is_active": True},
    {"model_code": "evo-lite", "model_name": "VinFast Evo Lite Kèm pin", "list_price": 18_900_000, "range_km": 165, "is_active": True},
    {"model_code": "evo-grand-lite", "model_name": "VinFast Evo Grand Lite Kèm pin", "list_price": 19_900_000, "range_km": 198, "is_active": True},
    {"model_code": "evo-grand", "model_name": "VinFast Evo Grand Kèm pin", "list_price": 22_500_000, "range_km": 262, "is_active": True},
    {"model_code": "evo", "model_name": "VinFast Evo Kèm pin", "list_price": 24_100_000, "range_km": 165, "is_active": True},
    {"model_code": "feliz-2025", "model_name": "VinFast Feliz 2025 Kèm pin", "list_price": 27_900_000, "range_km": 262, "is_active": True},
    {"model_code": "feliz-ii", "model_name": "VinFast Feliz II Kèm pin", "list_price": 28_700_000, "range_km": 156, "is_active": True},
    {"model_code": "vero-x", "model_name": "VinFast Vero X Tiêu chuẩn", "list_price": 34_900_000, "range_km": 262, "is_active": True},
    {"model_code": "kyo", "model_name": "VinFast Kyo Kèm pin", "list_price": 35_300_000, "range_km": 160, "is_active": True},
    {"model_code": "viper", "model_name": "VinFast Viper Kèm pin", "list_price": 45_500_000, "range_km": 156, "is_active": True},
    {"model_code": "kinet", "model_name": "VinFast Kinet Kèm pin", "list_price": 49_900_000, "range_km": 145, "is_active": True},
    {"model_code": "ludo", "model_name": "VinFast Ludo", "list_price": 12_900_000, "range_km": 75, "is_active": False},
    {"model_code": "impes", "model_name": "VinFast Impes", "list_price": 14_900_000, "range_km": 70, "is_active": False},
    {"model_code": "tempest", "model_name": "VinFast Tempest", "list_price": 19_250_000, "range_km": 80, "is_active": False},
    {"model_code": "klara-a1", "model_name": "VinFast Klara A1 (Pin Lithium V1)", "list_price": 39_900_000, "range_km": 80, "is_active": False},
]


def format_car_record(r: dict[str, Any]) -> dict[str, Any]:
    """Format car database record with full column passthrough and normalized aliases."""
    car_id = str(r.get("id") or r.get("car_id") or "")
    raw_code = r.get("model_code") or r.get("code")
    if not raw_code and r.get("model_name"):
        name_lower = str(r["model_name"]).lower().replace("vinfast", "").strip()
        raw_code = name_lower.replace(" ", "-")

    price_val = r.get("list_price") or r.get("base_price") or 0
    if raw_code and "ebus" in str(raw_code).lower():
        price_val = 0

    raw_specs = dict(r.get("additional_specs") or r.get("specs") or {})
    colors = r.get("colors")
    if not colors and isinstance(raw_specs, dict):
        colors = raw_specs.get("colors")

    code_clean = raw_code or (str(car_id) if car_id else "unknown-car")
    target_id = car_id or code_clean

    # Drivetrain extraction (AWD, FWD, 2 cầu, 1 cầu)
    drivetrain = (
        r.get("drivetrain")
        or raw_specs.get("drivetrain")
        or ("AWD" if "-awd" in code_clean or "awd" in str(r.get("model_name", "")).lower() else None)
    )

    # Battery capacity (kWh)
    battery_kwh = (
        r.get("usable_battery_capacity")
        or r.get("usable_battery_capacity_kwh")
        or r.get("battery_capacity_kwh")
        or r.get("battery_kwh")
        or raw_specs.get("usable_battery_capacity")
    )

    # Airbags
    airbags = None
    if "safety_features" in raw_specs and isinstance(raw_specs["safety_features"], dict):
        airbags = raw_specs["safety_features"].get("airbags")
    if airbags is None:
        airbags = raw_specs.get("airbags")

    # ADAS
    adas = None
    if "technology_features" in raw_specs and isinstance(raw_specs["technology_features"], dict):
        adas = raw_specs["technology_features"].get("adas")
    if not adas:
        adas = raw_specs.get("adas")

    # Trunk capacity (liters)
    trunk_liters = raw_specs.get("trunk_capacity_liters") or raw_specs.get("cargo_capacity_liters")

    # Ground clearance (mm)
    ground_clearance_mm = raw_specs.get("ground_clearance_mm")

    # Body type / segment
    body_type = r.get("body_type") or raw_specs.get("body_type")
    if not body_type:
        name_lower = str(r.get("model_name", "")).lower()
        if "mpv" in name_lower or "mpv" in code_clean:
            body_type = "MPV"
        elif "van" in name_lower or "van" in code_clean:
            body_type = "Van"
        elif "ebus" in name_lower or "ebus" in code_clean:
            body_type = "Bus"
        elif any(k in name_lower for k in ("lux a", "sedan")):
            body_type = "Sedan"
        elif any(k in name_lower for k in ("fadil", "hatchback")):
            body_type = "Hatchback"
        elif "vf" in name_lower:
            body_type = "SUV"

    return {
        **r,  # Passthrough all original columns from DB
        "id": target_id,
        "code": code_clean,
        "name": r.get("model_name") or r.get("name") or (str(car_id) if car_id else "Xe VinFast"),
        "category": r.get("category") or "Personal",
        "body_type": body_type,
        "colors": colors or [],
        "seats": r.get("seat_count") or r.get("seats") or 5,
        "base_price": int(price_val) if price_val else 0,
        "battery_buy_price": r.get("battery_buy_price"),
        "rent_monthly": r.get("battery_rent_monthly") or r.get("rent_monthly") or 1_200_000,
        "range_km": r.get("range_km") or r.get("range_per_charge_km") or 326,
        "power_kw": r.get("maximum_power_kw") or r.get("power_kw"),
        "torque_nm": r.get("maximum_torque_nm") or r.get("torque_nm"),
        "battery_kwh": battery_kwh,
        "drivetrain": drivetrain,
        "airbags": airbags,
        "adas": adas,
        "trunk_liters": trunk_liters,
        "ground_clearance_mm": ground_clearance_mm,
        "length_mm": r.get("length_mm"),
        "width_mm": r.get("width_mm"),
        "height_mm": r.get("height_mm"),
        "wheelbase_mm": r.get("wheelbase_mm"),
        "dimensions": {
            "length_mm": r.get("length_mm"),
            "width_mm": r.get("width_mm"),
            "height_mm": r.get("height_mm"),
            "wheelbase_mm": r.get("wheelbase_mm"),
        },
        "specs": raw_specs,
        "additional_specs": raw_specs,
        "detail_url": f"/#detail-{target_id}",
        "is_active": bool(r.get("is_active")) if r.get("is_active") is not None else True,
    }


def format_motorbike_record(r: dict[str, Any]) -> dict[str, Any]:
    """Format motorbike database record with full column passthrough."""
    bike_id = str(r.get("id") or r.get("motorbike_id") or "")
    price_val = r.get("list_price") or r.get("base_price") or 0
    raw_code = r.get("model_code") or r.get("code")
    if not raw_code and r.get("vehicle_line"):
        v_line = str(r["vehicle_line"]).strip().lower().replace("vinfast", "").strip()
        raw_code = v_line.replace(" ", "-")
    elif not raw_code and r.get("model_name"):
        name_lower = str(r["model_name"]).lower().replace("vinfast", "").strip()
        raw_code = name_lower.replace(" ", "-")
    code_clean = raw_code or "feliz-s"
    target_id = bike_id or code_clean

    combined_specs = dict(r.get("additional_specs") or r.get("specs") or {})
    colors = r.get("colors")
    if not colors and isinstance(r.get("additional_specs"), dict):
        colors = r["additional_specs"].get("colors")
    for k in (
        "maximum_power_w", "maximum_speed_kmh", "battery_type", "battery_capacity_kwh",
        "motor_type", "weight_kg", "length_mm", "width_mm", "height_mm",
        "front_brake", "rear_brake", "front_suspension", "rear_suspension",
        "underseat_storage_liters", "charging_time_minutes"
    ):
        if r.get(k) is not None and k not in combined_specs:
            combined_specs[k] = r[k]

    return {
        **r,  # Passthrough all original columns from DB
        "id": target_id,
        "code": code_clean,
        "name": r.get("model_name") or r.get("name") or "VinFast Feliz S",
        "version": r.get("version"),
        "vehicle_line": r.get("vehicle_line"),
        "category": r.get("category") or "Scooter",
        "colors": colors or [],
        "base_price": int(price_val) if price_val else 0,
        "battery_buy_price": r.get("battery_buy_price"),
        "rent_monthly": r.get("battery_rent_monthly") or r.get("rent_monthly") or 350_000,
        "range_km": r.get("range_per_charge_km") or r.get("range_km") or 198,
        "power_w": r.get("maximum_power_w") or combined_specs.get("maximum_power_w"),
        "max_speed_kmh": r.get("maximum_speed_kmh") or combined_specs.get("maximum_speed_kmh"),
        "charging_time_minutes": r.get("charging_time_minutes") or combined_specs.get("charging_time_minutes"),
        "specs": combined_specs,
        "additional_specs": combined_specs,
        "detail_url": f"/#detail-{target_id}",
        "is_active": bool(r.get("is_active")) if r.get("is_active") is not None else True,
    }


def get_supabase_headers(schema: str = "public") -> dict[str, str]:
    """Get Supabase REST API headers with schema selection."""
    key = settings.supabase_key.strip()
    if not key:
        raise RuntimeError("SUPABASE_KEY is not configured")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept-Profile": schema,
        "Content-Profile": schema,
    }


def get_supabase_url() -> str:
    """Get base Supabase URL."""
    url = settings.supabase_url.strip()
    if not url:
        raise RuntimeError("SUPABASE_URL is not configured")
    return url.rstrip("/")

