from __future__ import annotations

import json
import pickle
from datetime import datetime
from pathlib import Path

import pandas as pd


class PredictionService:
    def __init__(self, model_dir=None, model_path=None, feature_columns_path=None, metrics_path=None):
        root = Path(__file__).resolve().parents[2]
        model_dir = Path(model_dir) if model_dir else root / "models"
        self.model_path = Path(model_path) if model_path else model_dir / "cancellation_model.pkl"
        self.feature_columns_path = Path(feature_columns_path) if feature_columns_path else model_dir / "feature_columns.json"
        self.metrics_path = Path(metrics_path) if metrics_path else model_dir / "metrics.json"
        self._model = None
        self._feature_columns = None
        self._metrics = None

    def predict_booking(self, booking):
        probability = self._predict_probability(booking)
        risk_level, risk_level_name = risk_level_for_probability(probability)
        return {
            "booking_id": int(booking["booking_id"]),
            "model_version": self.model_version,
            "cancel_probability": probability,
            "predicted_label": 1 if probability >= 0.5 else 0,
            "predicted_label_name": "may_cancel" if probability >= 0.5 else "likely_keep",
            "risk_level": risk_level,
            "risk_level_name": risk_level_name,
            "reason_tags": reason_tags_for_booking(booking),
            "predicted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def model_metrics(self):
        metrics = self.metrics
        selected_model = metrics.get("selected_model", "unknown_model")
        return {
            "selected_model": {
                "model_name": selected_model,
                "model_version": self.model_version,
                "is_selected": 1,
                "reason": metrics.get("selection_reason", "selected by training pipeline"),
            },
            "metrics": metrics.get("metrics", {}),
            "model_comparison": self._model_comparison(metrics.get("comparison", [])),
            "confusion_matrix": self._confusion_matrix(metrics.get("confusion_matrix")),
        }

    @property
    def model_version(self):
        return self.metrics.get("model_version", "unknown_model_v1")

    @property
    def metrics(self):
        if self._metrics is None:
            self._metrics = json.loads(self.metrics_path.read_text(encoding="utf-8"))
        return self._metrics

    @property
    def feature_columns(self):
        if self._feature_columns is None:
            self._feature_columns = json.loads(self.feature_columns_path.read_text(encoding="utf-8"))
        return self._feature_columns

    @property
    def model(self):
        if self._model is None:
            with self.model_path.open("rb") as model_file:
                self._model = pickle.load(model_file)
        return self._model

    def _predict_probability(self, booking):
        frame = pd.DataFrame([{column: booking.get(column) for column in self.feature_columns}], columns=self.feature_columns)
        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(frame)
            return round(float(probabilities[0][1]), 4)
        prediction = self.model.predict(frame)
        return float(prediction[0])

    def _model_comparison(self, comparison):
        if isinstance(comparison, dict):
            rows = []
            for model_name, values in comparison.items():
                rows.append({"model_name": model_name, **_metric_subset(values)})
            return rows
        return [{"model_name": row.get("model_name", "unknown_model"), **_metric_subset(row)} for row in comparison]

    def _confusion_matrix(self, matrix):
        if isinstance(matrix, dict):
            return matrix
        if not matrix:
            matrix = [[0, 0], [0, 0]]
        return {
            "true_negative": int(matrix[0][0]),
            "false_positive": int(matrix[0][1]),
            "false_negative": int(matrix[1][0]),
            "true_positive": int(matrix[1][1]),
        }


def _metric_subset(values):
    return {
        "accuracy": values.get("accuracy", 0),
        "precision_score": values.get("precision_score", 0),
        "recall_score": values.get("recall_score", 0),
        "f1_score": values.get("f1_score", 0),
    }


def risk_level_for_probability(probability):
    if probability >= 0.6:
        return "high", "high_risk"
    if probability >= 0.3:
        return "medium", "medium_risk"
    return "low", "low_risk"


def reason_tags_for_booking(booking):
    tags = []
    if booking.get("lead_time", 0) >= 90:
        tags.append("lead_time_high")
    if booking.get("previous_cancellations", 0) > 0:
        tags.append("previous_cancellations")
    if booking.get("total_of_special_requests", 0) == 0:
        tags.append("no_special_requests")
    if booking.get("deposit_type") == "Non Refund":
        tags.append("non_refund_deposit")
    return tags or ["model_probability"]
