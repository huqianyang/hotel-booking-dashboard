from pathlib import Path

import pandas as pd

from app.data.cleaning import CLEANED_BOOKING_COLUMNS, clean_hotel_bookings
from app.database.schema import TABLE_DEFINITIONS, build_create_database_sql, build_schema_sql


def export_cleaned_bookings_csv(raw_csv_path, output_csv_path):
    raw_csv_path = Path(raw_csv_path)
    output_csv_path = Path(output_csv_path)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    raw_bookings = pd.read_csv(raw_csv_path)
    cleaned = clean_hotel_bookings(raw_bookings)
    cleaned.to_csv(output_csv_path, index=False, date_format="%Y-%m-%d", encoding="utf-8-sig")
    return output_csv_path


def build_insert_sql():
    columns = ", ".join(CLEANED_BOOKING_COLUMNS)
    placeholders = ", ".join(["%s"] * len(CLEANED_BOOKING_COLUMNS))
    updates = ", ".join(
        f"{column}=VALUES({column})"
        for column in CLEANED_BOOKING_COLUMNS
        if column != TABLE_DEFINITIONS["hotel_bookings"].primary_key
    )
    return f"INSERT INTO hotel_bookings ({columns}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}"


def build_missing_column_sql(existing_columns):
    return "\n".join(
        f"ALTER TABLE hotel_bookings ADD COLUMN {column.to_sql()};"
        for column in TABLE_DEFINITIONS["hotel_bookings"].columns
        if not column.primary_key and column.name not in existing_columns
    )


def import_cleaned_bookings(connection, cleaned_csv_path, batch_size=1000):
    cleaned_csv_path = Path(cleaned_csv_path)
    frame = pd.read_csv(cleaned_csv_path)
    rows = [tuple(row[column] for column in CLEANED_BOOKING_COLUMNS) for _, row in frame.iterrows()]

    with connection.cursor() as cursor:
        cursor.execute(build_create_database_sql())
        for statement in build_schema_sql().split(";\n"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        cursor.execute("SHOW COLUMNS FROM hotel_bookings")
        existing_columns = {row[0] for row in cursor.fetchall()}
        for statement in build_missing_column_sql(existing_columns).split(";\n"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)

        insert_sql = build_insert_sql()
        for start in range(0, len(rows), batch_size):
            cursor.executemany(insert_sql, rows[start : start + batch_size])

    connection.commit()
    return len(rows)
