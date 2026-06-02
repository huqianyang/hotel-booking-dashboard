from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

OFFLINE_CUTOFF_DATE = "2017-01-12"
REALTIME_START_DATE = "2017-01-13"
ARRIVAL_DATE_COLUMN = "arrival_date"


@dataclass(frozen=True)
class SplitCounts:
    offline_rows: int
    realtime_rows: int
    total_rows: int


def filter_offline_model_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Return rows allowed for offline model train/test splitting."""
    _require_arrival_date(frame)
    arrival_dates = pd.to_datetime(frame[ARRIVAL_DATE_COLUMN])
    return frame.loc[arrival_dates <= pd.Timestamp(OFFLINE_CUTOFF_DATE)].copy()


def filter_realtime_event_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Return rows reserved for simulated realtime event generation."""
    _require_arrival_date(frame)
    arrival_dates = pd.to_datetime(frame[ARRIVAL_DATE_COLUMN])
    return frame.loc[arrival_dates >= pd.Timestamp(REALTIME_START_DATE)].copy()


def count_split_rows(frame: pd.DataFrame) -> SplitCounts:
    """Count offline and realtime rows using the fixed project date boundary."""
    return SplitCounts(
        offline_rows=len(filter_offline_model_data(frame)),
        realtime_rows=len(filter_realtime_event_data(frame)),
        total_rows=len(frame),
    )


def _require_arrival_date(frame: pd.DataFrame) -> None:
    if ARRIVAL_DATE_COLUMN not in frame.columns:
        raise ValueError(f"cleaned data missing required boundary column: {ARRIVAL_DATE_COLUMN}")
