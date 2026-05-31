from app.data.cleaning import CLEANED_BOOKING_COLUMNS
from app.database.schema import DATABASE_NAME, TABLE_DEFINITIONS, build_create_database_sql, build_schema_sql


def test_schema_defines_required_database_and_core_tables():
    assert DATABASE_NAME == "hotel_booking_analysis"
    assert set(TABLE_DEFINITIONS) == {
        "hotel_bookings",
        "prediction_results",
        "model_metrics",
        "realtime_metrics",
    }


def test_hotel_bookings_table_contains_all_cleaned_columns_and_indexes():
    table = TABLE_DEFINITIONS["hotel_bookings"]
    column_names = [column.name for column in table.columns]

    for column in CLEANED_BOOKING_COLUMNS:
        assert column in column_names

    assert table.primary_key == "booking_id"
    assert {"idx_arrival_date", "idx_country_code", "idx_is_canceled", "idx_event_date"}.issubset(
        {index.name for index in table.indexes}
    )


def test_build_schema_sql_contains_mysql_tables_charset_and_constraints():
    sql = build_schema_sql()

    assert "CREATE DATABASE IF NOT EXISTS hotel_booking_analysis" in build_create_database_sql()
    assert "DEFAULT CHARACTER SET utf8mb4" in build_create_database_sql()
    assert "CREATE TABLE IF NOT EXISTS hotel_bookings" in sql
    assert "booking_id BIGINT PRIMARY KEY" in sql
    assert "arrival_date DATE NOT NULL" in sql
    assert "is_deleted TINYINT NOT NULL DEFAULT 0" in sql
    assert "CREATE TABLE IF NOT EXISTS prediction_results" in sql
    assert "FOREIGN KEY (booking_id) REFERENCES hotel_bookings(booking_id)" in sql
    assert "CREATE TABLE IF NOT EXISTS model_metrics" in sql
    assert "CREATE TABLE IF NOT EXISTS realtime_metrics" in sql
    assert "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4" in sql
