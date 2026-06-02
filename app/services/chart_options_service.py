from pyecharts import options as opts
from pyecharts.charts import Bar, HeatMap, Line, Map, Pie, WordCloud

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
            .add_yaxis("取消率", [_risk_value(item) for item in items])
            .set_global_opts(
                xaxis_opts=opts.AxisOpts(type_="category"),
                yaxis_opts=opts.AxisOpts(name="取消率"),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                legend_opts=opts.LegendOpts(pos_top="2%"),
            )
        )
        return _payload("bar", chart, risk)

    def dashboard_channel_risk(self):
        risk = self.realtime_service.channel_risk(include_source=True)
        items = risk.get("items", [])
        chart = Pie()
        if items:
            chart.add("取消率", [(item.get("name", ""), _risk_value(item)) for item in items])
        chart.set_global_opts(tooltip_opts=opts.TooltipOpts(trigger="item"), legend_opts=opts.LegendOpts(pos_top="2%"))
        return _payload("pie", chart, risk)

    def model_metrics(self):
        metrics = self.prediction_service.model_metrics().get("metrics", {})
        metric_pairs = [
            ("准确率", "accuracy"),
            ("精确率", "precision_score"),
            ("召回率", "recall_score"),
            ("F1 值", "f1_score"),
        ]
        values = [round(float(metrics.get(key, 0)), 4) for _, key in metric_pairs]
        chart = (
            Bar()
            .add_xaxis([label for label, _ in metric_pairs])
            .add_yaxis("模型分数", values)
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
            .add_xaxis(["预测未取消", "预测取消"])
            .add_yaxis("订单数", ["实际未取消", "实际取消"], values)
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
            .add_yaxis("订单数", [int(row.get("booking_count", 0)) for row in rows], is_smooth=True)
            .add_yaxis("已取消订单", [int(row.get("cancel_count", 0)) for row in rows], is_smooth=True)
            .add_yaxis("取消率", [_risk_value(row) for row in rows], is_smooth=True)
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
            chart.add("订单数", [(item.get("name", ""), int(item.get("value", 0))) for item in items])
        chart.set_global_opts(tooltip_opts=opts.TooltipOpts(trigger="item"))
        return _mysql_payload("pie", chart)

    def visualization_factor_bars(self, overview):
        rows = overview.get("factor_bars", [])
        chart = (
            Bar()
            .add_xaxis([row.get("name", "") for row in rows])
            .add_yaxis("取消率", [_risk_value(row) for row in rows])
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
            .add_yaxis("取消率", [_risk_value(row) for row in rows])
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
            chart.add("风险标签", [(row.get("name", ""), int(row.get("value", 0))) for row in rows])
        chart.set_global_opts(tooltip_opts=opts.TooltipOpts(trigger="item"))
        return _mysql_payload("wordcloud", chart)

    def visualization_country_risk(self, overview):
        rows = overview.get("country_map", [])
        chart = (
            Map()
            .add(
                "取消率",
                [(_world_map_name(row), _risk_value(row)) for row in rows if _world_map_name(row)],
                "world",
                is_map_symbol_show=False,
            )
            .set_global_opts(
                tooltip_opts=opts.TooltipOpts(trigger="item"),
                visualmap_opts=opts.VisualMapOpts(min_=0, max_=1, is_piecewise=False),
                legend_opts=opts.LegendOpts(pos_top="2%"),
            )
        )
        return _mysql_payload("map", chart)

    def _trend(self, granularity):
        trend = self.realtime_service.trend(granularity, include_source=True)
        chart = (
            Line()
            .add_xaxis(trend.get("labels", []))
            .add_yaxis("预订流入", trend.get("inflow", []), is_smooth=True)
            .add_yaxis("预测取消", trend.get("predicted_cancellations", []), is_smooth=True)
            .add_yaxis("取消率", trend.get("cancel_rate", []), is_smooth=True)
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


_WORLD_NAME_BY_CODE = {
    "AGO": "Angola",
    "ARG": "Argentina",
    "AUS": "Australia",
    "AUT": "Austria",
    "BEL": "Belgium",
    "BRA": "Brazil",
    "CAN": "Canada",
    "CHE": "Switzerland",
    "CHN": "China",
    "CN": "China",
    "DEU": "Germany",
    "ESP": "Spain",
    "FRA": "France",
    "GBR": "United Kingdom",
    "IRL": "Ireland",
    "ITA": "Italy",
    "JPN": "Japan",
    "KOR": "South Korea",
    "NLD": "Netherlands",
    "POL": "Poland",
    "PRT": "Portugal",
    "RUS": "Russia",
    "SWE": "Sweden",
    "USA": "United States",
    "ZAF": "South Africa",
}


def _world_map_name(row):
    code = str(row.get("code", ""))
    return _WORLD_NAME_BY_CODE.get(code, row.get("name", ""))
