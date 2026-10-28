"""Pure, deterministic total-cost-of-ownership calculator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

VehicleTypeCode = Literal["CAR", "MOTORBIKE"]
ProvinceCode = Literal["HN", "HCM", "OTHER"]
BatteryOption = Literal["RENTAL", "BUY"]


# Tham số đầu vào cho phép tính TCO: mẫu xe, khu vực đăng ký, phương án pin,
# quãng đường sử dụng và các giá trị giá tùy chọn để ghi đè baseline.
@dataclass(frozen=True)
class TCOCalculationRequest:
    model_id: str  # e.g., "vf3", "vf-5", "theon-s"
    vehicle_type: VehicleTypeCode = "CAR"
    variant_id: str | None = None
    province_code: ProvinceCode = "OTHER"
    battery_option: BatteryOption = "RENTAL"
    monthly_km_estimate: int = 1000
    base_price_override: int | None = None
    battery_buy_price_override: int | None = None
    battery_rent_monthly_override: int | None = None
    seat_count: int = 5


# Chi tiết các khoản phí ban đầu cần trả để xe đủ điều kiện lưu thông.
@dataclass(frozen=True)
class RollingCostBreakdown:
    plate_fee_vnd: int
    road_maintenance_fee_vnd: int
    civil_insurance_vnd: int
    total_rolling_cost_vnd: int
    registration_fee_vnd: int = 0  # 0 VND for EV in Vietnam


# Chi phí sử dụng ước tính mỗi tháng, tách phí pin, sạc điện và bảo dưỡng.
@dataclass(frozen=True)
class MonthlyOperatingCost:
    battery_subscription_fee_vnd: int
    charging_electricity_cost_vnd: int
    estimated_maintenance_vnd: int
    total_monthly_cost_vnd: int


# Kết quả tổng hợp gửi cho client, gồm chi phí lăn bánh và vận hành tháng.
@dataclass(frozen=True)
class TCOCalculationResponse:
    vehicle_type: str
    model_id: str
    province_code: str
    battery_option: str
    monthly_km_estimate: int
    list_price_vnd: int
    rolling_cost_breakdown: RollingCostBreakdown
    monthly_operating_cost: MonthlyOperatingCost
    disclaimer_text: str
    comparison_summary: dict[str, Any] | None = field(default=None)


DISCLAIMER_TEXT = "Mọi con số mang tính chất ước tính, vui lòng xác nhận báo giá chính thức với Tư vấn viên."
PUBLIC_CHARGING_RATE_VND_PER_KWH = 3858

# Bảng giá mặc định để tính toán độc lập với database và web framework.
# API có thể truyền giá override để dùng giá cập nhật từ catalog.
# Các mức này chỉ là baseline ước tính, dùng khi request/catalog không cung cấp giá.
TCO_BASELINES: dict[str, dict[str, Any]] = {
    "vf3": {"code": "vf3", "base_price": 240_000_000, "battery_buy_price": 322_000_000, "seats": 4},
    "vf5": {"code": "vf5", "base_price": 496_000_000, "battery_buy_price": 548_000_000, "seats": 5},
    "vf6": {"code": "vf6", "base_price": 675_000_000, "seats": 5},
    "vf7": {"code": "vf7", "base_price": 850_000_000, "seats": 5},
    "vf8": {"code": "vf8", "base_price": 1_019_000_000, "seats": 5},
    "vf9": {"code": "vf9", "base_price": 1_499_000_000, "seats": 7},
    "limogreen": {"code": "limo-green", "base_price": 699_000_000, "seats": 7},
    "felizs": {"code": "feliz-s", "base_price": 30_000_000, "seats": 2, "vehicle_type": "MOTORBIKE"},
    "theons": {"code": "theon-s", "base_price": 63_000_000, "seats": 2, "vehicle_type": "MOTORBIKE"},
}


# Chuẩn hóa mã xe rồi tìm cấu hình baseline; cờ thứ hai cho biết xe có phải ô tô.
def _find_vehicle_in_catalog(
    model_id: str,
    variant_id: str | None = None,
) -> tuple[dict[str, Any] | None, bool]:
    del variant_id
    # Chuẩn hóa mã xe để tra cứu không phụ thuộc chữ hoa, dấu cách hay dấu gạch.
    normalized = "".join(character for character in str(model_id).lower() if character.isalnum())
    vehicle = TCO_BASELINES.get(normalized)
    if vehicle is None:
        return None, True
    return vehicle, vehicle.get("vehicle_type", "CAR") == "CAR"


# Tính giá ban đầu và chi phí vận hành định kỳ theo thông tin xe và giả định đầu vào.
def calculate_tco(req: TCOCalculationRequest) -> TCOCalculationResponse:
    """Calculate deterministic rolling and monthly operating costs."""
    vehicle, is_car = _find_vehicle_in_catalog(req.model_id, req.variant_id)

    # Ưu tiên thông tin xe trong bảng baseline; nếu không có thì dùng dữ liệu request.
    # Giá override được ưu tiên hơn giá baseline; giá và số ghế mặc định dùng khi thiếu dữ liệu.
    if vehicle:
        v_type = "CAR" if is_car else "MOTORBIKE"
        v_code = str(vehicle.get("code") or "").lower()
        base_price = req.base_price_override or vehicle.get("base_price") or vehicle.get("list_price") or (500_000_000 if v_type == "CAR" else 30_000_000)
        seats = vehicle.get("seats") or req.seat_count
    else:
        v_type = req.vehicle_type
        v_code = str(req.model_id).lower().strip()
        base_price = req.base_price_override or (500_000_000 if v_type == "CAR" else 30_000_000)
        seats = req.seat_count

    # Giá mua pin ưu tiên override, sau đó đến giá catalog và cuối cùng là mức ước tính.
    # Với xe chưa có giá pin trong catalog, suy ra mức giá dựa trên dòng xe hoặc loại phương tiện.
    if req.battery_buy_price_override:
        battery_buy_price = req.battery_buy_price_override
    elif vehicle and vehicle.get("battery_buy_price"):
        battery_buy_price = int(vehicle["battery_buy_price"])
    else:
        if any(k in v_code for k in ("vf-3", "vf3")):
            battery_buy_price = 322_000_000
        elif any(k in v_code for k in ("vf-5", "vf5")):
            battery_buy_price = 548_000_000
        elif any(k in v_code for k in ("vf-6", "vf6", "herio")):
            battery_buy_price = base_price + 90_000_000
        elif any(k in v_code for k in ("vf-7", "vf7", "nerio")):
            battery_buy_price = base_price + 149_000_000
        elif any(k in v_code for k in ("vf-8", "vf8")):
            battery_buy_price = base_price + 200_000_000
        elif any(k in v_code for k in ("vf-9", "vf9", "limo")):
            battery_buy_price = base_price + 493_000_000
        elif v_type == "CAR":
            battery_buy_price = base_price + 100_000_000
        else:
            battery_buy_price = base_price + 19_000_000

    # Phí thuê pin cũng ưu tiên override; các mức còn lại là baseline theo dòng xe.
    # Nhánh cuối cùng cung cấp mức mặc định theo loại xe khi không khớp dòng xe cụ thể.
    if req.battery_rent_monthly_override:
        battery_rent_monthly = req.battery_rent_monthly_override
    elif vehicle and vehicle.get("battery_rent_monthly"):
        battery_rent_monthly = int(vehicle["battery_rent_monthly"])
    else:
        if any(k in v_code for k in ("vf-5", "vf5")):
            battery_rent_monthly = 1_600_000
        elif any(k in v_code for k in ("vf-3", "vf3", "vf-2", "minio", "ec-van")):
            battery_rent_monthly = 900_000
        elif any(k in v_code for k in ("vf-6", "vf6", "herio", "nerio")):
            battery_rent_monthly = 1_800_000
        elif any(k in v_code for k in ("vf-7", "vf7")):
            battery_rent_monthly = 2_100_000
        elif any(k in v_code for k in ("vf-8", "vf8")):
            battery_rent_monthly = 2_900_000
        elif any(k in v_code for k in ("vf-9", "vf9", "limo")):
            battery_rent_monthly = 4_200_000
        elif v_type == "CAR":
            battery_rent_monthly = 1_800_000
        else:
            battery_rent_monthly = 350_000

    # Giá niêm yết dùng để tính chi phí ban đầu phụ thuộc khách hàng mua hay thuê pin.
    if req.battery_option == "BUY":
        list_price = battery_buy_price
    else:
        list_price = base_price

    # 1. Phí lăn bánh: giá xe/pin cộng lệ phí trước bạ, biển số, bảo trì đường bộ và bảo hiểm.
    # Lệ phí trước bạ được đặt bằng 0 theo giả định xe điện đang áp dụng trong phép tính này.
    registration_fee = 0  # 0% for EV in VN

    # Các khoản đăng ký và bảo hiểm được chọn theo loại phương tiện, địa phương và số chỗ.
    if v_type == "CAR":
        # Phí biển số phân biệt Hà Nội/TP.HCM với các tỉnh thành khác.
        if req.province_code in ["HN", "HCM"]:
            plate_fee = 20_000_000
        else:
            plate_fee = 1_000_000

        road_maintenance_fee = 1_560_000  # 1.56m VND/year for passenger cars

        if seats >= 7:
            civil_insurance = 794_000  # 794,000 VND for >= 7 seats
        else:
            civil_insurance = 437_000  # 437,000 VND for < 7 seats
    else:
        # MOTORBIKE
        if req.province_code in ["HN", "HCM"]:
            plate_fee = 2000000
        else:
            plate_fee = 150000

        road_maintenance_fee = 0
        civil_insurance = 66000

    total_rolling_cost = list_price + registration_fee + plate_fee + road_maintenance_fee + civil_insurance

    # Đóng gói từng khoản phí ban đầu để API trả về chi tiết thay vì chỉ một tổng số.
    rolling_cost = RollingCostBreakdown(
        registration_fee_vnd=registration_fee,
        plate_fee_vnd=plate_fee,
        road_maintenance_fee_vnd=road_maintenance_fee,
        civil_insurance_vnd=civil_insurance,
        total_rolling_cost_vnd=total_rolling_cost,
    )

    # 2. Chi phí vận hành tháng gồm thuê pin (nếu có), điện sạc và bảo dưỡng ước tính.
    # Khi mua pin, không cộng phí thuê pin định kỳ.
    if req.battery_option == "RENTAL":
        battery_fee = battery_rent_monthly
    else:
        battery_fee = 0

    # Ưu tiên mức tiêu thụ suy ra từ thông số pin/tầm hoạt động trong catalog.
    # Nếu thiếu hoặc không hợp lệ, dùng baseline theo mẫu xe hay loại phương tiện.
    if vehicle and vehicle.get("battery_kwh") and vehicle.get("range_km"):
        try:
            # Nếu catalog có dung lượng pin và quãng đường, suy ra mức tiêu thụ kWh/100 km.
            kwh = float(vehicle["battery_kwh"])
            rng = float(vehicle["range_km"])
            if rng > 0:
                kwh_per_100km = round((kwh / rng) * 100, 1)
            else:
                kwh_per_100km = 14.0 if v_type == "CAR" else 2.5
        except (ValueError, TypeError):
            kwh_per_100km = 14.0 if v_type == "CAR" else 2.5
    else:
        if any(k in v_code for k in ("vf-3", "vf3", "vf-2", "minio")):
            kwh_per_100km = 10.5
        elif any(k in v_code for k in ("vf-5", "vf5")):
            kwh_per_100km = 12.0
        elif any(k in v_code for k in ("vf-6", "vf6")):
            kwh_per_100km = 14.0
        elif any(k in v_code for k in ("vf-7", "vf7")):
            kwh_per_100km = 16.0
        elif any(k in v_code for k in ("vf-8", "vf8")):
            kwh_per_100km = 18.0
        elif any(k in v_code for k in ("vf-9", "vf9")):
            kwh_per_100km = 21.0
        elif v_type == "CAR":
            kwh_per_100km = 14.0
        else:
            kwh_per_100km = 2.5
    # Quy đổi quãng đường tháng sang điện năng tiêu thụ và chi phí theo giá sạc công khai.
    monthly_kwh = (req.monthly_km_estimate / 100.0) * kwh_per_100km
    charging_cost = int(round(monthly_kwh * PUBLIC_CHARGING_RATE_VND_PER_KWH))

    # Cộng phí pin, tiền điện và mức bảo dưỡng ước tính thành tổng chi phí tháng.
    maintenance_cost = 200000 if v_type == "CAR" else 50000
    total_monthly = battery_fee + charging_cost + maintenance_cost

    # Giữ riêng từng thành phần chi phí để client có thể trình bày bảng phân tích.
    monthly_cost = MonthlyOperatingCost(
        battery_subscription_fee_vnd=battery_fee,
        charging_electricity_cost_vnd=charging_cost,
        estimated_maintenance_vnd=maintenance_cost,
        total_monthly_cost_vnd=total_monthly,
    )

    # Ước tính số tháng để phần chênh lệch giá mua pin bằng tổng phí thuê pin.
    # Nếu phí thuê không dương thì không thể tính thời điểm hòa vốn, kết quả là 0.
    delta_battery_buy = battery_buy_price - base_price
    breakeven_months = (delta_battery_buy // battery_rent_monthly) if battery_rent_monthly > 0 else 0

    comparison_summary = {
        "battery_buy_diff_vnd": delta_battery_buy,
        "monthly_rental_fee_vnd": battery_rent_monthly,
        "breakeven_months": breakeven_months,
        "recommendation": "Thuê pin phù hợp nếu đi vừa phải hoặc muốn tối ưu chi phí ban đầu. Mua pin phù hợp nếu di chuyển nhiều và sử dụng xe trên 3-5 năm."
    }

    # Trả về toàn bộ thông tin đầu vào quan trọng, chi phí chi tiết và lưu ý ước tính.
    return TCOCalculationResponse(
        vehicle_type=v_type,
        model_id=req.model_id,
        province_code=req.province_code,
        battery_option=req.battery_option,
        monthly_km_estimate=req.monthly_km_estimate,
        list_price_vnd=list_price,
        rolling_cost_breakdown=rolling_cost,
        monthly_operating_cost=monthly_cost,
        disclaimer_text=DISCLAIMER_TEXT,
        comparison_summary=comparison_summary,
    )
