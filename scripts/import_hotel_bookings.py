import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
