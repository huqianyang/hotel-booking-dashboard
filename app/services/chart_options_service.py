from pyecharts import options as opts
from pyecharts.charts import Bar, HeatMap, Line, Pie, WordCloud

from app.services.realtime_service import WAITING_MESSAGE


class ChartOptionsService:
    def __init__(self, realtime_service, prediction_service):
        self.realtime_service = realtime_service
        self.prediction_service = prediction_service

    def dashboard_trend(self, granularity="day"):
        return self._trend(granularity)

    def realtime_trend(self, granularity="day"):
        return self._trend(granularity)

    def dashboard_country_risk(self):
        risk = self.realtime_service.country_risk(include_source=True)
        items = risk.get("items", [])
        chart = (
            Bar()
            .add_xaxis([item.get("name", "") for item in items])
            .add_yaxis("cancel_rate", [_risk_value(item) for item in items])
            .set_global_opts(
                xaxis_opts=opts.AxisOpts(type_="category"),
                yaxis_opts=opts.AxisOpts(name="cancel_rate"),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
            )
        )
        return _payload("bar", chart, risk)

    def dashboard_channel_risk(self):
        risk = self.realtime_service.channel_risk(include_source=True)
        items = risk.get("items", [])
        chart = Pie()
        if items:
            chart.add("cancel_rate", [(item.get("name", ""), _risk_value(item)) for item in items])
        chart.set_global_opts(tooltip_opts=opts.TooltipOpts(trigger="item"))
        return _payload("pie", chart, risk)

    def model_metrics(self):
        metrics = self.prediction_service.model_metrics().get("metrics", {})
        labels = ["accuracy", "precision_score", "recall_score", "f1_score"]
        values = [round(float(metrics.get(label, 0)), 4) for label in labels]
        chart = (
            Bar()
            .add_xaxis(labels)
            .add_yaxis("score", values)
            .set_global_opts(
                yaxis_opts=opts.AxisOpts(min_=0, max_=1),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
            )
        )
        return {
            "chart_type": "bar",
            "options": chart.dump_options(),
            "status": "running",
            "message": "ok",
            "source": "metrics",
        }

    def confusion_matrix(self):
        matrix = self.prediction_service.model_metrics().get("confusion_matrix", {})
        values = [
            [0, 0, int(matrix.get("true_negative", 0))],
            [1, 0, int(matrix.get("false_positive", 0))],
            [0, 1, int(matrix.get("false_negative", 0))],
            [1, 1, int(matrix.get("true_positive", 0))],
        ]
        chart = (
            HeatMap()
            .add_xaxis(["predicted_keep", "predicted_cancel"])
            .add_yaxis("count", ["actual_keep", "actual_cancel"], values)
            .set_global_opts(
                visualmap_opts=opts.VisualMapOpts(min_=0, max_=max((item[2] for item in values), default=0)),
                tooltip_opts=opts.TooltipOpts(trigger="item"),
            )
        )
        return {
            "chart_type": "heatmap",
            "options": chart.dump_options(),
            "status": "running",
            "message": "ok",
            "source": "metrics",
        }

    def visualization_trend(self, overview):
        rows = overview.get("trend", [])
        chart = (
            Line()
            .add_xaxis([row.get("period", "") for row in rows])
            .add_yaxis("booking_count", [int(row.get("booking_count", 0)) for row in rows], is_smooth=True)
            .add_yaxis("cancel_count", [int(row.get("cancel_count", 0)) for row in rows], is_smooth=True)
            .add_yaxis("cancel_rate", [_risk_value(row) for row in rows], is_smooth=True)
            .set_global_opts(
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                xaxis_opts=opts.AxisOpts(type_="category"),
                yaxis_opts=opts.AxisOpts(type_="value"),
            )
        )
        return _mysql_payload("line", chart)

    def visualization_cancel_structure(self, overview):
        items = overview.get("cancel_structure", [])
        chart = Pie()
        if items:
            chart.add("bookings", [(item.get("name", ""), int(item.get("value", 0))) for item in items])
        chart.set_global_opts(tooltip_opts=opts.TooltipOpts(trigger="item"))
        return _mysql_payload("pie", chart)

    def visualization_factor_bars(self, overview):
        rows = overview.get("factor_bars", [])
        chart = (
            Bar()
            .add_xaxis([row.get("name", "") for row in rows])
            .add_yaxis("cancel_rate", [_risk_value(row) for row in rows])
            .set_global_opts(
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                xaxis_opts=opts.AxisOpts(type_="category"),
                yaxis_opts=opts.AxisOpts(min_=0, max_=1),
            )
        )
        return _mysql_payload("bar", chart)

    def visualization_channel_ranking(self, overview):
        rows = overview.get("channel_ranking", [])
        chart = (
            Bar()
            .add_xaxis([row.get("name", "") for row in rows])
            .add_yaxis("cancel_rate", [_risk_value(row) for row in rows])
            .set_global_opts(
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                xaxis_opts=opts.AxisOpts(type_="category"),
                yaxis_opts=opts.AxisOpts(min_=0, max_=1),
            )
        )
        return _mysql_payload("bar", chart)

    def visualization_risk_tags(self, overview):
        rows = overview.get("risk_tags", [])
        chart = WordCloud()
        if rows:
            chart.add("risk_tags", [(row.get("name", ""), int(row.get("value", 0))) for row in rows])
        chart.set_global_opts(tooltip_opts=opts.TooltipOpts(trigger="item"))
        return _mysql_payload("wordcloud", chart)

    def visualization_country_risk(self, overview):
        rows = sorted(overview.get("country_map", []), key=lambda row: row.get("value", 0), reverse=True)
        chart = (
            Bar()
            .add_xaxis([row.get("name", "") for row in rows])
            .add_yaxis("cancel_rate", [_risk_value(row) for row in rows])
            .set_global_opts(
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                xaxis_opts=opts.AxisOpts(type_="category"),
                yaxis_opts=opts.AxisOpts(min_=0, max_=1),
            )
        )
        return _mysql_payload("bar", chart)

    def _trend(self, granularity):
        trend = self.realtime_service.trend(granularity, include_source=True)
        chart = (
            Line()
            .add_xaxis(trend.get("labels", []))
            .add_yaxis("inflow", trend.get("inflow", []), is_smooth=True)
            .add_yaxis("predicted_cancellations", trend.get("predicted_cancellations", []), is_smooth=True)
            .add_yaxis("cancel_rate", trend.get("cancel_rate", []), is_smooth=True)
            .set_global_opts(
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                xaxis_opts=opts.AxisOpts(type_="category"),
                yaxis_opts=opts.AxisOpts(type_="value"),
            )
        )
        return _payload("line", chart, trend)


def _payload(chart_type, chart, source_payload):
    status = source_payload.get("status", "waiting")
    return {
        "chart_type": chart_type,
        "options": chart.dump_options(),
        "status": status,
        "message": source_payload.get("message") or ("ok" if status == "running" else WAITING_MESSAGE),
        "source": source_payload.get("source", "none"),
    }


def _mysql_payload(chart_type, chart):
    return {
        "chart_type": chart_type,
        "options": chart.dump_options(),
        "status": "running",
        "message": "ok",
        "source": "mysql",
    }


def _risk_value(item):
    value = item.get("cancel_rate", item.get("value", 0))
    return round(float(value), 4) if value not in (None, "") else 0
