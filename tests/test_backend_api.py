import csv
import json
import pickle
from pathlib import Path

from app import create_app
from app.data.cleaning import CLEANED_BOOKING_COLUMNS


def _write_bookings_csv(path: Path):
    rows = [
        {
            "booking_id": 1,
            "hotel": "City Hotel",
            "hotel_name": "City Hotel",
            "is_canceled": 1,
            "is_canceled_label": "Canceled",
            "lead_time": 120,
            "arrival_date": "2017-01-14",
            "event_date": "2017-01-14",
            "stays_in_weekend_nights": 1,
            "stays_in_week_nights": 2,
            "total_nights": 3,
            "adults": 2,
            "children": 0,
            "babies": 0,
            "total_guests": 2,
            "meal": "BB",
            "meal_name": "Breakfast",
            "country_code": "PRT",
            "country_name": "Portugal",
            "market_segment": "Online TA",
            "market_segment_name": "Online Travel Agent",
            "distribution_channel": "TA/TO",
            "is_repeated_guest": 0,
            "is_repeated_guest_label": "New Guest",
            "previous_cancellations": 1,
            "previous_bookings_not_canceled": 0,
            "reserved_room_type": "A",
            "assigned_room_type": "A",
            "room_type_changed": 0,
            "booking_changes": 0,
            "deposit_type": "No Deposit",
            "deposit_type_name": "No Deposit",
            "days_in_waiting_list": 0,
            "customer_type": "Transient",
            "customer_type_name": "Transient",
            "adr": 100.5,
            "required_car_parking_spaces": 0,
            "total_of_special_requests": 0,
            "reservation_status": "Canceled",
            "reservation_status_date": "2017-01-10",
            "is_deleted": 0,
        },
        {
            "booking_id": 2,
            "hotel": "Resort Hotel",
            "hotel_name": "Resort Hotel",
            "is_canceled": 0,
            "is_canceled_label": "Not Canceled",
            "lead_time": 10,
            "arrival_date": "2017-02-01",
            "event_date": "2017-02-01",
            "stays_in_weekend_nights": 0,
            "stays_in_week_nights": 1,
            "total_nights": 1,
            "adults": 1,
            "children": 1,
            "babies": 0,
            "total_guests": 2,
            "meal": "HB",
            "meal_name": "Half Board",
            "country_code": "GBR",
            "country_name": "United Kingdom",
            "market_segment": "Direct",
            "market_segment_name": "Direct",
            "distribution_channel": "Direct",
            "is_repeated_guest": 1,
            "is_repeated_guest_label": "Repeated Guest",
            "previous_cancellations": 0,
            "previous_bookings_not_canceled": 2,
            "reserved_room_type": "B",
            "assigned_room_type": "C",
            "room_type_changed": 1,
            "booking_changes": 1,
            "deposit_type": "Refundable",
            "deposit_type_name": "Refundable",
            "days_in_waiting_list": 0,
            "customer_type": "Contract",
            "customer_type_name": "Contract",
            "adr": 80,
            "required_car_parking_spaces": 1,
            "total_of_special_requests": 2,
            "reservation_status": "Check-Out",
            "reservation_status_date": "2017-02-02",
            "is_deleted": 0,
        },
        {
            "booking_id": 3,
            "hotel": "City Hotel",
            "hotel_name": "City Hotel",
            "is_canceled": 0,
            "is_canceled_label": "Not Canceled",
            "lead_time": 5,
            "arrival_date": "2017-02-10",
            "event_date": "2017-02-10",
            "stays_in_weekend_nights": 0,
            "stays_in_week_nights": 1,
            "total_nights": 1,
            "adults": 1,
            "children": 0,
            "babies": 0,
            "total_guests": 1,
            "meal": "SC",
            "meal_name": "Self Catering",
            "country_code": "PRT",
            "country_name": "Portugal",
            "market_segment": "Online TA",
            "market_segment_name": "Online Travel Agent",
            "distribution_channel": "TA/TO",
            "is_repeated_guest": 0,
            "is_repeated_guest_label": "New Guest",
            "previous_cancellations": 0,
            "previous_bookings_not_canceled": 0,
            "reserved_room_type": "A",
            "assigned_room_type": "A",
            "room_type_changed": 0,
            "booking_changes": 0,
            "deposit_type": "No Deposit",
            "deposit_type_name": "No Deposit",
            "days_in_waiting_list": 0,
            "customer_type": "Transient",
            "customer_type_name": "Transient",
            "adr": 50,
            "required_car_parking_spaces": 0,
            "total_of_special_requests": 1,
            "reservation_status": "Check-Out",
            "reservation_status_date": "2017-02-11",
            "is_deleted": 1,
        },
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CLEANED_BOOKING_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _client(tmp_path):
    csv_path = tmp_path / "bookings.csv"
    _write_bookings_csv(csv_path)
    app = create_app({"TESTING": True, "BOOKING_DATA_SOURCE": "csv", "BOOKING_DATA_CSV": str(csv_path), "REDIS_ENABLED": False})
    return app.test_client()


class FakeCancellationModel:
    def __init__(self, probability):
        self.probability = probability

    def predict_proba(self, frame):
        assert list(frame.columns) == [
            "hotel",
            "lead_time",
            "total_nights",
            "adults",
            "children",
            "babies",
            "total_guests",
            "meal",
            "country_code",
            "market_segment",
            "distribution_channel",
            "is_repeated_guest",
            "previous_cancellations",
            "previous_bookings_not_canceled",
            "reserved_room_type",
            "assigned_room_type",
            "room_type_changed",
            "booking_changes",
            "deposit_type",
            "days_in_waiting_list",
            "customer_type",
            "adr",
            "required_car_parking_spaces",
            "total_of_special_requests",
        ]
        return [[1 - self.probability, self.probability]]


def _write_model_artifacts(model_dir: Path, probability=0.72):
    model_dir.mkdir()
    (model_dir / "feature_columns.json").write_text(
        json.dumps(
            [
                "hotel",
                "lead_time",
                "total_nights",
                "adults",
                "children",
                "babies",
                "total_guests",
                "meal",
                "country_code",
                "market_segment",
                "distribution_channel",
                "is_repeated_guest",
                "previous_cancellations",
                "previous_bookings_not_canceled",
                "reserved_room_type",
                "assigned_room_type",
                "room_type_changed",
                "booking_changes",
                "deposit_type",
                "days_in_waiting_list",
                "customer_type",
                "adr",
                "required_car_parking_spaces",
                "total_of_special_requests",
            ]
        ),
        encoding="utf-8",
    )
    (model_dir / "metrics.json").write_text(
        json.dumps(
            {
                "selected_model": "random_forest",
                "model_version": "random_forest_v1",
                "metrics": {
                    "accuracy": 0.87,
                    "precision_score": 0.82,
                    "recall_score": 0.83,
                    "f1_score": 0.825,
                    "train_score": 0.91,
                    "test_score": 0.87,
                },
                "comparison": {
                    "random_forest": {
                        "accuracy": 0.87,
                        "precision_score": 0.82,
                        "recall_score": 0.83,
                        "f1_score": 0.825,
                    }
                },
                "confusion_matrix": [[13482, 1551], [1536, 7309]],
            }
        ),
        encoding="utf-8",
    )
    with (model_dir / "cancellation_model.pkl").open("wb") as model_file:
        pickle.dump(FakeCancellationModel(probability), model_file)


def _client_with_model(tmp_path, probability=0.72):
    csv_path = tmp_path / "bookings.csv"
    model_dir = tmp_path / "models"
    _write_bookings_csv(csv_path)
    _write_model_artifacts(model_dir, probability)
    app = create_app(
        {
            "TESTING": True,
            "BOOKING_DATA_SOURCE": "csv",
            "BOOKING_DATA_CSV": str(csv_path),
            "REDIS_ENABLED": False,
            "PREDICTION_MODEL_DIR": str(model_dir),
        }
    )
    return app.test_client()


def test_filter_options_return_contract_shape(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/bookings/filter-options")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert set(payload["data"]) == {
        "hotels",
        "countries",
        "market_segments",
        "customer_types",
        "cancel_statuses",
    }
    assert {"value": "City Hotel", "label": "City Hotel"} in payload["data"]["hotels"]
    assert {"value": 1, "label": "Canceled"} in payload["data"]["cancel_statuses"]


def test_bookings_list_filters_paginates_and_excludes_deleted_rows(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/bookings?hotel=City%20Hotel&page=1&page_size=5")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["pagination"] == {
        "page": 1,
        "page_size": 5,
        "total": 1,
        "total_pages": 1,
    }
    assert payload["data"]["items"][0]["booking_id"] == 1
    assert "is_deleted" not in payload["data"]["items"][0]


def test_dashboard_summary_uses_fixed_offline_base_when_realtime_waiting(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/dashboard/summary")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["offline_base_rows"] == 80008
    assert payload["data"]["realtime_processed_count"] == 0
    assert payload["data"]["total_bookings"] == 80008
    assert payload["data"]["high_risk_count"] == 0
    assert payload["data"]["average_cancel_probability"] == 0.0
    assert payload["data"]["status"] == "waiting"


def test_visualization_overview_returns_contract_sections(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/visualization/overview?country_code=PRT")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["filters"]["country_code"] == "PRT"
    assert payload["data"]["summary"]["booking_count"] == 1
    assert set(payload["data"]) == {
        "filters",
        "summary",
        "trend",
        "cancel_structure",
        "factor_bars",
        "channel_ranking",
        "country_map",
        "risk_tags",
        "sample_orders",
    }


def test_prediction_single_uses_real_model_artifact_and_keeps_contract(tmp_path):
    client = _client_with_model(tmp_path, probability=0.72)

    response = client.post("/api/prediction/single", json={"booking_id": 1})

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["booking_id"] == 1
    assert payload["data"]["model_version"] == "random_forest_v1"
    assert payload["data"]["cancel_probability"] == 0.72
    assert payload["data"]["predicted_label"] == 1
    assert payload["data"]["risk_level"] == "high"
    assert payload["data"]["risk_level_name"] == "high_risk"
    assert "lead_time_high" in payload["data"]["reason_tags"]


def test_model_metrics_reads_training_artifact_and_formats_frontend_contract(tmp_path):
    client = _client_with_model(tmp_path)

    response = client.get("/api/prediction/model-metrics")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["selected_model"] == {
        "model_name": "random_forest",
        "model_version": "random_forest_v1",
        "is_selected": 1,
        "reason": "selected by training pipeline",
    }
    assert payload["data"]["metrics"]["f1_score"] == 0.825
    assert payload["data"]["model_comparison"] == [
        {
            "model_name": "random_forest",
            "accuracy": 0.87,
            "precision_score": 0.82,
            "recall_score": 0.83,
            "f1_score": 0.825,
        }
    ]
    assert payload["data"]["confusion_matrix"] == {
        "true_negative": 13482,
        "false_positive": 1551,
        "false_negative": 1536,
        "true_positive": 7309,
    }


def test_prediction_batch_records_returns_waiting_without_stub_data(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/prediction/batch-records?page=1&page_size=10")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"] == {
        "items": [],
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total": 0,
            "total_pages": 0,
        },
        "status": "waiting",
        "message": "绛夊緟瀹炴椂閾捐矾鏁版嵁",
    }


def test_api_module_no_longer_contains_stub_prediction_helpers():
    api_source = (Path(__file__).resolve().parents[1] / "app" / "api.py").read_text(encoding="utf-8")

    assert "_stub_probability" not in api_source
    assert "_stub_model_metrics" not in api_source
    assert "stub-2017-02" not in api_source


def test_booking_detail_returns_contract_fields(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/bookings/1")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["booking_id"] == 1
    assert payload["data"]["meal_name"] == "Breakfast"
    assert payload["data"]["reservation_status_date"] == "2017-01-10"


def test_booking_update_allows_only_demo_fields(tmp_path):
    client = _client(tmp_path)

    response = client.put(
        "/api/bookings/1",
        json={
            "customer_type": "Contract",
            "market_segment": "Direct",
            "deposit_type": "Refundable",
            "adr": 120.5,
            "total_of_special_requests": 1,
            "is_canceled": 0,
        },
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload == {
        "success": True,
        "data": {"booking_id": 1, "updated": True},
        "message": "booking updated",
    }


def test_booking_delete_marks_logical_delete(tmp_path):
    client = _client(tmp_path)

    response = client.delete("/api/bookings/1")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload == {
        "success": True,
        "data": {"booking_id": 1, "is_deleted": 1},
        "message": "booking deleted",
    }


def test_realtime_summary_returns_waiting_state_without_live_data(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/realtime/summary")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["processed_count"] == 0
    assert payload["data"]["status"] == "waiting"
    assert payload["data"]["message"] == "等待实时链路数据"


def test_realtime_trend_returns_echarts_contract_without_stub_points(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/realtime/trend?granularity=week")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["granularity"] == "week"
    assert payload["data"]["labels"] == []
    assert payload["data"]["inflow"] == []
    assert payload["data"]["predicted_cancellations"] == []
    assert payload["data"]["cancel_rate"] == []
    assert payload["data"]["status"] == "waiting"


def test_realtime_recent_predictions_returns_empty_waiting_state_without_stub(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/realtime/recent-predictions")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"] == {"items": [], "status": "waiting", "message": "等待实时链路数据"}


def test_realtime_risk_and_service_status_endpoints_are_not_static_mocks(tmp_path):
    client = _client(tmp_path)

    country_response = client.get("/api/realtime/country-risk")
    channel_response = client.get("/api/realtime/channel-risk")
    status_response = client.get("/api/system/service-status")

    assert country_response.get_json()["data"] == {"items": [], "status": "waiting", "message": "等待实时链路数据"}
    assert channel_response.get_json()["data"] == {"items": [], "status": "waiting", "message": "等待实时链路数据"}
    assert status_response.get_json()["data"]["services"]["flask"] == "running"
    assert status_response.get_json()["data"]["services"]["redis"] == "disabled"


def _chart_options(payload):
    assert payload["success"] is True
    options = payload["data"]["options"]
    assert isinstance(options, str)
    return json.loads(options)


def test_dashboard_trend_chart_options_accept_granularity_and_wait_without_fake_points(tmp_path):
    client = _client(tmp_path)

    for granularity in ("day", "week", "month"):
        response = client.get(f"/api/charts/dashboard-trend?granularity={granularity}")
        payload = response.get_json()
        options = _chart_options(payload)

        assert response.status_code == 200
        assert payload["data"]["chart_type"] == "line"
        assert payload["data"]["status"] == "waiting"
        assert payload["data"]["source"] == "none"
        assert payload["data"]["message"] == "等待实时链路数据"
        assert options["xAxis"][0]["data"] == []
        assert all(series["data"] == [] for series in options["series"])


def test_realtime_trend_chart_options_use_same_waiting_contract(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/charts/realtime-trend?granularity=month")
    payload = response.get_json()
    options = _chart_options(payload)

    assert response.status_code == 200
    assert payload["data"]["chart_type"] == "line"
    assert payload["data"]["status"] == "waiting"
    assert options["xAxis"][0]["data"] == []
    assert all(series["data"] == [] for series in options["series"])


def test_risk_chart_options_wait_without_static_mock_data(tmp_path):
    client = _client(tmp_path)

    country_response = client.get("/api/charts/dashboard-country-risk")
    channel_response = client.get("/api/charts/dashboard-channel-risk")
    country_payload = country_response.get_json()
    channel_payload = channel_response.get_json()
    country_options = _chart_options(country_payload)
    channel_options = _chart_options(channel_payload)

    assert country_payload["data"]["chart_type"] == "bar"
    assert channel_payload["data"]["chart_type"] == "pie"
    assert country_payload["data"]["status"] == "waiting"
    assert channel_payload["data"]["status"] == "waiting"
    assert country_options["xAxis"][0]["data"] == []
    assert country_options["series"][0]["data"] == []
    assert channel_options.get("series", []) == []


def test_model_metric_chart_options_are_generated_from_training_metrics(tmp_path):
    client = _client_with_model(tmp_path)

    response = client.get("/api/charts/model-metrics")
    payload = response.get_json()
    options = _chart_options(payload)

    assert response.status_code == 200
    assert payload["data"]["chart_type"] == "bar"
    assert payload["data"]["status"] == "running"
    assert options["xAxis"][0]["data"] == ["accuracy", "precision_score", "recall_score", "f1_score"]
    assert options["series"][0]["data"] == [0.87, 0.82, 0.83, 0.825]


def test_confusion_matrix_chart_options_are_generated_from_training_metrics(tmp_path):
    client = _client_with_model(tmp_path)

    response = client.get("/api/charts/confusion-matrix")
    payload = response.get_json()
    options = _chart_options(payload)

    assert response.status_code == 200
    assert payload["data"]["chart_type"] == "heatmap"
    assert payload["data"]["status"] == "running"
    assert sorted(options["series"][0]["data"]) == sorted(
        [[0, 0, 13482], [1, 0, 1551], [0, 1, 1536], [1, 1, 7309]]
    )
