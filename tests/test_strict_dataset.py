import numpy as np
import pandas as pd
import pytest
import torch

from data_pipeline.transforms import normalize_lookback_window
from finetune_csv.strict_dataset import StrictKlineDataset


def write_curated_symbol(root, rows=20, split_at=None):
    symbols = root / "symbols"
    symbols.mkdir(parents=True)
    dates = pd.bdate_range("2024-01-01", periods=rows)
    values = np.arange(rows, dtype=float) + 100
    segment = np.zeros(rows, dtype=int)
    if split_at is not None:
        segment[split_at:] = 1
    pd.DataFrame(
        {
            "security_id": "HOSE_AAA",
            "symbol": "AAA",
            "timestamps": dates + pd.Timedelta(hours=9),
            "session_id": range(rows),
            "segment_id": segment,
            "open": values,
            "high": values + 2,
            "low": values - 2,
            "close": values + 1,
            "volume": values * 100,
            "amount": values * 100000,
            "amount_source": "derived_ohlc4",
        }
    ).to_csv(symbols / "AAA.csv", index=False)


def test_windows_never_cross_segments(tmp_path):
    write_curated_symbol(tmp_path, rows=20, split_at=10)
    dataset = StrictKlineDataset(
        tmp_path, data_type="all", lookback_window=3, predict_window=2
    )

    assert len(dataset) == 10
    for symbol, segment_id, start_idx in dataset.global_index_map:
        frame = dataset.stock_data[symbol]
        window = frame.iloc[start_idx:start_idx + dataset.window]
        assert window["segment_id"].nunique() == 1
        assert window["segment_id"].iloc[0] == segment_id


def test_strict_dataset_rejects_non_finite_values(tmp_path):
    write_curated_symbol(tmp_path)
    path = tmp_path / "symbols" / "AAA.csv"
    frame = pd.read_csv(path)
    frame.loc[3, "close"] = np.nan
    frame.to_csv(path, index=False)

    with pytest.raises(ValueError, match="non-finite"):
        StrictKlineDataset(tmp_path, data_type="all", lookback_window=3, predict_window=2)


def test_normalization_uses_lookback_only(tmp_path):
    write_curated_symbol(tmp_path, rows=8)
    dataset = StrictKlineDataset(
        tmp_path, data_type="all", lookback_window=3, predict_window=2
    )
    first, _ = dataset[0]

    path = tmp_path / "symbols" / "AAA.csv"
    frame = pd.read_csv(path)
    frame.loc[3:5, ["open", "high", "low", "close"]] *= 100
    frame.to_csv(path, index=False)
    changed = StrictKlineDataset(
        tmp_path, data_type="all", lookback_window=3, predict_window=2
    )
    second, _ = changed[0]

    assert torch.allclose(first[:3], second[:3])


def test_validation_purge_follows_horizon(tmp_path):
    write_curated_symbol(tmp_path, rows=30)
    dataset = StrictKlineDataset(
        tmp_path,
        data_type="val",
        lookback_window=3,
        predict_window=3,
        train_end_date="2024-01-15",
        val_end_date="2024-02-01",
    )

    first_val_session = dataset.stock_data["AAA"].loc[
        dataset.stock_data["AAA"]["timestamps"] >= pd.Timestamp("2024-01-15"),
        "session_id",
    ].iloc[0]
    for symbol, _, start_idx in dataset.global_index_map:
        frame = dataset.stock_data[symbol]
        target_start = frame.iloc[start_idx + dataset.lookback_window]["session_id"]
        assert target_start >= first_val_session + dataset.predict_window


def test_shared_normalization_does_not_use_future_rows():
    values = np.arange(36, dtype=float).reshape(6, 6) + 1
    first, _, _ = normalize_lookback_window(values, lookback_length=3, clip=5.0)
    changed = values.copy()
    changed[3:] *= 1000
    second, _, _ = normalize_lookback_window(changed, lookback_length=3, clip=5.0)

    np.testing.assert_allclose(first[:3], second[:3])


def test_shared_normalization_handles_constant_feature():
    values = np.ones((6, 6), dtype=float)
    normalized, mean, scale = normalize_lookback_window(
        values, lookback_length=3, clip=5.0
    )

    assert np.isfinite(normalized).all()
    np.testing.assert_array_equal(mean, np.ones(6))
    np.testing.assert_array_equal(scale, np.ones(6))
