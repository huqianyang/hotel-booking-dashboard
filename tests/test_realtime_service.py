import json

import pandas as pd

from app.services.realtime_service import RealtimeService


class FakeRedis:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key):
        return self.values.get(key)


class FakeRepository:
    def active_bookings(self):
        return pd.DataFrame(
            [
                {
                    "booking_id": 1,
                    "hotel_name": "City Hotel",
                    "country_name": "Portugal",
                    "event_date": pd.Timestamp("2017-01-01"),
                    "is_canceled": 1,
                    "lead_time": 120,
                    "previous_cancellations": 1,
                    "total_of_special_requests": 0,
                    "deposit_type": "No Deposit",
                },
                {
                    "booking_id": 2,
                    "hotel_name": "Resort Hotel",
                    "country_name": "United Kingdom",
                    "event_date": pd.Timestamp("2017-01-02"),
                    "is_canceled": 0,
                    "lead_time": 10,
                    "previous_cancellations": 0,
                    "total_of_special_requests": 2,
                    "deposit_type": "Refundable",
                },
            ]
        )


def test_realtime_service_reads_summary_from_redis_first():
    service = RealtimeService(
        repository=FakeRepository(),
        redis_client=FakeRedis(
            {
                "realtime:summary": json.dumps(
                    {
                        "processed_count": 9,
                        "latest_business_time": "2017-01-09 00:00:00",
                        "latest_cancel_rate": 0.4,
                        "latest_high_risk_count": 3,
                        "service_status": {
                            "mysql": "running",
                            "redis": "running",
                            "flume": "pending",
                            "kafka": "pending",
                            "storm": "pending",
                        },
                    }
                )
            }
        ),
    )

    assert service.summary()["processed_count"] == 9
    assert service.summary()["service_status"]["redis"] == "running"


def test_realtime_service_falls_back_to_repository_when_redis_empty():
    service = RealtimeService(repository=FakeRepository(), redis_client=FakeRedis())

    assert service.summary()["processed_count"] == 2
    assert service.summary()["latest_cancel_rate"] == 0.5
    assert service.trend()["points"][0]["business_time"] == "2017-01-01 00:00:00"
    assert service.recent_predictions()["items"][0]["booking_id"] == 1
    assert service.recent_predictions()["items"][0]["cancel_probability"] == 0.85
