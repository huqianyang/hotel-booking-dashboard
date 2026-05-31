# 41-Column Cleaning Field Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the hotel booking cleaned dataset from 28 to 41 columns by restoring high-value raw fields and derived Chinese/explanation fields for modeling, querying, and visualization.

**Architecture:** Keep `app.data.cleaning.CLEANED_BOOKING_COLUMNS` as the single source of truth for cleaned CSV column order. Update `app.database.schema.HOTEL_BOOKINGS_COLUMNS` to mirror those columns so importer SQL and MySQL stay aligned automatically. Regenerate `数据/cleaned_hotel_bookings.csv` and re-import MySQL after tests pass.

**Tech Stack:** Python, pandas, pytest, PyMySQL, existing importer CLI.

---

### Task 1: Add failing cleaning tests for the 41-column schema

**Files:**
- Modify: `tests/test_data_cleaning.py`
- Reference: `app/data/cleaning.py`

- [ ] **Step 1: Update the sample raw rows with restored fields**

In both raw sample dictionaries in `test_clean_hotel_bookings_builds_core_fields_and_chinese_labels`, add these keys:

```python
"meal": "BB",
"is_repeated_guest": 0,
"previous_cancellations": 0,
"previous_bookings_not_canceled": 1,
"reserved_room_type": "C",
"assigned_room_type": "C",
"booking_changes": 3,
"days_in_waiting_list": 0,
"required_car_parking_spaces": 0,
"total_of_special_requests": 0,
```

For the second sample row, use:

```python
"meal": "HB",
"is_repeated_guest": 1,
"previous_cancellations": 1,
"previous_bookings_not_canceled": 0,
"reserved_room_type": "A",
"assigned_room_type": "C",
"booking_changes": 0,
"days_in_waiting_list": 5,
"required_car_parking_spaces": 1,
"total_of_special_requests": 2,
```

In the raw sample dictionary in `test_clean_hotel_bookings_preserves_model_features_as_numeric_values`, add:

```python
"meal": "SC",
"is_repeated_guest": 0,
"previous_cancellations": 2,
"previous_bookings_not_canceled": 4,
"reserved_room_type": "A",
"assigned_room_type": "A",
"booking_changes": 1,
"days_in_waiting_list": 12,
"required_car_parking_spaces": 2,
"total_of_special_requests": 3,
```

- [ ] **Step 2: Add assertions for restored fields**

In `test_clean_hotel_bookings_builds_core_fields_and_chinese_labels`, after existing assertions, add:

```python
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
```

In `test_clean_hotel_bookings_preserves_model_features_as_numeric_values`, extend `numeric_columns` with:

```python
        "is_repeated_guest",
        "previous_cancellations",
        "previous_bookings_not_canceled",
        "booking_changes",
        "days_in_waiting_list",
        "required_car_parking_spaces",
        "total_of_special_requests",
        "room_type_changed",
```

Then add:

```python
    assert cleaned.loc[0, "meal_name"] == "不含餐"
    assert cleaned.loc[0, "room_type_changed"] == 0
```

- [ ] **Step 3: Run cleaning tests to verify RED**

Run:

```bash
python -m pytest tests/test_data_cleaning.py -v
```

Expected: FAIL because `CLEANED_BOOKING_COLUMNS` is still length 28 and restored fields do not exist.

---

### Task 2: Implement 41-column cleaning output

**Files:**
- Modify: `app/data/cleaning.py`
- Test: `tests/test_data_cleaning.py`

- [ ] **Step 1: Add meal Chinese mapping**

Add below `_CUSTOMER_TYPE_NAMES`:

```python
_MEAL_NAMES = {
    "BB": "含早餐",
    "HB": "半餐",
    "FB": "全餐",
    "SC": "不含餐",
    "Undefined": "未知",
}
```

- [ ] **Step 2: Expand `CLEANED_BOOKING_COLUMNS` to 41 columns**

Replace the list with this exact order:

```python
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
    "meal",
    "meal_name",
    "country_code",
    "country_name",
    "market_segment",
    "market_segment_name",
    "distribution_channel",
    "is_repeated_guest",
    "is_repeated_guest_label",
    "previous_cancellations",
    "previous_bookings_not_canceled",
    "reserved_room_type",
    "assigned_room_type",
    "room_type_changed",
    "booking_changes",
    "deposit_type",
    "deposit_type_name",
    "days_in_waiting_list",
    "customer_type",
    "customer_type_name",
    "adr",
    "required_car_parking_spaces",
    "total_of_special_requests",
    "reservation_status",
    "reservation_status_date",
    "is_deleted",
]
```

- [ ] **Step 3: Populate restored fields in `clean_hotel_bookings()`**

After `total_guests`, add:

```python
    cleaned["meal"] = raw_bookings["meal"].fillna("Undefined")
    cleaned["meal_name"] = cleaned["meal"].map(_MEAL_NAMES).fillna(cleaned["meal"])
```

After `distribution_channel`, add:

```python
    cleaned["is_repeated_guest"] = pd.to_numeric(raw_bookings["is_repeated_guest"], errors="coerce").fillna(0).astype(int)
    cleaned["is_repeated_guest_label"] = cleaned["is_repeated_guest"].map({0: "新客户", 1: "回头客"})
    cleaned["previous_cancellations"] = pd.to_numeric(raw_bookings["previous_cancellations"], errors="coerce").fillna(0).astype(int)
    cleaned["previous_bookings_not_canceled"] = pd.to_numeric(raw_bookings["previous_bookings_not_canceled"], errors="coerce").fillna(0).astype(int)
    cleaned["reserved_room_type"] = raw_bookings["reserved_room_type"].fillna("未知")
    cleaned["assigned_room_type"] = raw_bookings["assigned_room_type"].fillna("未知")
    cleaned["room_type_changed"] = (cleaned["reserved_room_type"] != cleaned["assigned_room_type"]).astype(int)
    cleaned["booking_changes"] = pd.to_numeric(raw_bookings["booking_changes"], errors="coerce").fillna(0).astype(int)
```

After `deposit_type_name`, add:

```python
    cleaned["days_in_waiting_list"] = pd.to_numeric(raw_bookings["days_in_waiting_list"], errors="coerce").fillna(0).astype(int)
```

After `adr`, add:

```python
    cleaned["required_car_parking_spaces"] = pd.to_numeric(raw_bookings["required_car_parking_spaces"], errors="coerce").fillna(0).astype(int)
    cleaned["total_of_special_requests"] = pd.to_numeric(raw_bookings["total_of_special_requests"], errors="coerce").fillna(0).astype(int)
```

- [ ] **Step 4: Run cleaning tests to verify GREEN**

Run:

```bash
python -m pytest tests/test_data_cleaning.py -v
```

Expected: PASS.

---

### Task 3: Update MySQL schema for restored fields

**Files:**
- Modify: `tests/test_database_schema.py`
- Modify: `app/database/schema.py`
- Test: `tests/test_database_schema.py`

- [ ] **Step 1: Add failing schema assertions**

In `test_build_schema_sql_contains_mysql_tables_charset_and_constraints`, add:

```python
    assert "meal VARCHAR(30) NOT NULL" in sql
    assert "meal_name VARCHAR(30) NOT NULL" in sql
    assert "is_repeated_guest TINYINT NOT NULL DEFAULT 0" in sql
    assert "previous_cancellations INT NOT NULL DEFAULT 0" in sql
    assert "previous_bookings_not_canceled INT NOT NULL DEFAULT 0" in sql
    assert "reserved_room_type VARCHAR(10) NOT NULL" in sql
    assert "assigned_room_type VARCHAR(10) NOT NULL" in sql
    assert "room_type_changed TINYINT NOT NULL DEFAULT 0" in sql
    assert "booking_changes INT NOT NULL DEFAULT 0" in sql
    assert "days_in_waiting_list INT NOT NULL DEFAULT 0" in sql
    assert "required_car_parking_spaces INT NOT NULL DEFAULT 0" in sql
    assert "total_of_special_requests INT NOT NULL DEFAULT 0" in sql
```

In `test_hotel_bookings_table_contains_all_cleaned_columns_and_indexes`, update the index subset assertion to include:

```python
"idx_meal",
"idx_room_type_changed",
"idx_special_requests",
```

- [ ] **Step 2: Run schema tests to verify RED**

Run:

```bash
python -m pytest tests/test_database_schema.py -v
```

Expected: FAIL because schema does not yet include restored columns and indexes.

- [ ] **Step 3: Add restored columns to `HOTEL_BOOKINGS_COLUMNS`**

In `app/database/schema.py`, add column definitions matching the 41-column order from `CLEANED_BOOKING_COLUMNS`:

```python
    ColumnDefinition("meal", "VARCHAR(30)", nullable=False),
    ColumnDefinition("meal_name", "VARCHAR(30)", nullable=False),
    ColumnDefinition("is_repeated_guest", "TINYINT", nullable=False, default="0"),
    ColumnDefinition("is_repeated_guest_label", "VARCHAR(20)", nullable=False),
    ColumnDefinition("previous_cancellations", "INT", nullable=False, default="0"),
    ColumnDefinition("previous_bookings_not_canceled", "INT", nullable=False, default="0"),
    ColumnDefinition("reserved_room_type", "VARCHAR(10)", nullable=False),
    ColumnDefinition("assigned_room_type", "VARCHAR(10)", nullable=False),
    ColumnDefinition("room_type_changed", "TINYINT", nullable=False, default="0"),
    ColumnDefinition("booking_changes", "INT", nullable=False, default="0"),
    ColumnDefinition("days_in_waiting_list", "INT", nullable=False, default="0"),
    ColumnDefinition("required_car_parking_spaces", "INT", nullable=False, default="0"),
    ColumnDefinition("total_of_special_requests", "INT", nullable=False, default="0"),
```

- [ ] **Step 4: Add supporting indexes**

In the `hotel_bookings` indexes tuple, add:

```python
            IndexDefinition("idx_meal", ("meal",)),
            IndexDefinition("idx_room_type_changed", ("room_type_changed",)),
            IndexDefinition("idx_special_requests", ("total_of_special_requests",)),
```

- [ ] **Step 5: Run schema tests to verify GREEN**

Run:

```bash
python -m pytest tests/test_database_schema.py -v
```

Expected: PASS.

---

### Task 4: Update importer tests for 41 columns and regenerate data

**Files:**
- Modify: `tests/test_hotel_booking_importer.py`
- Generated: `数据/cleaned_hotel_bookings.csv`

- [ ] **Step 1: Update importer test sample raw rows**

In `_raw_bookings()` inside `tests/test_hotel_booking_importer.py`, add the same restored raw keys used in `tests/test_data_cleaning.py` for both rows.

- [ ] **Step 2: Add importer assertions for 41 columns**

In `test_export_cleaned_bookings_csv_writes_schema_aligned_file`, add:

```python
    assert cleaned.shape[1] == 41
    assert cleaned.loc[0, "meal_name"] == "含早餐"
    assert cleaned.loc[1, "is_repeated_guest_label"] == "回头客"
    assert cleaned.loc[1, "room_type_changed"] == 1
    assert cleaned.loc[1, "required_car_parking_spaces"] == 1
    assert cleaned.loc[1, "total_of_special_requests"] == 2
```

- [ ] **Step 3: Run importer tests to verify compatibility**

Run:

```bash
python -m pytest tests/test_hotel_booking_importer.py -v
```

Expected: PASS after Tasks 1-3 are implemented.

- [ ] **Step 4: Run full tests**

Run:

```bash
python -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 5: Regenerate cleaned CSV**

Run:

```bash
python scripts/import_hotel_bookings.py --export-only
```

Expected output includes:

```text
Cleaned CSV written to 数据/cleaned_hotel_bookings.csv
```

- [ ] **Step 6: Verify generated CSV shape and fields**

Run:

```bash
python -X utf8 - <<'PY'
import pandas as pd
from app.data.cleaning import CLEANED_BOOKING_COLUMNS
frame = pd.read_csv('数据/cleaned_hotel_bookings.csv')
print(frame.shape)
print(list(frame.columns) == CLEANED_BOOKING_COLUMNS)
print(frame[['meal_name','is_repeated_guest_label','room_type_changed','required_car_parking_spaces','total_of_special_requests']].head().to_string(index=False))
PY
```

Expected first two lines:

```text
(119390, 41)
True
```

---

### Task 5: Re-import MySQL and verify database shape

**Files:**
- Uses: `scripts/import_hotel_bookings.py`
- Database: local MySQL `hotel_booking_analysis.hotel_bookings`

- [ ] **Step 1: Import regenerated CSV into local MySQL**

Run with the user's confirmed local MySQL credentials:

```bash
python scripts/import_hotel_bookings.py --host 127.0.0.1 --port 3306 --user root --password 123456
```

Expected output includes:

```text
Imported 119390 rows into hotel_booking_analysis.hotel_bookings
```

- [ ] **Step 2: Verify MySQL row count and restored columns**

Run:

```bash
python - <<'PY'
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='hotel_booking_analysis', charset='utf8mb4')
try:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM hotel_bookings')
        print(cur.fetchone()[0])
        cur.execute("SHOW COLUMNS FROM hotel_bookings LIKE 'total_of_special_requests'")
        print(cur.fetchone()[0])
        cur.execute("SHOW COLUMNS FROM hotel_bookings LIKE 'room_type_changed'")
        print(cur.fetchone()[0])
finally:
    conn.close()
PY
```

Expected output:

```text
119390
total_of_special_requests
room_type_changed
```

---

### Self-review

- Spec coverage: implements the user-confirmed 41-column plan, including 10 restored high-value raw fields and 3 derived display/explanation fields.
- Placeholder scan: no TODO/TBD placeholders remain in executable steps.
- Type consistency: column names are consistent across cleaning tests, schema tests, importer tests, CSV generation, and MySQL verification.
