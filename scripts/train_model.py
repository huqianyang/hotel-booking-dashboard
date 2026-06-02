from __future__ import annotations

import argparse
import json
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.data.split_policy import OFFLINE_CUTOFF_DATE, REALTIME_START_DATE, count_split_rows, filter_offline_model_data

DEFAULT_INPUT_CSV = PROJECT_ROOT / "数据" / "cleaned_hotel_bookings.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "models"
TARGET_COLUMN = "is_canceled"
MODEL_FEATURE_COLUMNS = [
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
CATEGORICAL_COLUMNS = [
    "hotel",
    "meal",
    "country_code",
    "market_segment",
    "distribution_channel",
    "reserved_room_type",
    "assigned_room_type",
    "deposit_type",
    "customer_type",
]
NUMERIC_COLUMNS = [column for column in MODEL_FEATURE_COLUMNS if column not in CATEGORICAL_COLUMNS]


@dataclass(frozen=True)
class TrainingResult:
    model_path: Path
    feature_columns_path: Path
    metrics_path: Path
    selected_model: str


def build_preprocessor() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_COLUMNS),
            ("categorical", categorical_pipeline, CATEGORICAL_COLUMNS),
        ]
    )


def build_candidate_models() -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline(
            steps=[
                ("preprocessor", build_preprocessor()),
                ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("preprocessor", build_preprocessor()),
                ("classifier", RandomForestClassifier(n_estimators=120, min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=-1)),
            ]
        ),
    }


def score_model(model: Pipeline, x_train: pd.DataFrame, x_test: pd.DataFrame, y_train: pd.Series, y_test: pd.Series) -> dict[str, float | list[list[int]]]:
    predictions = model.predict(x_test)
    return {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision_score": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
        "recall_score": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, predictions, zero_division=0)), 4),
        "train_score": round(float(model.score(x_train, y_train)), 4),
        "test_score": round(float(model.score(x_test, y_test)), 4),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=[0, 1]).astype(int).tolist(),
    }


def choose_best_model(results: dict[str, dict[str, float | list[list[int]]]]) -> str:
    return max(results, key=lambda name: (float(results[name]["f1_score"]), float(results[name]["accuracy"])))


def load_offline_training_data(input_csv: str | Path) -> pd.DataFrame:
    data = pd.read_csv(input_csv)
    return filter_offline_model_data(data)


def train_and_save(input_csv: str | Path = DEFAULT_INPUT_CSV, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> TrainingResult:
    input_csv = Path(input_csv)
    output_dir = Path(output_dir)
    raw_data = pd.read_csv(input_csv)
    data = filter_offline_model_data(raw_data)
    split_counts = count_split_rows(raw_data)
    missing_columns = [column for column in [*MODEL_FEATURE_COLUMNS, TARGET_COLUMN] if column not in data.columns]
    if missing_columns:
        raise ValueError(f"cleaned data missing columns: {missing_columns}")

    x = data[MODEL_FEATURE_COLUMNS].copy()
    y = data[TARGET_COLUMN].astype(int)
    stratify = y if y.nunique() > 1 and y.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=stratify)

    models = build_candidate_models()
    comparison = {}
    for name, model in models.items():
        model.fit(x_train, y_train)
        comparison[name] = score_model(model, x_train, x_test, y_train, y_test)

    selected_model = choose_best_model(comparison)
    selected_metrics = comparison[selected_model]
    metrics = {
        "selected_model": selected_model,
        "model_version": f"{selected_model}_v1",
        "metrics": {key: selected_metrics[key] for key in ["accuracy", "precision_score", "recall_score", "f1_score", "train_score", "test_score"]},
        "comparison": comparison,
        "confusion_matrix": selected_metrics["confusion_matrix"],
        "feature_count": len(MODEL_FEATURE_COLUMNS),
        "data_split": {
            "offline_cutoff_date": OFFLINE_CUTOFF_DATE,
            "realtime_start_date": REALTIME_START_DATE,
            "offline_source_rows": split_counts.offline_rows,
            "train_rows": len(x_train),
            "test_rows": len(x_test),
            "realtime_simulation_rows": split_counts.realtime_rows,
            "test_size": 0.2,
            "random_state": 42,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "cancellation_model.pkl"
    feature_columns_path = output_dir / "feature_columns.json"
    metrics_path = output_dir / "metrics.json"
    with model_path.open("wb") as model_file:
        pickle.dump(models[selected_model], model_file)
    feature_columns_path.write_text(json.dumps(MODEL_FEATURE_COLUMNS, ensure_ascii=False, indent=2), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return TrainingResult(model_path, feature_columns_path, metrics_path, selected_model)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train hotel booking cancellation models.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = train_and_save(args.input_csv, args.output_dir)
    print(f"selected_model={result.selected_model}")
    print(f"model_path={result.model_path}")
    print(f"feature_columns_path={result.feature_columns_path}")
    print(f"metrics_path={result.metrics_path}")


if __name__ == "__main__":
    main()
