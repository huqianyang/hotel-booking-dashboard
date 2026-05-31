import subprocess
import sys
from pathlib import Path

import pandas as pd

from app.data.cleaning import CLEANED_BOOKING_COLUMNS
from app.database.importer import (
    build_insert_sql,
    build_missing_column_sql,
    export_cleaned_bookings_csv,
    import_cleaned_bookings,
)


def _raw_bookings():
    return pd.DataFrame(
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


def test_export_cleaned_bookings_csv_writes_schema_aligned_file(tmp_path):
    raw_path = tmp_path / "raw.csv"
    output_path = tmp_path / "cleaned.csv"
    _raw_bookings().to_csv(raw_path, index=False)

    exported = export_cleaned_bookings_csv(raw_path, output_path)

    assert exported == output_path
    cleaned = pd.read_csv(output_path)
    assert list(cleaned.columns) == CLEANED_BOOKING_COLUMNS
    assert cleaned.loc[0, "booking_id"] == 1
    assert cleaned.loc[0, "hotel_name"] == "度假酒店"
    assert cleaned.loc[1, "country_code"] == "未知"
    assert cleaned.loc[1, "adr"] == 0.0
    assert cleaned.loc[0, "arrival_date"] == "2015-07-01"
    assert cleaned.shape[1] == 41
    assert cleaned.loc[0, "meal_name"] == "含早餐"
    assert cleaned.loc[1, "is_repeated_guest_label"] == "回头客"
    assert cleaned.loc[1, "room_type_changed"] == 1
    assert cleaned.loc[1, "required_car_parking_spaces"] == 1
    assert cleaned.loc[1, "total_of_special_requests"] == 2


def test_build_insert_sql_matches_cleaned_columns():
    sql = build_insert_sql()

    assert sql.startswith("INSERT INTO hotel_bookings (")
    assert ", ".join(CLEANED_BOOKING_COLUMNS) in sql
    assert sql.count("%s") == len(CLEANED_BOOKING_COLUMNS)
    assert sql.endswith(")")


def test_build_missing_column_sql_adds_41_column_schema_fields():
    sql = build_missing_column_sql({"booking_id", "hotel"})

    assert "ALTER TABLE hotel_bookings ADD COLUMN meal VARCHAR(30) NOT NULL" in sql
    assert "ALTER TABLE hotel_bookings ADD COLUMN room_type_changed TINYINT NOT NULL DEFAULT 0" in sql
    assert "ALTER TABLE hotel_bookings ADD COLUMN total_of_special_requests INT NOT NULL DEFAULT 0" in sql
    assert "ADD COLUMN hotel " not in sql


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.batches = []

    def execute(self, sql):
        self.executed.append(sql)
        if sql == "SHOW COLUMNS FROM hotel_bookings":
            self.column_rows = [("booking_id",), ("hotel",)]

    def fetchall(self):
        return getattr(self, "column_rows", [])

    def executemany(self, sql, rows):
        self.batches.append((sql, rows))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.commits = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1


def test_import_cleaned_bookings_creates_schema_and_batches_rows(tmp_path):
    cleaned_path = tmp_path / "cleaned.csv"
    raw_path = tmp_path / "raw.csv"
    _raw_bookings().to_csv(raw_path, index=False)
    export_cleaned_bookings_csv(raw_path, cleaned_path)
    connection = FakeConnection()

    imported = import_cleaned_bookings(connection, cleaned_path, batch_size=1)

    assert imported == 2
    assert any("CREATE DATABASE IF NOT EXISTS hotel_booking_analysis" in sql for sql in connection.cursor_instance.executed)
    assert any("CREATE TABLE IF NOT EXISTS hotel_bookings" in sql for sql in connection.cursor_instance.executed)
    assert len(connection.cursor_instance.batches) == 2
    first_sql, first_rows = connection.cursor_instance.batches[0]
    assert first_sql == build_insert_sql()
    assert first_rows[0][0] == 1
    assert first_rows[0][2] == "度假酒店"
from scripts.import_hotel_bookings import parse_args


def test_parse_args_uses_project_default_paths():
    args = parse_args([])

    assert args.raw_csv == Path("hotel_bookings.csv")
    assert args.cleaned_csv == Path("数据/cleaned_hotel_bookings.csv")
    assert args.host == "127.0.0.1"
    assert args.port == 3306
    assert args.user == "root"
    assert args.password is None
    assert args.export_only is False


def test_import_script_runs_export_only_from_project_root(tmp_path):
    raw_path = tmp_path / "raw.csv"
    cleaned_path = tmp_path / "cleaned.csv"
    _raw_bookings().to_csv(raw_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/import_hotel_bookings.py",
            "--raw-csv",
            str(raw_path),
            "--cleaned-csv",
            str(cleaned_path),
            "--export-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Cleaned CSV written to" in result.stdout
    assert cleaned_path.exists()
