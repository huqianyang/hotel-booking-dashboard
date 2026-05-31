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
                "meal": "BB",
                "country": "PRT",
                "market_segment": "Direct",
                "distribution_channel": "Direct",
                "is_repeated_guest": 0,
                "previous_cancellations": 0,
                "previous_bookings_not_canceled": 1,
                "reserved_room_type": "C",
                "assigned_room_type": "C",
                "booking_changes": 3,
                "deposit_type": "No Deposit",
                "days_in_waiting_list": 0,
                "customer_type": "Transient",
                "adr": 88.5,
                "required_car_parking_spaces": 0,
                "total_of_special_requests": 0,
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
                "meal": "HB",
                "country": None,
                "market_segment": "Online TA",
                "distribution_channel": "TA/TO",
                "is_repeated_guest": 1,
                "previous_cancellations": 1,
                "previous_bookings_not_canceled": 0,
                "reserved_room_type": "A",
                "assigned_room_type": "C",
                "booking_changes": 0,
                "deposit_type": "Non Refund",
                "days_in_waiting_list": 5,
                "customer_type": "Transient-Party",
                "adr": None,
                "required_car_parking_spaces": 1,
                "total_of_special_requests": 2,
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
    assert len(CLEANED_BOOKING_COLUMNS) == 41
    assert cleaned.loc[0, "meal"] == "BB"
    assert cleaned.loc[0, "meal_name"] == "含早餐"
    assert cleaned.loc[1, "meal_name"] == "半餐"
    assert cleaned.loc[0, "is_repeated_guest"] == 0
    assert cleaned.loc[1, "is_repeated_guest"] == 1
    assert cleaned.loc[0, "is_repeated_guest_label"] == "新客户"
    assert cleaned.loc[1, "is_repeated_guest_label"] == "回头客"
    assert cleaned.loc[0, "previous_cancellations"] == 0
    assert cleaned.loc[1, "previous_cancellations"] == 1
    assert cleaned.loc[0, "previous_bookings_not_canceled"] == 1
    assert cleaned.loc[1, "previous_bookings_not_canceled"] == 0
    assert cleaned.loc[0, "reserved_room_type"] == "C"
    assert cleaned.loc[1, "assigned_room_type"] == "C"
    assert cleaned.loc[0, "room_type_changed"] == 0
    assert cleaned.loc[1, "room_type_changed"] == 1
    assert cleaned.loc[0, "booking_changes"] == 3
    assert cleaned.loc[1, "days_in_waiting_list"] == 5
    assert cleaned.loc[1, "required_car_parking_spaces"] == 1
    assert cleaned.loc[1, "total_of_special_requests"] == 2


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
                "meal": "SC",
                "country": "GBR",
                "market_segment": "Groups",
                "distribution_channel": "TA/TO",
                "is_repeated_guest": 0,
                "previous_cancellations": 2,
                "previous_bookings_not_canceled": 4,
                "reserved_room_type": "A",
                "assigned_room_type": "A",
                "booking_changes": 1,
                "deposit_type": "Refundable",
                "days_in_waiting_list": 12,
                "customer_type": "Group",
                "adr": 130.25,
                "required_car_parking_spaces": 2,
                "total_of_special_requests": 3,
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
        "is_repeated_guest",
        "previous_cancellations",
        "previous_bookings_not_canceled",
        "booking_changes",
        "days_in_waiting_list",
        "required_car_parking_spaces",
        "total_of_special_requests",
        "room_type_changed",
    ]
    assert all(pd.api.types.is_numeric_dtype(cleaned[column]) for column in numeric_columns)
    assert cleaned.loc[0, "market_segment_name"] == "团队"
    assert cleaned.loc[0, "customer_type_name"] == "团队客户"
    assert cleaned.loc[0, "deposit_type_name"] == "可退订金"
    assert cleaned.loc[0, "meal_name"] == "不含餐"
    assert cleaned.loc[0, "room_type_changed"] == 0
