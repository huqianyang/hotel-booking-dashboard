# Historical Data Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested historical data import flow that cleans `hotel_bookings.csv`, writes a cleaned CSV, and imports it into the MySQL `hotel_bookings` table.

**Architecture:** Reuse `app.data.cleaning.clean_hotel_bookings()` as the only source of cleaned booking fields. Add `app.database.importer` for reusable export/import functions and `scripts/import_hotel_bookings.py` as a thin CLI wrapper. Keep MySQL schema ownership in `app.database.schema` so field order and table SQL do not drift.

**Tech Stack:** Python, pandas, PyMySQL, pytest, existing Flask project structure.

---

### Task 1: Importer behavior tests

**Files:**
- Create: `tests/test_hotel_booking_importer.py`
- Read-only reference: `app/data/cleaning.py`
- Read-only reference: `app/database/schema.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_hotel_booking_importer.py` with:

```python
from pathlib import Path

import pandas as pd

from app.data.cleaning import CLEANED_BOOKING_COLUMNS
from app.database.importer import (
    build_insert_sql,
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


def test_build_insert_sql_matches_cleaned_columns():
    sql = build_insert_sql()

    assert sql.startswith("INSERT INTO hotel_bookings (")
    assert ", ".join(CLEANED_BOOKING_COLUMNS) in sql
    assert sql.count("%s") == len(CLEANED_BOOKING_COLUMNS)
    assert sql.endswith(")")


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.batches = []

    def execute(self, sql):
        self.executed.append(sql)

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
    assert connection.commits == 1
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m pytest tests/test_hotel_booking_importer.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.database.importer'`.

---

### Task 2: Minimal importer implementation

**Files:**
- Create: `app/database/importer.py`
- Test: `tests/test_hotel_booking_importer.py`

- [ ] **Step 1: Implement minimal importer module**

Create `app/database/importer.py` with:

```python
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

        insert_sql = build_insert_sql()
        for start in range(0, len(rows), batch_size):
            cursor.executemany(insert_sql, rows[start : start + batch_size])

    connection.commit()
    return len(rows)
```

- [ ] **Step 2: Run importer tests to verify GREEN**

Run:

```bash
python -m pytest tests/test_hotel_booking_importer.py -v
```

Expected: PASS.

---

### Task 3: CLI wrapper tests

**Files:**
- Create: `scripts/import_hotel_bookings.py`
- Modify: `tests/test_hotel_booking_importer.py`

- [ ] **Step 1: Add failing CLI argument test**

Append to `tests/test_hotel_booking_importer.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m pytest tests/test_hotel_booking_importer.py::test_parse_args_uses_project_default_paths -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts'` or `No module named 'scripts.import_hotel_bookings'`.

- [ ] **Step 3: Implement minimal CLI**

Create `scripts/import_hotel_bookings.py` with:

```python
import argparse
from pathlib import Path

import pymysql

from app.database.importer import export_cleaned_bookings_csv, import_cleaned_bookings
from app.database.schema import DATABASE_NAME


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Clean hotel bookings CSV and import it into MySQL.")
    parser.add_argument("--raw-csv", type=Path, default=Path("hotel_bookings.csv"))
    parser.add_argument("--cleaned-csv", type=Path, default=Path("数据/cleaned_hotel_bookings.csv"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password")
    parser.add_argument("--export-only", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    export_cleaned_bookings_csv(args.raw_csv, args.cleaned_csv)

    if args.export_only:
        print(f"Cleaned CSV written to {args.cleaned_csv}")
        return 0

    connection = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        imported = import_cleaned_bookings(connection, args.cleaned_csv)
    finally:
        connection.close()

    print(f"Imported {imported} rows into {DATABASE_NAME}.hotel_bookings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI test to verify GREEN**

Run:

```bash
python -m pytest tests/test_hotel_booking_importer.py::test_parse_args_uses_project_default_paths -v
```

Expected: PASS.

---

### Task 4: Full verification and generated CSV check

**Files:**
- Generated: `数据/cleaned_hotel_bookings.csv`
- Test: all existing tests

- [ ] **Step 1: Run all tests**

Run:

```bash
python -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Generate cleaned CSV without touching MySQL**

Run:

```bash
python scripts/import_hotel_bookings.py --export-only
```

Expected output includes:

```text
Cleaned CSV written to 数据/cleaned_hotel_bookings.csv
```

- [ ] **Step 3: Verify generated CSV shape**

Run:

```bash
python -X utf8 - <<'PY'
import pandas as pd
from app.data.cleaning import CLEANED_BOOKING_COLUMNS
frame = pd.read_csv('数据/cleaned_hotel_bookings.csv')
print(frame.shape)
print(list(frame.columns) == CLEANED_BOOKING_COLUMNS)
PY
```

Expected output:

```text
(119390, 28)
True
```

- [ ] **Step 4: Optional local MySQL import**

Only run when MySQL is available and the user confirms credentials:

```bash
python scripts/import_hotel_bookings.py --host 127.0.0.1 --port 3306 --user root --password YOUR_PASSWORD
```

Expected output includes:

```text
Imported 119390 rows into hotel_booking_analysis.hotel_bookings
```

---

### Self-review

- Spec coverage: covers cleaning raw `hotel_bookings.csv`, outputting cleaned CSV, and implementing a MySQL import path for `hotel_bookings`.
- Placeholder scan: no TODO/TBD placeholders remain in executable steps.
- Type consistency: tests and implementation consistently use `Path`, `CLEANED_BOOKING_COLUMNS`, `build_insert_sql()`, `export_cleaned_bookings_csv()`, and `import_cleaned_bookings()`.
