import json
from pathlib import Path

import pandas as pd

from scripts.generate_realtime_events import build_events, write_events


def test_build_events_uses_realtime_arrival_date_boundary(tmp_path):
    csv_path = tmp_path / "bookings.csv"
    pd.DataFrame(
        [
            {
                "booking_id": 1,
                "hotel": "City Hotel",
                "hotel_name": "City Hotel",
                "country_code": "PRT",
                "country_name": "Portugal",
                "market_segment": "Online TA",
                "customer_type": "Transient",
                "lead_time": 120,
                "adr": 100.5,
                "total_guests": 2,
                "total_nights": 3,
                "previous_cancellations": 1,
                "total_of_special_requests": 0,
                "arrival_date": "2017-01-12",
                "event_date": "2017-01-12",
            },
            {
                "booking_id": 2,
                "hotel": "Resort Hotel",
                "hotel_name": "Resort Hotel",
                "country_code": "GBR",
                "country_name": "United Kingdom",
                "market_segment": "Direct",
                "customer_type": "Contract",
                "lead_time": 15,
                "adr": 88.0,
                "total_guests": 1,
                "total_nights": 2,
                "previous_cancellations": 0,
                "total_of_special_requests": 2,
                "arrival_date": "2017-01-13",
                "event_date": "2017-01-13",
            },
            {
                "booking_id": 3,
                "hotel": "City Hotel",
                "hotel_name": "City Hotel",
                "country_code": "FRA",
                "country_name": "France",
                "market_segment": "Groups",
                "customer_type": "Transient",
                "lead_time": 90,
                "adr": 110.0,
                "total_guests": 2,
                "total_nights": 4,
                "previous_cancellations": 0,
                "total_of_special_requests": 1,
                "arrival_date": "2017-01-14",
                "event_date": "2017-01-14",
            },
        ]
    ).to_csv(csv_path, index=False)

    events = build_events(Path(csv_path), count=2, start=0)

    assert [event["booking_id"] for event in events] == [2, 3]
    assert [event["business_time"] for event in events] == ["2017-01-13", "2017-01-14"]


def test_generate_realtime_events_writes_json_lines(tmp_path):
    csv_path = tmp_path / "bookings.csv"
    output_path = tmp_path / "booking_events.log"
    pd.DataFrame(
        [
            {
                "booking_id": 1,
                "hotel": "City Hotel",
                "hotel_name": "City Hotel",
                "country_code": "PRT",
                "country_name": "Portugal",
                "market_segment": "Online TA",
                "customer_type": "Transient",
                "lead_time": 120,
                "adr": 100.5,
                "total_guests": 2,
                "total_nights": 3,
                "previous_cancellations": 1,
                "total_of_special_requests": 0,
                "arrival_date": "2017-01-14",
                "event_date": "2017-01-14",
            }
        ]
    ).to_csv(csv_path, index=False)

    events = build_events(Path(csv_path), count=1, start=0)
    written = write_events(events, output_path)

    assert written == 1
    line = output_path.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["booking_id"] == 1
    assert payload["business_time"] == "2017-01-14"
    assert payload["generated_at"]
