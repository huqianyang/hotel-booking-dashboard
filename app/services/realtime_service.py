import json


class RealtimeService:
    def __init__(self, repository, redis_client=None):
        self.repository = repository
        self.redis_client = redis_client

    def summary(self):
        cached = self._get_cached("realtime:summary")
        if cached:
            return cached
        frame = self.repository.active_bookings()
        total = len(frame)
        latest = frame["event_date"].max() if total else None
        return {
            "processed_count": total,
            "latest_business_time": latest.strftime("%Y-%m-%d 00:00:00") if latest is not None else None,
            "latest_cancel_rate": _cancel_rate(frame),
            "latest_high_risk_count": int((frame["lead_time"] >= 90).sum()) if total else 0,
            "service_status": {
                "mysql": "running",
                "redis": "stub",
                "flume": "pending",
                "kafka": "pending",
                "storm": "pending",
            },
        }

    def trend(self):
        cached = self._get_cached("realtime:trend")
        if cached:
            return cached
        frame = self.repository.active_bookings()
        if frame.empty:
            return {"points": []}
        points = []
        grouped = frame.assign(business_time=frame["event_date"].dt.strftime("%Y-%m-%d 00:00:00")).groupby(
            "business_time"
        )
        for business_time, group in grouped:
            points.append(
                {
                    "business_time": business_time,
                    "processed_count": len(group),
                    "cancel_rate": _cancel_rate(group),
                    "high_risk_count": int((group["lead_time"] >= 90).sum()),
                }
            )
        return {"points": points}

    def recent_predictions(self):
        cached = self._get_cached("realtime:recent_predictions")
        if cached:
            return cached
        frame = self.repository.active_bookings()
        if frame.empty:
            return {"items": []}
        items = []
        for _, row in frame.sort_values("event_date").head(10).iterrows():
            booking = row.to_dict()
            probability = _stub_probability(booking)
            _, risk_level_name = _risk_level(probability)
            items.append(
                {
                    "booking_id": _json_value(booking["booking_id"]),
                    "hotel_name": _json_value(booking["hotel_name"]),
                    "country_name": _json_value(booking["country_name"]),
                    "cancel_probability": probability,
                    "risk_level_name": risk_level_name,
                    "business_time": row["event_date"].strftime("%Y-%m-%d 00:00:00"),
                }
            )
        return {"items": items}

    def _get_cached(self, key):
        if not self.redis_client:
            return None
        if hasattr(self.redis_client, "get_json"):
            return self.redis_client.get_json(key)
        value = self.redis_client.get(key)
        if not value:
            return None
        return json.loads(value)


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


def _cancel_rate(frame):
    return round(float(frame["is_canceled"].sum()) / len(frame), 4) if len(frame) else 0


def _json_value(value):
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        return round(value, 4)
    return value
