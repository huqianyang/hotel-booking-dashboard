from datetime import datetime
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
        frame = _repository().active_bookings()
        total = len(frame)
        canceled = int(frame["is_canceled"].sum()) if total else 0
        latest = frame["event_date"].max() if total else None
        data = {
            "total_bookings": total,
            "canceled_bookings": canceled,
            "cancel_rate": round(canceled / total, 4) if total else 0,
            "avg_adr": round(float(frame["adr"].mean()), 2) if total else 0,
            "high_risk_count": int((frame["lead_time"] >= 90).sum()) if total else 0,
            "latest_event_time": latest.strftime("%Y-%m-%d 00:00:00") if latest is not None else None,
        }
        return _ok(data)

    @app.get("/api/dashboard/trend")
    def dashboard_trend():
        granularity = request.args.get("granularity", "month")
        frame = _repository().active_bookings()
        return _ok({"points": _trend_points(frame, granularity)})

    @app.get("/api/visualization/overview")
    def visualization_overview():
        filters = {
            "country_code": request.args.get("country_code") or None,
            "month": request.args.get("month") or None,
            "market_segment": request.args.get("market_segment") or None,
            "customer_type": request.args.get("customer_type") or None,
            "risk_tag": request.args.get("risk_tag") or None,
        }
        frame = _repository().active_bookings()
        frame = _apply_visualization_filters(frame, filters)
        total = len(frame)
        canceled = int(frame["is_canceled"].sum()) if total else 0
        data = {
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
        return _ok(data)

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
        probability = _stub_probability(booking)
        risk_level, risk_level_name = _risk_level(probability)
        data = {
            "booking_id": int(booking_id),
            "model_version": "stub_v1",
            "cancel_probability": probability,
            "predicted_label": 1 if probability >= 0.5 else 0,
            "predicted_label_name": "may_cancel" if probability >= 0.5 else "likely_keep",
            "risk_level": risk_level,
            "risk_level_name": risk_level_name,
            "reason_tags": _reason_tags(booking),
            "predicted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return _ok(data, "prediction completed")

    @app.get("/api/prediction/model-metrics")
    def model_metrics():
        return _ok(_stub_model_metrics())

    @app.get("/api/prediction/batch-records")
    def batch_records():
        page = max(int(request.args.get("page", 1)), 1)
        page_size = max(int(request.args.get("page_size", 10)), 1)
        items = [
            {
                "batch_id": "stub-2017-02",
                "business_date": "2017-02-01",
                "time_window": "00:00-23:59",
                "total_count": len(_repository().active_bookings()),
                "predicted_cancel_count": 0,
                "high_risk_count": 0,
                "avg_cancel_probability": 0.0,
                "source": "stub",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        ]
        return _ok(
            {
                "items": items[(page - 1) * page_size : page * page_size],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": len(items),
                    "total_pages": 1,
                },
            }
        )

    @app.get("/api/realtime/summary")
    def realtime_summary():
        return _ok(_realtime_service().summary())

    @app.get("/api/realtime/trend")
    def realtime_trend():
        return _ok(_realtime_service().trend())

    @app.get("/api/realtime/recent-predictions")
    def realtime_recent_predictions():
        return _ok(_realtime_service().recent_predictions())


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
    return RealtimeService(_repository(), redis_client)


def _booking_filters():
    return {
        "hotel": request.args.get("hotel"),
        "country_code": request.args.get("country_code"),
        "market_segment": request.args.get("market_segment"),
        "customer_type": request.args.get("customer_type"),
        "is_canceled": request.args.get("is_canceled"),
        "keyword": request.args.get("keyword"),
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
        {"name": "lead_time_high", "cancel_rate": _cancel_rate(frame[frame["lead_time"] >= 90])},
        {"name": "no_special_requests", "cancel_rate": _cancel_rate(frame[frame["total_of_special_requests"] == 0])},
        {"name": "previous_cancellations", "cancel_rate": _cancel_rate(frame[frame["previous_cancellations"] > 0])},
    ]


def _channel_ranking(frame):
    if frame.empty:
        return []
    grouped = frame.groupby("market_segment_name")
    rows = []
    for name, group in grouped:
        rows.append({"name": name, "booking_count": len(group), "cancel_rate": _cancel_rate(group)})
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


def _stub_probability(booking):
    score = 0.15
    if booking.get("lead_time", 0) >= 90:
        score += 0.3
    if booking.get("previous_cancellations", 0) > 0:
        score += 0.25
    if booking.get("total_of_special_requests", 0) == 0:
        score += 0.15
    if booking.get("deposit_type") == "Non Refund":
        score += 0.15
    return round(min(score, 0.95), 4)


def _risk_level(probability):
    if probability >= 0.6:
        return "high", "high_risk"
    if probability >= 0.3:
        return "medium", "medium_risk"
    return "low", "low_risk"


def _reason_tags(booking):
    tags = []
    if booking.get("lead_time", 0) >= 90:
        tags.append("lead_time_high")
    if booking.get("previous_cancellations", 0) > 0:
        tags.append("previous_cancellations")
    if booking.get("total_of_special_requests", 0) == 0:
        tags.append("no_special_requests")
    return tags or ["baseline_stub"]


def _stub_model_metrics():
    return {
        "selected_model": {
            "model_name": "stub_model",
            "model_version": "stub_v1",
            "is_selected": 1,
            "reason": "temporary API stub before trained model is delivered",
        },
        "metrics": {
            "accuracy": 0.0,
            "precision_score": 0.0,
            "recall_score": 0.0,
            "f1_score": 0.0,
            "train_score": 0.0,
            "test_score": 0.0,
        },
        "model_comparison": [],
        "confusion_matrix": {
            "true_negative": 0,
            "false_positive": 0,
            "false_negative": 0,
            "true_positive": 0,
        },
    }


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
