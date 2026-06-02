from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

from app.database.mysql import MySQLConfig
from app.services.booking_repository import MySQLBookingRepository


class FakeCursor:
    def __init__(self, fetch_results):
        self.fetch_results = list(fetch_results)
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params or ()))

    def fetchall(self):
        return self.fetch_results.pop(0)

    def fetchone(self):
        return self.fetch_results.pop(0)


class FakeClient:
    def __init__(self, fetch_results):
        self.cursor_obj = FakeCursor(fetch_results)

    @contextmanager
    def cursor(self):
        yield self.cursor_obj


def test_mysql_config_reads_flask_overrides():
    config = MySQLConfig.from_flask_config(
        {
            "MYSQL_HOST": "db.local",
            "MYSQL_PORT": 3307,
            "MYSQL_USER": "hotel",
            "MYSQL_PASSWORD": "secret",
            "MYSQL_DATABASE": "hotel_booking_analysis",
        }
    )

    assert config.host == "db.local"
    assert config.port == 3307
    assert config.user == "hotel"
    assert config.password == "secret"
    assert config.database == "hotel_booking_analysis"


def test_mysql_repository_filters_paginates_and_excludes_deleted_rows():
    client = FakeClient(
        [
            [{"total": 1}],
            [
                {
                    "booking_id": 1,
                    "hotel": "City Hotel",
                    "hotel_name": "City Hotel",
                    "is_canceled": 1,
                    "is_canceled_label": "Canceled",
                    "arrival_date": "2017-01-14",
                    "country_code": "PRT",
                    "country_name": "Portugal",
                    "market_segment": "Online TA",
                    "market_segment_name": "Online Travel Agent",
                    "customer_type": "Transient",
                    "customer_type_name": "Transient",
                    "lead_time": 120,
                    "total_guests": 2,
                    "total_nights": 3,
                    "adr": 100.5,
                }
            ],
        ]
    )
    repository = MySQLBookingRepository(client)

    result = repository.paginated_bookings(
        {"hotel": "City Hotel", "country_code": "PRT"},
        page=1,
        page_size=5,
    )

    count_sql, count_params = client.cursor_obj.statements[0]
    list_sql, list_params = client.cursor_obj.statements[1]
    assert "is_deleted = 0" in count_sql
    assert "hotel = %s" in count_sql
    assert "country_code = %s" in count_sql
    assert count_params == ("City Hotel", "PRT")
    assert "LIMIT %s OFFSET %s" in list_sql
    assert list_params == ("City Hotel", "PRT", 5, 0)
    assert result["pagination"]["total"] == 1
    assert result["items"][0]["booking_id"] == 1


def test_mysql_repository_serializes_date_and_decimal_values_for_api_contract():
    client = FakeClient(
        [
            [{"total": 1}],
            [
                {
                    "booking_id": 1,
                    "hotel": "City Hotel",
                    "hotel_name": "City Hotel",
                    "is_canceled": 0,
                    "is_canceled_label": "Not Canceled",
                    "arrival_date": date(2017, 1, 14),
                    "country_code": "PRT",
                    "country_name": "Portugal",
                    "market_segment": "Online TA",
                    "market_segment_name": "Online Travel Agent",
                    "customer_type": "Transient",
                    "customer_type_name": "Transient",
                    "lead_time": 120,
                    "total_guests": 2,
                    "total_nights": 3,
                    "adr": Decimal("100.50"),
                }
            ],
        ]
    )
    repository = MySQLBookingRepository(client)

    result = repository.paginated_bookings({}, page=1, page_size=5)

    assert result["items"][0]["arrival_date"] == "2017-01-14"
    assert result["items"][0]["adr"] == 100.5


def test_mysql_repository_updates_only_allowed_fields_and_logically_deletes():
    client = FakeClient([[{"affected": 1}], [{"affected": 1}]])
    repository = MySQLBookingRepository(client)

    updated = repository.update_booking(
        1,
        {
            "customer_type": "Contract",
            "market_segment": "Direct",
            "is_canceled": 0,
        },
    )
    deleted = repository.logical_delete_booking(1)

    update_sql, update_params = client.cursor_obj.statements[0]
    delete_sql, delete_params = client.cursor_obj.statements[1]
    assert updated is True
    assert "customer_type = %s" in update_sql
    assert "market_segment = %s" in update_sql
    assert "is_canceled" not in update_sql
    assert update_params == ("Contract", "Direct", 1)
    assert deleted is True
    assert delete_sql == "UPDATE hotel_bookings SET is_deleted = 1 WHERE booking_id = %s"
    assert delete_params == (1,)


def test_mysql_repository_returns_storm_prediction_batch_records():
    client = FakeClient(
        [
            [{"total": 1}],
            [
                {
                    "batch_id": "storm-2017-01-13",
                    "business_date": date(2017, 1, 13),
                    "time_window": "00:00:00-23:59:59",
                    "total_count": 25,
                    "predicted_cancel_count": 8,
                    "high_risk_count": 5,
                    "avg_cancel_probability": Decimal("0.4267"),
                    "source": "storm",
                    "created_at": datetime(2017, 1, 13, 23, 59, 59),
                }
            ],
        ]
    )
    repository = MySQLBookingRepository(client)

    result = repository.latest_prediction_batches(page=1, page_size=10)

    count_sql, count_params = client.cursor_obj.statements[0]
    list_sql, list_params = client.cursor_obj.statements[1]
    assert "prediction_results" in count_sql
    assert "source = %s" in count_sql
    assert count_params == ("storm",)
    assert "prediction_results" in list_sql
    assert "GROUP BY DATE(predicted_at), source" in list_sql
    assert list_params == ("storm", 10, 0)
    assert result["items"] == [
        {
            "batch_id": "storm-2017-01-13",
            "business_date": "2017-01-13",
            "time_window": "00:00:00-23:59:59",
            "total_count": 25,
            "predicted_cancel_count": 8,
            "high_risk_count": 5,
            "avg_cancel_probability": 0.4267,
            "source": "storm",
            "created_at": "2017-01-13 23:59:59",
        }
    ]
    assert result["pagination"]["total"] == 1
    assert result["status"] == "running"
