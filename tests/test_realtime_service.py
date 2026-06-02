import json

import pandas as pd

from app.services.realtime_service import RealtimeService


class FakeRedis:
    def __init__(self, values=None):
        self.values = values or {}
        self.ping_called = False

    def get(self, key):
        return self.values.get(key)

    def ping(self):
        self.ping_called = True
        return True


class FakeRepository:
    def __init__(self):
        self.active_bookings_called = False

    def active_bookings(self):
        self.active_bookings_called = True
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

    def latest_realtime_summary(self):
        return None

    def latest_storm_predictions(self, limit=10):
        return []

    def latest_realtime_trend(self, granularity="day"):
        return None

    def latest_realtime_risk(self, metric_type):
        return []

    def ping(self):
        return True


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


def test_dashboard_summary_uses_offline_base_plus_redis_processed_count():
    repository = FakeRepository()
    service = RealtimeService(
        repository=repository,
        redis_client=FakeRedis(
            {
                "realtime:summary": json.dumps(
                    {
                        "processed_count": 12,
                        "high_risk_count": 4,
                        "average_cancel_probability": 0.37,
                        "updated_at": "2017-01-13 00:05:00",
                    }
                )
            }
        ),
    )

    summary = service.dashboard_summary()

    assert summary["offline_base_rows"] == 80008
    assert summary["realtime_processed_count"] == 12
    assert summary["total_bookings"] == 80020
    assert summary["high_risk_count"] == 4
    assert summary["average_cancel_probability"] == 0.37
    assert summary["updated_at"] == "2017-01-13 00:05:00"
    assert repository.active_bookings_called is False


def test_realtime_service_falls_back_to_mysql_summary_without_history_stub():
    class Repository(FakeRepository):
        def latest_realtime_summary(self):
            return {
                "processed_count": 7,
                "high_risk_count": 2,
                "average_cancel_probability": 0.41,
                "updated_at": "2017-01-13 00:10:00",
            }

    service = RealtimeService(repository=Repository(), redis_client=FakeRedis())

    summary = service.dashboard_summary()

    assert summary["realtime_processed_count"] == 7
    assert summary["total_bookings"] == 80015
    assert summary["status"] == "mysql_fallback"


def test_realtime_service_returns_waiting_state_when_no_realtime_data():
    repository = FakeRepository()
    service = RealtimeService(repository=repository, redis_client=FakeRedis())

    summary = service.dashboard_summary()

    assert summary["realtime_processed_count"] == 0
    assert summary["total_bookings"] == 80008
    assert summary["status"] == "waiting"
    assert "等待实时链路数据" in summary["message"]
    assert repository.active_bookings_called is False


def test_dashboard_summary_preserves_redis_waiting_status():
    service = RealtimeService(
        repository=FakeRepository(),
        redis_client=FakeRedis(
            {
                "realtime:summary": json.dumps(
                    {
                        "processed_count": 0,
                        "status": "waiting",
                        "message": "等待实时链路数据",
                    }
                )
            }
        ),
    )

    summary = service.dashboard_summary()

    assert summary["status"] == "waiting"
    assert summary["message"] == "等待实时链路数据"


def test_recent_predictions_reads_redis_then_returns_empty_when_no_data():
    service = RealtimeService(
        repository=FakeRepository(),
        redis_client=FakeRedis(
            {
                "realtime:recent_predictions": json.dumps(
                    {
                        "items": [
                            {
                                "booking_id": 9,
                                "cancel_probability": 0.74,
                                "risk_level_name": "high_risk",
                                "business_time": "2017-01-13 00:01:00",
                            }
                        ]
                    }
                )
            }
        ),
    )

    assert service.recent_predictions()["items"][0]["booking_id"] == 9
    assert RealtimeService(FakeRepository(), FakeRedis()).recent_predictions() == {
        "items": [],
        "status": "waiting",
        "message": "等待实时链路数据",
    }


def test_trend_supports_granularity_and_echarts_series_from_redis():
    service = RealtimeService(
        repository=FakeRepository(),
        redis_client=FakeRedis(
            {
                "realtime:trend": json.dumps(
                    {
                        "day": [
                            {
                                "label": "2017-01-13",
                                "inflow": 10,
                                "predicted_cancellations": 3,
                                "cancel_rate": 0.3,
                            }
                        ]
                    }
                )
            }
        ),
    )

    trend = service.trend("day")

    assert trend["granularity"] == "day"
    assert trend["labels"] == ["2017-01-13"]
    assert trend["inflow"] == [10]
    assert trend["predicted_cancellations"] == [3]
    assert trend["cancel_rate"] == [0.3]


def test_country_and_channel_risk_read_redis_without_static_mock():
    service = RealtimeService(
        repository=FakeRepository(),
        redis_client=FakeRedis(
            {
                "realtime:country_risk": json.dumps([{"name": "Portugal", "value": 0.67}]),
                "realtime:channel_risk": json.dumps([{"name": "Online TA", "value": 0.52}]),
            }
        ),
    )

    assert service.country_risk()["items"] == [{"name": "Portugal", "value": 0.67}]
    assert service.channel_risk()["items"] == [{"name": "Online TA", "value": 0.52}]


def test_service_status_combines_real_connections_and_link_status():
    service = RealtimeService(
        repository=FakeRepository(),
        redis_client=FakeRedis(
            {"realtime:link_status": json.dumps({"flume": "running", "kafka": "pending", "storm": "pending"})}
        ),
    )

    assert service.service_status()["services"] == {
        "flask": "running",
        "mysql": "running",
        "redis": "running",
        "flume": "running",
        "kafka": "pending",
        "storm": "pending",
    }
