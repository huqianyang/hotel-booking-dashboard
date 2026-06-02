import json
import pickle
import subprocess
import sys
from pathlib import Path

import pandas as pd


EXPECTED_FEATURE_COLUMNS = [
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


def make_training_frame() -> pd.DataFrame:
    rows = []
    for index in range(80):
        high_risk = index % 4 in (0, 1)
        rows.append(
            {
                "booking_id": index + 1,
                "hotel": "City Hotel" if index % 2 else "Resort Hotel",
                "hotel_name": "城市酒店" if index % 2 else "度假酒店",
                "is_canceled": 1 if high_risk else 0,
                "is_canceled_label": "已取消" if high_risk else "未取消",
                "lead_time": 180 + index if high_risk else 10 + index,
                "arrival_date": "2017-01-01",
                "event_date": "2017-01-01",
                "stays_in_weekend_nights": index % 3,
                "stays_in_week_nights": 2 + index % 5,
                "total_nights": 2 + index % 6,
                "adults": 2,
                "children": index % 2,
                "babies": 0,
                "total_guests": 2 + index % 2,
                "meal": "BB" if index % 3 else "SC",
                "meal_name": "含早餐" if index % 3 else "不含餐",
                "country_code": "PRT" if high_risk else "GBR",
                "country_name": "葡萄牙" if high_risk else "英国",
                "market_segment": "Groups" if high_risk else "Direct",
                "market_segment_name": "团队" if high_risk else "直接预订",
                "distribution_channel": "TA/TO" if high_risk else "Direct",
                "is_repeated_guest": 0 if high_risk else 1,
                "is_repeated_guest_label": "新客户" if high_risk else "回头客",
                "previous_cancellations": 1 if high_risk else 0,
                "previous_bookings_not_canceled": 0 if high_risk else 2,
                "reserved_room_type": "A",
                "assigned_room_type": "A" if not high_risk else "D",
                "room_type_changed": 1 if high_risk else 0,
                "booking_changes": 0 if high_risk else 2,
                "deposit_type": "Non Refund" if high_risk else "No Deposit",
                "deposit_type_name": "不可退订金" if high_risk else "无订金",
                "days_in_waiting_list": 5 if high_risk else 0,
                "customer_type": "Transient" if high_risk else "Contract",
                "customer_type_name": "散客" if high_risk else "合约客户",
                "adr": 120.0 + index if high_risk else 80.0 + index,
                "required_car_parking_spaces": 0 if high_risk else 1,
                "total_of_special_requests": 0 if high_risk else 2,
                "reservation_status": "Canceled" if high_risk else "Check-Out",
                "reservation_status_date": "2017-01-02",
                "is_deleted": 0,
            }
        )
    return pd.DataFrame(rows)


def test_model_feature_columns_match_field_contract():
    from scripts.train_model import MODEL_FEATURE_COLUMNS

    assert MODEL_FEATURE_COLUMNS == EXPECTED_FEATURE_COLUMNS


def test_train_and_save_writes_contract_outputs(tmp_path):
    from scripts.train_model import train_and_save

    input_csv = tmp_path / "cleaned_hotel_bookings.csv"
    output_dir = tmp_path / "models"
    make_training_frame().to_csv(input_csv, index=False, encoding="utf-8-sig")

    result = train_and_save(input_csv, output_dir)

    model_path = output_dir / "cancellation_model.pkl"
    feature_columns_path = output_dir / "feature_columns.json"
    metrics_path = output_dir / "metrics.json"

    assert result.model_path == model_path
    assert result.feature_columns_path == feature_columns_path
    assert result.metrics_path == metrics_path
    assert model_path.exists()
    assert feature_columns_path.exists()
    assert metrics_path.exists()

    feature_columns = json.loads(feature_columns_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    assert feature_columns == EXPECTED_FEATURE_COLUMNS
    assert metrics["selected_model"] in {"logistic_regression", "random_forest"}
    assert metrics["model_version"].endswith("_v1")
    assert set(metrics["metrics"]) == {
        "accuracy",
        "precision_score",
        "recall_score",
        "f1_score",
        "train_score",
        "test_score",
    }
    assert set(metrics["comparison"]) == {"logistic_regression", "random_forest"}
    assert len(metrics["confusion_matrix"]) == 2
    assert len(metrics["confusion_matrix"][0]) == 2

    with model_path.open("rb") as model_file:
        model = pickle.load(model_file)
    probabilities = model.predict_proba(make_training_frame()[EXPECTED_FEATURE_COLUMNS].head(2))
    assert probabilities.shape == (2, 2)


def test_cli_accepts_input_csv_and_output_dir(tmp_path):
    input_csv = tmp_path / "cleaned_hotel_bookings.csv"
    output_dir = tmp_path / "models"
    make_training_frame().to_csv(input_csv, index=False, encoding="utf-8-sig")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/train_model.py",
            "--input-csv",
            str(input_csv),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "selected_model=" in completed.stdout
    assert (output_dir / "cancellation_model.pkl").exists()
    assert (output_dir / "feature_columns.json").exists()
    assert (output_dir / "metrics.json").exists()
