import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

from src.services.tco_calculator import (
    DISCLAIMER_TEXT,
    TCOCalculationRequest,
    calculate_tco,
)


def test_tco_calculator_car_hanoi():
    req = TCOCalculationRequest(
        vehicle_type="CAR",
        model_id="vf-5",
        province_code="HN",
        battery_option="RENTAL",
        monthly_km_estimate=1000,
    )
    res = calculate_tco(req)

    assert res.vehicle_type == "CAR"
    assert res.model_id == "vf-5"
    assert res.list_price_vnd == 496000000
    assert res.rolling_cost_breakdown.registration_fee_vnd == 0
    assert res.rolling_cost_breakdown.plate_fee_vnd == 20000000
    assert res.rolling_cost_breakdown.road_maintenance_fee_vnd == 1560000
    assert res.rolling_cost_breakdown.civil_insurance_vnd == 437000
    assert res.rolling_cost_breakdown.total_rolling_cost_vnd == 496000000 + 20000000 + 1560000 + 437000

    assert res.monthly_operating_cost.battery_subscription_fee_vnd == 1600000
    assert res.monthly_operating_cost.charging_electricity_cost_vnd > 0
    assert res.monthly_operating_cost.estimated_maintenance_vnd == 200000
    assert res.disclaimer_text == DISCLAIMER_TEXT


def test_tco_calculator_car_other_province_buy_battery():
    req = TCOCalculationRequest(
        vehicle_type="CAR",
        model_id="vf3",
        province_code="OTHER",
        battery_option="BUY",
        monthly_km_estimate=500,
    )
    res = calculate_tco(req)

    assert res.list_price_vnd == 322000000
    assert res.rolling_cost_breakdown.plate_fee_vnd == 1000000
    assert res.monthly_operating_cost.battery_subscription_fee_vnd == 0
    assert res.disclaimer_text == DISCLAIMER_TEXT


def test_tco_calculator_motorbike():
    req = TCOCalculationRequest(
        vehicle_type="MOTORBIKE",
        model_id="feliz-s",
        province_code="HCM",
        battery_option="RENTAL",
        monthly_km_estimate=800,
    )
    res = calculate_tco(req)

    assert res.vehicle_type == "MOTORBIKE"
    assert res.rolling_cost_breakdown.registration_fee_vnd == 0
    assert res.rolling_cost_breakdown.plate_fee_vnd == 2000000
    assert res.rolling_cost_breakdown.road_maintenance_fee_vnd == 0
    assert res.rolling_cost_breakdown.civil_insurance_vnd == 66000
    assert res.monthly_operating_cost.battery_subscription_fee_vnd == 350000
    assert res.disclaimer_text == DISCLAIMER_TEXT


@pytest.mark.asyncio
async def test_tco_calculator_api_endpoint(client):
    response = await client.post(
        "/api/v1/tco/calculate",
        json={
            "vehicle_type": "CAR",
            "model_id": "vf8-eco",
            "province_code": "HN",
            "battery_option": "RENTAL",
            "monthly_km_estimate": 1200,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == "vf8-eco"
    assert data["disclaimer_text"] == DISCLAIMER_TEXT


def test_tco_calculator_7_seater_limo_green():
    """Test 7-seat car gets correct civil insurance (794,000 VND) and DB list price."""
    req = TCOCalculationRequest(
        vehicle_type="CAR",
        model_id="limo-green",
        province_code="HN",
        battery_option="RENTAL",
        monthly_km_estimate=1500,
    )
    res = calculate_tco(req)

    assert res.vehicle_type == "CAR"
    assert res.list_price_vnd == 699000000
    assert res.rolling_cost_breakdown.civil_insurance_vnd == 794000
    assert res.rolling_cost_breakdown.plate_fee_vnd == 20000000


def test_tco_calculator_overrides():
    """Test manual overrides for price, seats, and battery rental."""
    req = TCOCalculationRequest(
        vehicle_type="CAR",
        model_id="custom-model",
        base_price_override=600000000,
        battery_buy_price_override=700000000,
        battery_rent_monthly_override=2000000,
        seat_count=7,
        province_code="HCM",
        battery_option="RENTAL",
    )
    res = calculate_tco(req)

    assert res.list_price_vnd == 600000000
    assert res.rolling_cost_breakdown.civil_insurance_vnd == 794000
    assert res.monthly_operating_cost.battery_subscription_fee_vnd == 2000000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

