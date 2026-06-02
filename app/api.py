from pathlib import Path

from flask import current_app, jsonify, request

from app.database.mysql import MySQLClient, MySQLConfig
from app.redis_client import RedisClient
from app.services.booking_repository import (
    DETAIL_FIELDS,
    LIST_FIELDS,
    SAMPLE_ORDER_FIELDS,
    BookingRepository,
    MySQLBookingRepository,
    option_pairs,
)
from app.services.chart_options_service import ChartOptionsService
from app.services.prediction_service import PredictionService
from app.services.realtime_service import RealtimeService


def register_api_routes(app):
    @app.get("/api/bookings/filter-options")
    def filter_options():
        repository = _repository()
        frame = repository.active_bookings()
        data = {
            "hotels": option_pairs(frame, "hotel", "hotel_name"),
            "countries": option_pairs(frame, "country_code", "country_name"),
            "market_segments": option_pairs(frame, "market_segment", "market_segment_name"),
            "customer_types": option_pairs(frame, "customer_type", "customer_type_name"),
            "cancel_statuses": option_pairs(frame, "is_canceled", "is_canceled_label"),
        }
        return _ok(data)

    @app.get("/api/bookings")
    def bookings():
        result = _repository().paginated_bookings(
            _booking_filters(),
            page=request.args.get("page", 1),
            page_size=request.args.get("page_size", 20),
            fields=LIST_FIELDS,
        )
        return _ok(result)

    @app.get("/api/bookings/<int:booking_id>")
    def booking_detail(booking_id):
        booking = _repository().get_booking(booking_id)
        if not booking:
            return _fail("booking not found", 404)
        return _ok({field: booking.get(field) for field in DETAIL_FIELDS})

    @app.put("/api/bookings/<int:booking_id>")
    def booking_update(booking_id):
        updated = _repository().update_booking(booking_id, request.get_json(silent=True) or {})
        if not updated:
            return _fail("booking not found", 404)
        return _ok({"booking_id": booking_id, "updated": True}, "booking updated")

    @app.delete("/api/bookings/<int:booking_id>")
    def booking_delete(booking_id):
        deleted = _repository().logical_delete_booking(booking_id)
        if not deleted:
            return _fail("booking not found", 404)
        return _ok({"booking_id": booking_id, "is_deleted": 1}, "booking deleted")

    @app.get("/api/dashboard/summary")
    def dashboard_summary():
        return _ok(_realtime_service().dashboard_summary())

    @app.get("/api/dashboard/trend")
    def dashboard_trend():
        granularity = request.args.get("granularity", "day")
        return _ok(_realtime_service().trend(granularity))

    @app.get("/api/visualization/overview")
    def visualization_overview():
        return _ok(_visualization_overview_data())

    @app.get("/api/prediction/candidate-bookings")
    def candidate_bookings():
        result = _repository().paginated_bookings(
            {"keyword": request.args.get("keyword")},
            page=request.args.get("page", 1),
            page_size=request.args.get("page_size", 10),
            fields=[
                "booking_id",
                "hotel_name",
                "arrival_date",
                "country_name",
                "lead_time",
                "adr",
                "customer_type_name",
            ],
        )
        return _ok(result)

    @app.post("/api/prediction/single")
    def prediction_single():
        payload = request.get_json(silent=True) or {}
        booking_id = payload.get("booking_id")
        if booking_id is None:
            return _fail("booking_id is required", 400)
        booking = _repository().get_booking(booking_id)
        if not booking:
            return _fail("booking not found", 404)
        data = _prediction_service().predict_booking(booking)
        return _ok(data, "prediction completed")

    @app.get("/api/prediction/model-metrics")
    def model_metrics():
        return _ok(_prediction_service().model_metrics())

    @app.get("/api/prediction/batch-records")
    def batch_records():
        page = max(int(request.args.get("page", 1)), 1)
        page_size = max(int(request.args.get("page_size", 10)), 1)
        return _ok(_repository().latest_prediction_batches(page=page, page_size=page_size))

    @app.get("/api/realtime/summary")
    def realtime_summary():
        return _ok(_realtime_service().summary())

    @app.get("/api/realtime/trend")
    def realtime_trend():
        granularity = request.args.get("granularity", "day")
        return _ok(_realtime_service().trend(granularity))

    @app.get("/api/realtime/recent-predictions")
    def realtime_recent_predictions():
        return _ok(_realtime_service().recent_predictions())

    @app.get("/api/realtime/country-risk")
    @app.get("/api/dashboard/country-risk")
    def realtime_country_risk():
        return _ok(_realtime_service().country_risk())

    @app.get("/api/realtime/channel-risk")
    @app.get("/api/dashboard/channel-risk")
    def realtime_channel_risk():
        return _ok(_realtime_service().channel_risk())

    @app.get("/api/system/service-status")
    def system_service_status():
        return _ok(_realtime_service().service_status())

    @app.get("/api/charts/dashboard-trend")
    def chart_dashboard_trend():
        granularity = request.args.get("granularity", "day")
        return _ok(_chart_options_service().dashboard_trend(granularity))

    @app.get("/api/charts/dashboard-country-risk")
    def chart_dashboard_country_risk():
        return _ok(_chart_options_service().dashboard_country_risk())

    @app.get("/api/charts/dashboard-channel-risk")
    def chart_dashboard_channel_risk():
        return _ok(_chart_options_service().dashboard_channel_risk())

    @app.get("/api/charts/realtime-trend")
    def chart_realtime_trend():
        granularity = request.args.get("granularity", "day")
        return _ok(_chart_options_service().realtime_trend(granularity))

    @app.get("/api/charts/model-metrics")
    def chart_model_metrics():
        return _ok(_chart_options_service().model_metrics())

    @app.get("/api/charts/confusion-matrix")
    def chart_confusion_matrix():
        return _ok(_chart_options_service().confusion_matrix())

    @app.get("/api/charts/visualization-trend")
    def chart_visualization_trend():
        return _ok(_chart_options_service().visualization_trend(_visualization_overview_data()))

    @app.get("/api/charts/visualization-cancel-structure")
    def chart_visualization_cancel_structure():
        return _ok(_chart_options_service().visualization_cancel_structure(_visualization_overview_data()))

    @app.get("/api/charts/visualization-factor-bars")
    def chart_visualization_factor_bars():
        return _ok(_chart_options_service().visualization_factor_bars(_visualization_overview_data()))

    @app.get("/api/charts/visualization-channel-ranking")
    def chart_visualization_channel_ranking():
        return _ok(_chart_options_service().visualization_channel_ranking(_visualization_overview_data()))

    @app.get("/api/charts/visualization-risk-tags")
    def chart_visualization_risk_tags():
        return _ok(_chart_options_service().visualization_risk_tags(_visualization_overview_data()))

    @app.get("/api/charts/visualization-country-risk")
    def chart_visualization_country_risk():
        return _ok(_chart_options_service().visualization_country_risk(_visualization_overview_data()))


def _repository():
    if current_app.config.get("BOOKING_DATA_SOURCE") == "mysql":
        mysql_client = MySQLClient(MySQLConfig.from_flask_config(current_app.config))
        return MySQLBookingRepository(mysql_client)
    csv_path = current_app.config.get("BOOKING_DATA_CSV")
    if not csv_path:
        csv_path = Path(current_app.root_path).parent / "\u6570\u636e" / "cleaned_hotel_bookings.csv"
    return BookingRepository(csv_path)


def _realtime_service():
    redis_client = None
    if current_app.config.get("REDIS_ENABLED"):
        redis_client = RedisClient.from_flask_config(current_app.config)
    return RealtimeService(
        _repository(),
        redis_client,
        metrics_path=current_app.config.get("PREDICTION_METRICS_PATH"),
    )


def _prediction_service():
    return PredictionService(
        model_dir=current_app.config.get("PREDICTION_MODEL_DIR"),
        model_path=current_app.config.get("PREDICTION_MODEL_PATH"),
        feature_columns_path=current_app.config.get("PREDICTION_FEATURE_COLUMNS_PATH"),
        metrics_path=current_app.config.get("PREDICTION_METRICS_PATH"),
    )


def _chart_options_service():
    return ChartOptionsService(_realtime_service(), _prediction_service())


def _booking_filters():
    return {
        "hotel": request.args.get("hotel"),
        "country_code": request.args.get("country_code"),
        "market_segment": request.args.get("market_segment"),
        "customer_type": request.args.get("customer_type"),
        "is_canceled": request.args.get("is_canceled"),
        "keyword": request.args.get("keyword"),
    }


def _visualization_filters():
    return {
        "country_code": request.args.get("country_code") or None,
        "month": request.args.get("month") or None,
        "market_segment": request.args.get("market_segment") or None,
        "customer_type": request.args.get("customer_type") or None,
        "risk_tag": request.args.get("risk_tag") or None,
    }


def _visualization_overview_data():
    filters = _visualization_filters()
    frame = _repository().active_bookings()
    frame = _apply_visualization_filters(frame, filters)
    total = len(frame)
    canceled = int(frame["is_canceled"].sum()) if total else 0
    return {
        "filters": filters,
        "summary": {
            "booking_count": total,
            "cancel_count": canceled,
            "cancel_rate": round(canceled / total, 4) if total else 0,
            "avg_adr": round(float(frame["adr"].mean()), 2) if total else 0,
        },
        "trend": _trend_points(frame, "month"),
        "cancel_structure": _cancel_structure(frame),
        "factor_bars": _factor_bars(frame),
        "channel_ranking": _channel_ranking(frame),
        "country_map": _country_map(frame),
        "risk_tags": _risk_tags(frame),
        "sample_orders": _sample_orders(frame),
    }


def _apply_visualization_filters(frame, filters):
    if filters["country_code"]:
        frame = frame[frame["country_code"].astype(str) == filters["country_code"]]
    if filters["month"]:
        frame = frame[frame["arrival_date"].dt.strftime("%Y-%m") == filters["month"]]
    if filters["market_segment"]:
        frame = frame[frame["market_segment"].astype(str) == filters["market_segment"]]
    if filters["customer_type"]:
        frame = frame[frame["customer_type"].astype(str) == filters["customer_type"]]
    if filters["risk_tag"] == "lead_time_high":
        frame = frame[frame["lead_time"] >= 90]
    if filters["risk_tag"] == "no_special_requests":
        frame = frame[frame["total_of_special_requests"] == 0]
    if filters["risk_tag"] == "previous_cancellations":
        frame = frame[frame["previous_cancellations"] > 0]
    return frame


def _trend_points(frame, granularity):
    if frame.empty:
        return []
    period_format = "%Y-%m-%d" if granularity == "day" else "%Y-%m"
    grouped = frame.assign(period=frame["arrival_date"].dt.strftime(period_format)).groupby("period")
    points = []
    for period, group in grouped:
        booking_count = len(group)
        cancel_count = int(group["is_canceled"].sum())
        points.append(
            {
                "period": period,
                "booking_count": booking_count,
                "cancel_count": cancel_count,
                "cancel_rate": round(cancel_count / booking_count, 4) if booking_count else 0,
            }
        )
    return points


def _cancel_structure(frame):
    if frame.empty:
        return []
    grouped = frame.groupby("is_canceled_label").size()
    return [{"name": name, "value": int(value)} for name, value in grouped.items()]


def _factor_bars(frame):
    if frame.empty:
        return []
    return [
        {"name": "lead_time_high", "risk_tag": "lead_time_high", "cancel_rate": _cancel_rate(frame[frame["lead_time"] >= 90])},
        {"name": "no_special_requests", "risk_tag": "no_special_requests", "cancel_rate": _cancel_rate(frame[frame["total_of_special_requests"] == 0])},
        {"name": "previous_cancellations", "risk_tag": "previous_cancellations", "cancel_rate": _cancel_rate(frame[frame["previous_cancellations"] > 0])},
    ]


def _channel_ranking(frame):
    if frame.empty:
        return []
    grouped = frame.groupby(["market_segment", "market_segment_name"])
    rows = []
    for (market_segment, name), group in grouped:
        rows.append(
            {
                "name": name,
                "market_segment": market_segment,
                "booking_count": len(group),
                "cancel_rate": _cancel_rate(group),
            }
        )
    return sorted(rows, key=lambda item: item["booking_count"], reverse=True)


def _country_map(frame):
    if frame.empty:
        return []
    rows = []
    for (code, name), group in frame.groupby(["country_code", "country_name"]):
        rows.append({"code": code, "name": name, "value": _cancel_rate(group), "booking_count": len(group)})
    return rows


def _risk_tags(frame):
    if frame.empty:
        return []
    return [
        {"name": "lead_time_high", "value": int((frame["lead_time"] >= 90).sum())},
        {"name": "no_special_requests", "value": int((frame["total_of_special_requests"] == 0).sum())},
        {"name": "previous_cancellations", "value": int((frame["previous_cancellations"] > 0).sum())},
    ]


def _sample_orders(frame):
    if frame.empty:
        return []
    return [
        {field: _json_value(row[field]) for field in SAMPLE_ORDER_FIELDS}
        for _, row in frame.head(10).iterrows()
    ]


def _cancel_rate(frame):
    return round(float(frame["is_canceled"].sum()) / len(frame), 4) if len(frame) else 0


def _json_value(value):
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        return round(value, 4)
    return value


def _ok(data, message="ok"):
    return jsonify({"success": True, "data": data, "message": message})


def _fail(message, status_code):
    return jsonify({"success": False, "data": None, "message": message}), status_code
