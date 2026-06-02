import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


EVENT_FIELDS = [
    "booking_id",
    "hotel",
    "hotel_name",
    "country_code",
    "country_name",
    "market_segment",
    "customer_type",
    "lead_time",
    "adr",
    "total_guests",
    "total_nights",
    "previous_cancellations",
    "total_of_special_requests",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Append simulated hotel booking events to booking_events.log.")
    parser.add_argument("--csv", type=Path, default=PROJECT_ROOT / "数据" / "cleaned_hotel_bookings.csv")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "realtime" / "events" / "booking_events.log")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--start", type=int, default=0)
    return parser.parse_args(argv)


def build_events(csv_path, count, start):
    frame = pd.read_csv(csv_path)
    sample = frame.iloc[start : start + count]
    events = []
    for _, row in sample.iterrows():
        event = {field: _json_value(row[field]) for field in EVENT_FIELDS if field in row}
        event["business_time"] = _json_value(row.get("event_date"))
        event["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        events.append(event)
    return events


def write_events(events, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as event_file:
        for event in events:
            event_file.write(json.dumps(event, ensure_ascii=False) + "\n")
    return len(events)


def _json_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def main(argv=None):
    args = parse_args(argv)
    events = build_events(args.csv, args.count, args.start)
    written = write_events(events, args.output)
    print(f"Appended {written} booking events to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
