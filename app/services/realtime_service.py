import json
from pathlib import Path


DEFAULT_OFFLINE_BASE_ROWS = 80008
WAITING_MESSAGE = "等待实时链路数据"


class RealtimeService:
    def __init__(self, repository, redis_client=None, metrics_path=None):
        self.repository = repository
        self.redis_client = redis_client
        self.metrics_path = Path(metrics_path) if metrics_path else Path(__file__).resolve().parents[2] / "models" / "metrics.json"

    def dashboard_summary(self):
        source, summary = self._summary_source()
        offline_base_rows = self._offline_base_rows()
        processed_count = _int_value(summary, "realtime_processed_count", "processed_count")
        high_risk_count = _int_value(summary, "high_risk_count", "latest_high_risk_count")
        average_probability = _float_value(summary, "average_cancel_probability", "avg_cancel_probability")
        updated_at = summary.get("updated_at") or summary.get("latest_business_time")
        status = summary.get("status")
        if status not in {"running", "waiting"}:
            status = "running" if source == "redis" else "mysql_fallback" if source == "mysql" else "waiting"
        data = {
            "offline_base_rows": offline_base_rows,
            "realtime_processed_count": processed_count,
            "total_bookings": offline_base_rows + processed_count,
            "high_risk_count": high_risk_count,
            "average_cancel_probability": average_probability,
            "updated_at": updated_at,
            "status": status,
        }
        if status == "waiting":
            data["message"] = WAITING_MESSAGE
        return data

    def summary(self):
        source, summary = self._summary_source()
        if summary:
            normalized = dict(summary)
            normalized.setdefault("processed_count", _int_value(summary, "realtime_processed_count", "processed_count"))
            normalized.setdefault("high_risk_count", _int_value(summary, "high_risk_count", "latest_high_risk_count"))
            normalized.setdefault("average_cancel_probability", _float_value(summary, "average_cancel_probability", "avg_cancel_probability"))
            normalized.setdefault("status", "running" if source == "redis" else "mysql_fallback")
            return normalized
        return {
            "processed_count": 0,
            "high_risk_count": 0,
            "average_cancel_probability": 0.0,
            "updated_at": None,
            "status": "waiting",
            "message": WAITING_MESSAGE,
        }

    def trend(self, granularity="day"):
        granularity = granularity if granularity in {"day", "week", "month"} else "day"
        cached = self._get_cached("realtime:trend")
        rows = _select_granularity(cached, granularity)
        if rows is None and hasattr(self.repository, "latest_realtime_trend"):
            rows = self.repository.latest_realtime_trend(granularity)
        if not rows:
            return _empty_trend(granularity)
        return _trend_series(rows, granularity)

    def recent_predictions(self, limit=10):
        cached = self._get_cached("realtime:recent_predictions")
        items = _items(cached)
        if items is None and hasattr(self.repository, "latest_storm_predictions"):
            items = self.repository.latest_storm_predictions(limit=limit)
        if not items:
            return {"items": [], "status": "waiting", "message": WAITING_MESSAGE}
        return {"items": items[:limit], "status": "running"}

    def country_risk(self):
        return self._risk("realtime:country_risk", "country_risk")

    def channel_risk(self):
        return self._risk("realtime:channel_risk", "channel_risk")

    def service_status(self):
        link_status = self._get_cached("realtime:link_status") or {}
        services = {
            "flask": "running",
            "mysql": self._mysql_status(),
            "redis": self._redis_status(),
            "flume": link_status.get("flume", "unknown"),
            "kafka": link_status.get("kafka", "unknown"),
            "storm": link_status.get("storm", "unknown"),
        }
        status = "running" if all(value == "running" for value in services.values()) else "degraded"
        return {"services": services, "status": status}

    def _summary_source(self):
        cached = self._get_cached("realtime:summary")
        if cached:
            return "redis", cached
        if hasattr(self.repository, "latest_realtime_summary"):
            summary = self.repository.latest_realtime_summary()
            if summary:
                return "mysql", summary
        return "none", {}

    def _risk(self, redis_key, metric_type):
        cached = self._get_cached(redis_key)
        items = _items(cached)
        if items is None and hasattr(self.repository, "latest_realtime_risk"):
            items = self.repository.latest_realtime_risk(metric_type)
        if not items:
            return {"items": [], "status": "waiting", "message": WAITING_MESSAGE}
        return {"items": items, "status": "running"}

    def _offline_base_rows(self):
        try:
            data_split = json.loads(self.metrics_path.read_text(encoding="utf-8")).get("data_split", {})
        except (OSError, json.JSONDecodeError):
            return DEFAULT_OFFLINE_BASE_ROWS
        return int(data_split.get("offline_source_rows") or DEFAULT_OFFLINE_BASE_ROWS)

    def _mysql_status(self):
        if hasattr(self.repository, "ping"):
            try:
                return "running" if self.repository.ping() else "down"
            except Exception:
                return "down"
        return "unknown"

    def _redis_status(self):
        if not self.redis_client:
            return "disabled"
        try:
            return "running" if self.redis_client.ping() else "down"
        except Exception:
            return "down"

    def _get_cached(self, key):
        if not self.redis_client:
            return None
        try:
            if hasattr(self.redis_client, "get_json"):
                return self.redis_client.get_json(key)
            value = self.redis_client.get(key)
            if not value:
                return None
            return json.loads(value)
        except Exception:
            return None


def _select_granularity(cached, granularity):
    if cached is None:
        return None
    if isinstance(cached, dict):
        if granularity in cached:
            return cached[granularity]
        if "points" in cached:
            return cached["points"]
        if "labels" in cached:
            return cached
    return cached


def _trend_series(rows, granularity):
    if isinstance(rows, dict) and "labels" in rows:
        return {"granularity": granularity, **rows}
    labels = []
    inflow = []
    predicted_cancellations = []
    cancel_rate = []
    points = []
    for row in rows:
        label = row.get("label") or row.get("period") or row.get("business_time") or row.get("window_start")
        row_inflow = _int_value(row, "inflow", "processed_count", "booking_count")
        row_cancellations = _int_value(row, "predicted_cancellations", "cancel_count", "high_risk_count")
        row_cancel_rate = _float_value(row, "cancel_rate", "latest_cancel_rate")
        labels.append(label)
        inflow.append(row_inflow)
        predicted_cancellations.append(row_cancellations)
        cancel_rate.append(row_cancel_rate)
        points.append(
            {
                "label": label,
                "period": label,
                "inflow": row_inflow,
                "predicted_cancellations": row_cancellations,
                "cancel_rate": row_cancel_rate,
            }
        )
    return {
        "granularity": granularity,
        "labels": labels,
        "inflow": inflow,
        "predicted_cancellations": predicted_cancellations,
        "cancel_rate": cancel_rate,
        "points": points,
        "status": "running",
    }


def _empty_trend(granularity):
    return {
        "granularity": granularity,
        "labels": [],
        "inflow": [],
        "predicted_cancellations": [],
        "cancel_rate": [],
        "points": [],
        "status": "waiting",
        "message": WAITING_MESSAGE,
    }


def _items(value):
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if "items" in value:
            return value["items"]
        if "points" in value:
            return value["points"]
    return None


def _int_value(mapping, *keys):
    value = _first_value(mapping, *keys)
    return int(float(value)) if value not in (None, "") else 0


def _float_value(mapping, *keys):
    value = _first_value(mapping, *keys)
    return round(float(value), 4) if value not in (None, "") else 0.0


def _first_value(mapping, *keys):
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return None
