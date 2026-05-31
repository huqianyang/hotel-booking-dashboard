import pandas as pd

from app.data.cleaning import CLEANED_BOOKING_COLUMNS, clean_hotel_bookings


def test_clean_hotel_bookings_builds_core_fields_and_chinese_labels():
    raw = pd.DataFrame(
        [
            {
                "hotel": "Resort Hotel",
                "is_canceled": 0,
                "lead_time": 10,
                "arrival_date_year": 2015,
                "arrival_date_month": "July",
                "arrival_date_day_of_month": 1,
                "stays_in_weekend_nights": 1,
                "stays_in_week_nights": 2,
                "adults": 2,
                "children": None,
                "babies": 0,
                "country": "PRT",
                "market_segment": "Direct",
                "distribution_channel": "Direct",
                "deposit_type": "No Deposit",
                "customer_type": "Transient",
                "adr": 88.5,
                "reservation_status": "Check-Out",
                "reservation_status_date": "2015-07-01",
            },
            {
                "hotel": "City Hotel",
                "is_canceled": 1,
                "lead_time": 42,
                "arrival_date_year": 2016,
                "arrival_date_month": "August",
                "arrival_date_day_of_month": 15,
                "stays_in_weekend_nights": 0,
                "stays_in_week_nights": 3,
                "adults": 1,
                "children": 1,
                "babies": 0,
                "country": None,
                "market_segment": "Online TA",
                "distribution_channel": "TA/TO",
                "deposit_type": "Non Refund",
                "customer_type": "Transient-Party",
                "adr": None,
                "reservation_status": "Canceled",
                "reservation_status_date": "2016-08-10",
            },
        ]
    )

    cleaned = clean_hotel_bookings(raw)

    assert list(cleaned.columns) == CLEANED_BOOKING_COLUMNS
    assert cleaned.loc[0, "booking_id"] == 1
    assert cleaned.loc[1, "booking_id"] == 2
    assert str(cleaned.loc[0, "arrival_date"].date()) == "2015-07-01"
    assert str(cleaned.loc[1, "arrival_date"].date()) == "2016-08-15"
    assert cleaned.loc[0, "hotel_name"] == "度假酒店"
    assert cleaned.loc[1, "hotel_name"] == "城市酒店"
    assert cleaned.loc[0, "is_canceled_label"] == "未取消"
    assert cleaned.loc[1, "is_canceled_label"] == "已取消"
    assert cleaned.loc[0, "country_code"] == "PRT"
    assert cleaned.loc[1, "country_code"] == "未知"
    assert cleaned.loc[0, "country_name"] == "葡萄牙"
    assert cleaned.loc[1, "country_name"] == "未知"
    assert cleaned.loc[0, "children"] == 0
    assert cleaned.loc[1, "adr"] == 0.0
    assert cleaned.loc[0, "total_guests"] == 2
    assert cleaned.loc[1, "total_nights"] == 3
    assert cleaned.loc[0, "is_deleted"] == 0


def test_clean_hotel_bookings_preserves_model_features_as_numeric_values():
    raw = pd.DataFrame(
        [
            {
                "hotel": "City Hotel",
                "is_canceled": 1,
                "lead_time": 7,
                "arrival_date_year": 2017,
                "arrival_date_month": "January",
                "arrival_date_day_of_month": 20,
                "stays_in_weekend_nights": 2,
                "stays_in_week_nights": 5,
                "adults": 2,
                "children": 2,
                "babies": 1,
                "country": "GBR",
                "market_segment": "Groups",
                "distribution_channel": "TA/TO",
                "deposit_type": "Refundable",
                "customer_type": "Group",
                "adr": 130.25,
                "reservation_status": "Canceled",
                "reservation_status_date": "2017-01-18",
            }
        ]
    )

    cleaned = clean_hotel_bookings(raw)

    numeric_columns = [
        "is_canceled",
        "lead_time",
        "stays_in_weekend_nights",
        "stays_in_week_nights",
        "adults",
        "children",
        "babies",
        "adr",
        "total_guests",
        "total_nights",
    ]
    assert all(pd.api.types.is_numeric_dtype(cleaned[column]) for column in numeric_columns)
    assert cleaned.loc[0, "market_segment_name"] == "团队"
    assert cleaned.loc[0, "customer_type_name"] == "团队客户"
    assert cleaned.loc[0, "deposit_type_name"] == "可退订金"
