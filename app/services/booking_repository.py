from math import ceil
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal

import pandas as pd


LIST_FIELDS = [
    "booking_id",
    "hotel",
    "hotel_name",
    "is_canceled",
    "is_canceled_label",
    "arrival_date",
    "country_code",
    "country_name",
    "market_segment",
    "market_segment_name",
    "customer_type",
    "customer_type_name",
    "lead_time",
    "total_guests",
    "total_nights",
    "adr",
]

DETAIL_FIELDS = [
    "booking_id",
    "hotel_name",
    "is_canceled_label",
    "lead_time",
    "arrival_date",
    "total_nights",
    "total_guests",
    "meal_name",
    "country_name",
    "market_segment_name",
    "distribution_channel",
    "is_repeated_guest_label",
    "previous_cancellations",
    "previous_bookings_not_canceled",
    "reserved_room_type",
    "assigned_room_type",
    "room_type_changed",
    "booking_changes",
    "deposit_type_name",
    "days_in_waiting_list",
    "customer_type_name",
    "adr",
    "required_car_parking_spaces",
    "total_of_special_requests",
    "reservation_status",
    "reservation_status_date",
]

SAMPLE_ORDER_FIELDS = [
    "booking_id",
    "hotel_name",
    "country_name",
    "lead_time",
    "adr",
    "is_canceled_label",
]

EDITABLE_FIELDS = {
    "customer_type",
    "market_segment",
    "deposit_type",
    "adr",
    "total_of_special_requests",
}


class BookingRepository:
    def __init__(self, csv_path):
        self.csv_path = Path(csv_path)
        self._frame = None

    def _load(self):
        if self._frame is None:
            frame = pd.read_csv(self.csv_path)
            for column in ("arrival_date", "event_date", "reservation_status_date"):
                if column in frame:
                    frame[column] = pd.to_datetime(frame[column], errors="coerce")
            self._frame = frame
        return self._frame.copy()

    def active_bookings(self):
        frame = self._load()
        if "is_deleted" in frame:
            frame = frame[frame["is_deleted"].fillna(0).astype(int) == 0]
        return frame

    def get_booking(self, booking_id):
        frame = self.active_bookings()
        matches = frame[frame["booking_id"].astype(int) == int(booking_id)]
        if matches.empty:
            return None
        return _json_record(matches.iloc[0].to_dict())

    def update_booking(self, booking_id, values):
        frame = self._load()
        mask = frame["booking_id"].astype(int) == int(booking_id)
        if not mask.any():
            return False
        for field, value in values.items():
            if field in EDITABLE_FIELDS:
                frame.loc[mask, field] = value
        self._frame = frame
        self._save(frame)
        return True

    def logical_delete_booking(self, booking_id):
        frame = self._load()
        mask = frame["booking_id"].astype(int) == int(booking_id)
        if not mask.any():
            return False
        frame.loc[mask, "is_deleted"] = 1
        self._frame = frame
        self._save(frame)
        return True

    def filter_bookings(self, filters):
        frame = self.active_bookings()
        for key in ("hotel", "country_code", "market_segment", "customer_type"):
            value = filters.get(key)
            if value:
                frame = frame[frame[key].astype(str) == str(value)]
        if filters.get("is_canceled") not in (None, ""):
            frame = frame[frame["is_canceled"].astype(int) == int(filters["is_canceled"])]
        keyword = filters.get("keyword")
        if keyword:
            keyword = str(keyword).lower()
            frame = frame[
                frame["booking_id"].astype(str).str.contains(keyword, na=False)
                | frame["country_name"].astype(str).str.lower().str.contains(keyword, na=False)
                | frame["country_code"].astype(str).str.lower().str.contains(keyword, na=False)
            ]
        return frame

    def _save(self, frame):
        output = frame.copy()
        for column in ("arrival_date", "event_date", "reservation_status_date"):
            if column in output:
                output[column] = output[column].dt.strftime("%Y-%m-%d")
        output.to_csv(self.csv_path, index=False, encoding="utf-8")

    def paginated_bookings(self, filters, page=1, page_size=20, fields=None):
        frame = self.filter_bookings(filters)
        return _paginate_frame(frame, page, page_size, fields or LIST_FIELDS)


class MySQLBookingRepository:
    def __init__(self, mysql_client):
        self.mysql_client = mysql_client

    def active_bookings(self):
        with self.mysql_client.cursor() as cursor:
            cursor.execute("SELECT * FROM hotel_bookings WHERE is_deleted = 0")
            frame = pd.DataFrame(cursor.fetchall())
        return _normalize_dates(frame)

    def get_booking(self, booking_id):
        with self.mysql_client.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM hotel_bookings WHERE is_deleted = 0 AND booking_id = %s",
                (int(booking_id),),
            )
            row = cursor.fetchone()
        return _json_record(row) if row else None

    def update_booking(self, booking_id, values):
        update_values = {key: value for key, value in values.items() if key in EDITABLE_FIELDS}
        if not update_values:
            return False
        assignments = ", ".join(f"{field} = %s" for field in update_values)
        params = tuple(update_values.values()) + (int(booking_id),)
        with self.mysql_client.cursor() as cursor:
            cursor.execute(f"UPDATE hotel_bookings SET {assignments} WHERE booking_id = %s", params)
        return True

    def logical_delete_booking(self, booking_id):
        with self.mysql_client.cursor() as cursor:
            cursor.execute("UPDATE hotel_bookings SET is_deleted = 1 WHERE booking_id = %s", (int(booking_id),))
        return True

    def filter_bookings(self, filters):
        where_sql, params = _build_where(filters)
        with self.mysql_client.cursor() as cursor:
            cursor.execute(f"SELECT * FROM hotel_bookings {where_sql}", params)
            frame = pd.DataFrame(cursor.fetchall())
        return _normalize_dates(frame)

    def paginated_bookings(self, filters, page=1, page_size=20, fields=None):
        page = max(int(page or 1), 1)
        page_size = max(min(int(page_size or 20), 100), 1)
        offset = (page - 1) * page_size
        fields = fields or LIST_FIELDS
        select_fields = ", ".join(fields)
        where_sql, params = _build_where(filters)
        with self.mysql_client.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM hotel_bookings {where_sql}", params)
            total = int(cursor.fetchall()[0]["total"])
            cursor.execute(
                f"SELECT {select_fields} FROM hotel_bookings {where_sql} ORDER BY booking_id LIMIT %s OFFSET %s",
                params + (page_size, offset),
            )
            rows = cursor.fetchall()
        return {
            "items": [_json_record(row) for row in rows],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": ceil(total / page_size) if total else 0,
            },
        }


def option_pairs(frame, value_column, label_column):
    values = frame[[value_column, label_column]].dropna().drop_duplicates()
    values = values.sort_values([label_column, value_column])
    return [
        {"value": _json_value(row[value_column]), "label": _json_value(row[label_column])}
        for _, row in values.iterrows()
    ]


def _build_where(filters):
    filters = filters or {}
    clauses = ["is_deleted = 0"]
    params = []
    for key in ("hotel", "country_code", "market_segment", "customer_type"):
        value = filters.get(key)
        if value:
            clauses.append(f"{key} = %s")
            params.append(value)
    if filters.get("is_canceled") not in (None, ""):
        clauses.append("is_canceled = %s")
        params.append(int(filters["is_canceled"]))
    keyword = filters.get("keyword")
    if keyword:
        clauses.append("(CAST(booking_id AS CHAR) LIKE %s OR country_name LIKE %s OR country_code LIKE %s)")
        pattern = f"%{keyword}%"
        params.extend([pattern, pattern, pattern])
    return "WHERE " + " AND ".join(clauses), tuple(params)


def _normalize_dates(frame):
    for column in ("arrival_date", "event_date", "reservation_status_date"):
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def _paginate_frame(frame, page, page_size, fields):
    page = max(int(page or 1), 1)
    page_size = max(min(int(page_size or 20), 100), 1)
    total = len(frame)
    start = (page - 1) * page_size
    items_frame = frame.iloc[start : start + page_size]
    items = [_json_record(row[fields].to_dict()) for _, row in items_frame.iterrows()]
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": ceil(total / page_size) if total else 0,
        },
    }


def _json_record(record):
    return {key: _json_value(value) for key, value in record.items()}


def _json_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, Decimal):
        return round(float(value), 4)
    if isinstance(value, float):
        return round(value, 4)
    return value
