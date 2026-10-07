import time

from src.services import catalog_service


def test_catalog_color_filter_matches_accent_and_mixed_case(monkeypatch):
    monkeypatch.setattr(
        catalog_service,
        "_CATALOG_CACHE",
        {
            "raw_cars": (
                time.time(),
                [
                        {"car_id": "red", "model_name": "VinFast Xe Đỏ", "colors": ["Đỏ tươi"], "base_price": 100, "is_active": True},
                        {"car_id": "blue", "model_name": "VinFast Xe Xanh", "colors": ["Xanh rêu"], "base_price": 100, "is_active": True},
                ],
            )
        },
    )

    result = catalog_service.fetch_cars_from_supabase(colors=["do"])

    assert [car["id"] for car in result] == ["red"]


def test_motorbike_formatter_keeps_colors_and_filters_them(monkeypatch):
    monkeypatch.setattr(
        catalog_service,
        "_CATALOG_CACHE",
        {
            "raw_bikes": (
                time.time(),
                [
                    {"motorbike_id": "red-bike", "model_name": "Xe đỏ", "colors": [{"name": "Đỏ tươi"}], "is_active": True},
                    {"motorbike_id": "black-bike", "model_name": "Xe đen", "colors": ["Đen bóng"], "is_active": True},
                ],
            )
        },
    )

    result = catalog_service.fetch_motorbikes_from_supabase(colors=["Đỏ"])

    assert [bike["id"] for bike in result] == ["red-bike"]
    assert result[0]["colors"] == [{"name": "Đỏ tươi"}]
