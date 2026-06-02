import json
from pathlib import Path

import pandas as pd

from scripts.generate_realtime_events import build_events, write_events


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
