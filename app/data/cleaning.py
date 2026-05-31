import pandas as pd


CLEANED_BOOKING_COLUMNS = [
    "booking_id",
    "hotel",
    "hotel_name",
    "is_canceled",
    "is_canceled_label",
    "lead_time",
    "arrival_date",
    "event_date",
    "stays_in_weekend_nights",
    "stays_in_week_nights",
    "total_nights",
    "adults",
    "children",
    "babies",
    "total_guests",
    "country_code",
    "country_name",
    "market_segment",
    "market_segment_name",
    "distribution_channel",
    "deposit_type",
    "deposit_type_name",
    "customer_type",
    "customer_type_name",
    "adr",
    "reservation_status",
    "reservation_status_date",
    "is_deleted",
]

_MONTH_NAMES = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}

_HOTEL_NAMES = {
    "Resort Hotel": "度假酒店",
    "City Hotel": "城市酒店",
}

_COUNTRY_NAMES = {
    "PRT": "葡萄牙",
    "GBR": "英国",
    "FRA": "法国",
    "ESP": "西班牙",
    "DEU": "德国",
    "ITA": "意大利",
    "IRL": "爱尔兰",
    "BRA": "巴西",
    "USA": "美国",
    "CN": "中国",
    "CHN": "中国",
}

_MARKET_SEGMENT_NAMES = {
    "Direct": "直接预订",
    "Corporate": "企业客户",
    "Online TA": "线上旅行社",
    "Offline TA/TO": "线下旅行社/批发商",
    "Groups": "团队",
    "Complementary": "免费订单",
    "Aviation": "航空客户",
    "Undefined": "未知",
}

_DEPOSIT_TYPE_NAMES = {
    "No Deposit": "无订金",
    "Non Refund": "不可退订金",
    "Refundable": "可退订金",
}

_CUSTOMER_TYPE_NAMES = {
    "Transient": "散客",
    "Transient-Party": "散客团体",
    "Contract": "合约客户",
    "Group": "团队客户",
}


def _arrival_date(frame):
    month = frame["arrival_date_month"].map(_MONTH_NAMES)
    date_parts = pd.DataFrame(
        {
            "year": frame["arrival_date_year"],
            "month": month,
            "day": frame["arrival_date_day_of_month"],
        }
    )
    return pd.to_datetime(date_parts)


def clean_hotel_bookings(raw_bookings):
    cleaned = pd.DataFrame(index=raw_bookings.index)
    cleaned["booking_id"] = range(1, len(raw_bookings) + 1)
    cleaned["hotel"] = raw_bookings["hotel"]
    cleaned["hotel_name"] = raw_bookings["hotel"].map(_HOTEL_NAMES).fillna(raw_bookings["hotel"])
    cleaned["is_canceled"] = pd.to_numeric(raw_bookings["is_canceled"], errors="coerce").fillna(0).astype(int)
    cleaned["is_canceled_label"] = cleaned["is_canceled"].map({0: "未取消", 1: "已取消"})
    cleaned["lead_time"] = pd.to_numeric(raw_bookings["lead_time"], errors="coerce").fillna(0).astype(int)
    cleaned["arrival_date"] = _arrival_date(raw_bookings)
    cleaned["event_date"] = cleaned["arrival_date"]
    cleaned["stays_in_weekend_nights"] = pd.to_numeric(raw_bookings["stays_in_weekend_nights"], errors="coerce").fillna(0).astype(int)
    cleaned["stays_in_week_nights"] = pd.to_numeric(raw_bookings["stays_in_week_nights"], errors="coerce").fillna(0).astype(int)
    cleaned["total_nights"] = cleaned["stays_in_weekend_nights"] + cleaned["stays_in_week_nights"]
    cleaned["adults"] = pd.to_numeric(raw_bookings["adults"], errors="coerce").fillna(0).astype(int)
    cleaned["children"] = pd.to_numeric(raw_bookings["children"], errors="coerce").fillna(0).astype(int)
    cleaned["babies"] = pd.to_numeric(raw_bookings["babies"], errors="coerce").fillna(0).astype(int)
    cleaned["total_guests"] = cleaned["adults"] + cleaned["children"] + cleaned["babies"]
    cleaned["country_code"] = raw_bookings["country"].fillna("未知")
    cleaned["country_name"] = cleaned["country_code"].map(_COUNTRY_NAMES).fillna(cleaned["country_code"])
    cleaned["market_segment"] = raw_bookings["market_segment"].fillna("Undefined")
    cleaned["market_segment_name"] = cleaned["market_segment"].map(_MARKET_SEGMENT_NAMES).fillna(cleaned["market_segment"])
    cleaned["distribution_channel"] = raw_bookings["distribution_channel"].fillna("Undefined")
    cleaned["deposit_type"] = raw_bookings["deposit_type"].fillna("No Deposit")
    cleaned["deposit_type_name"] = cleaned["deposit_type"].map(_DEPOSIT_TYPE_NAMES).fillna(cleaned["deposit_type"])
    cleaned["customer_type"] = raw_bookings["customer_type"].fillna("Transient")
    cleaned["customer_type_name"] = cleaned["customer_type"].map(_CUSTOMER_TYPE_NAMES).fillna(cleaned["customer_type"])
    cleaned["adr"] = pd.to_numeric(raw_bookings["adr"], errors="coerce").fillna(0.0).astype(float)
    cleaned["reservation_status"] = raw_bookings["reservation_status"]
    cleaned["reservation_status_date"] = pd.to_datetime(raw_bookings["reservation_status_date"])
    cleaned["is_deleted"] = 0
    return cleaned[CLEANED_BOOKING_COLUMNS]
