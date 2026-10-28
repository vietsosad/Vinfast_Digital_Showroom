from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TCOCalculationRequest(BaseModel):
    # Loại phương tiện dùng để tính tổng chi phí sở hữu (TCO).
    vehicle_type: Literal["CAR", "MOTORBIKE"] = "CAR"
    # Mã mẫu xe bắt buộc, dài từ 1 đến 60 ký tự.
    model_id: str = Field(..., min_length=1, max_length=60, examples=["vf-5"])
    # Mã phiên bản xe; có thể bỏ trống nếu không chọn phiên bản cụ thể.
    variant_id: str | None = None
    # Mã khu vực dùng để áp dụng các khoản phí đăng ký tương ứng.
    province_code: Literal["HN", "HCM", "OTHER"] = "OTHER"
    # Hình thức sử dụng pin: thuê theo tháng hoặc mua pin.
    battery_option: Literal["RENTAL", "BUY"] = "RENTAL"
    # Số km di chuyển ước tính mỗi tháng; chấp nhận từ 0 đến 100.000 km.
    monthly_km_estimate: int = Field(default=1000, ge=0, le=100_000)
    # Giá xe tùy chỉnh (VND), nếu không nhập sẽ dùng giá niêm yết.
    base_price_override: int | None = Field(None, ge=0)
    # Giá mua pin tùy chỉnh (VND), áp dụng khi cần ghi đè giá mặc định.
    battery_buy_price_override: int | None = Field(None, ge=0)
    # Phí thuê pin hàng tháng tùy chỉnh (VND).
    battery_rent_monthly_override: int | None = Field(None, ge=0)
    # Số chỗ ngồi, giới hạn từ 2 đến 9.
    seat_count: int = Field(default=5, ge=2, le=9)


class RollingCostBreakdown(BaseModel):
    # Cho phép tạo schema trực tiếp từ thuộc tính của đối tượng domain/ORM.
    model_config = ConfigDict(from_attributes=True)

    # Các khoản chi phí ban đầu khi đưa xe vào sử dụng, đơn vị VND.
    registration_fee_vnd: int
    plate_fee_vnd: int
    road_maintenance_fee_vnd: int
    civil_insurance_vnd: int
    # Tổng các khoản chi phí ban đầu ở trên, đơn vị VND.
    total_rolling_cost_vnd: int


class MonthlyOperatingCost(BaseModel):
    # Cho phép tạo schema trực tiếp từ thuộc tính của đối tượng domain/ORM.
    model_config = ConfigDict(from_attributes=True)

    # Chi phí vận hành ước tính mỗi tháng, các giá trị tính bằng VND.
    battery_subscription_fee_vnd: int
    charging_electricity_cost_vnd: int
    estimated_maintenance_vnd: int
    total_monthly_cost_vnd: int


class TCOCalculationResponse(BaseModel):
    # Cho phép tạo schema trực tiếp từ thuộc tính của đối tượng domain/ORM.
    model_config = ConfigDict(from_attributes=True)

    # Thông tin phương tiện và giả định đầu vào của phép tính.
    vehicle_type: str
    model_id: str
    province_code: str
    battery_option: str
    monthly_km_estimate: int
    # Giá niêm yết và các khoản phí/chi phí tổng hợp, đơn vị tiền là VND.
    list_price_vnd: int
    rolling_cost_breakdown: RollingCostBreakdown
    monthly_operating_cost: MonthlyOperatingCost
    # Lưu ý về giả định hoặc phạm vi của kết quả tính toán.
    disclaimer_text: str
    # Thông tin so sánh bổ sung; có thể không có nếu không áp dụng.
    comparison_summary: dict[str, Any] | None = None
