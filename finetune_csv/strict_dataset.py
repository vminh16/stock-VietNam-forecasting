"""Strict segmented dataset for post-M0 Kronos research."""

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from data_pipeline.contracts import FEATURE_COLUMNS
from data_pipeline.transforms import normalize_lookback_window

REQUIRED_COLUMNS = [
    "security_id", "symbol", "timestamps", "session_id", "segment_id",
    *FEATURE_COLUMNS,
]


class StrictKlineDataset(Dataset):
    def __init__(self, data_path, data_type="train", lookback_window=63,
                 predict_window=5, clip=5.0, train_end_date="2023-01-01",
                 val_end_date="2024-01-01"):
        self.data_path = Path(data_path)
        self.data_type = data_type
        self.lookback_window = lookback_window
        self.predict_window = predict_window
        self.window = lookback_window + predict_window + 1
        self.clip = clip
        self.train_end_date = pd.Timestamp(train_end_date)
        self.val_end_date = pd.Timestamp(val_end_date)
        self.time_feature_list = ["minute", "hour", "weekday", "day", "month"]

        self.stock_data = self._load_symbols()
        self.global_index_map = self._build_index()

    def _load_symbols(self):
        symbol_dir = self.data_path / "symbols"
        files = sorted(symbol_dir.glob("*.csv"))
        if not files:
            raise ValueError(f"No curated symbol files found in {symbol_dir}")

        stock_data = {}
        for path in files:
            frame = pd.read_csv(path)
            missing = set(REQUIRED_COLUMNS) - set(frame.columns)
            if missing:
                raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
            frame["timestamps"] = pd.to_datetime(frame["timestamps"], errors="coerce")
            numeric = frame[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
            if frame["timestamps"].isna().any() or not np.isfinite(numeric.to_numpy()).all():
                raise ValueError(f"{path.name} contains non-finite strict data")
            frame[FEATURE_COLUMNS] = numeric
            frame = frame.sort_values(["segment_id", "session_id"]).reset_index(drop=True)
            for _, segment in frame.groupby("segment_id"):
                if len(segment) > 1 and not segment["session_id"].diff().dropna().eq(1).all():
                    raise ValueError(f"{path.name} has a session gap inside a segment")
            frame["minute"] = frame["timestamps"].dt.minute
            frame["hour"] = frame["timestamps"].dt.hour
            frame["weekday"] = frame["timestamps"].dt.weekday
            frame["day"] = frame["timestamps"].dt.day
            frame["month"] = frame["timestamps"].dt.month
            stock_data[path.stem] = frame
        return stock_data

    def _partition_allows(self, frame, start_idx):
        if self.data_type == "all":
            return True
        target_start_idx = start_idx + self.lookback_window
        target_end_idx = start_idx + self.window - 1
        target_start = frame.iloc[target_start_idx]
        target_end_time = frame.iloc[target_end_idx]["timestamps"]

        if self.data_type == "train":
            return target_end_time < self.train_end_date

        if self.data_type == "val":
            boundary = self.train_end_date
            upper = self.val_end_date
        elif self.data_type == "test":
            boundary = self.val_end_date
            upper = None
        else:
            raise ValueError(f"Unsupported data_type: {self.data_type}")

        boundary_rows = frame[frame["timestamps"] >= boundary]
        if boundary_rows.empty:
            return False
        first_session = boundary_rows.iloc[0]["session_id"]
        if target_start["session_id"] < first_session + self.predict_window:
            return False
        return upper is None or target_end_time < upper

    def _build_index(self):
        index = []
        for symbol, frame in self.stock_data.items():
            for segment_id, segment in frame.groupby("segment_id", sort=True):
                if len(segment) < self.window:
                    continue
                first_idx = int(segment.index.min())
                last_start = int(segment.index.max()) - self.window + 1
                for start_idx in range(first_idx, last_start + 1):
                    if self._partition_allows(frame, start_idx):
                        index.append((symbol, int(segment_id), start_idx))
        return index

    def __len__(self):
        return len(self.global_index_map)

    def __getitem__(self, idx):
        symbol, _, start_idx = self.global_index_map[idx]
        frame = self.stock_data[symbol].iloc[start_idx:start_idx + self.window]
        values = frame[FEATURE_COLUMNS].to_numpy(dtype=np.float64)
        normalized, _, _ = normalize_lookback_window(
            values, self.lookback_window, self.clip
        )
        stamps = frame[self.time_feature_list].to_numpy(dtype=np.float32)
        return (
            torch.from_numpy(normalized.astype(np.float32)),
            torch.from_numpy(stamps),
        )
