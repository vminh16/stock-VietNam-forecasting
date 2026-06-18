import os
import tempfile
import pandas as pd
import numpy as np
import pytest
import torch
from finetune_base_model import CustomKlineDataset

def create_mock_stock_data(temp_dir):
    # Stock A: 200 days, normal
    dates_a = pd.date_range(start="2022-01-01", periods=200, freq="D")
    df_a = pd.DataFrame({
        "timestamps": dates_a,
        "open": np.linspace(100, 150, 200),
        "high": np.linspace(105, 155, 200),
        "low": np.linspace(95, 145, 200),
        "close": np.linspace(101, 151, 200),
        "volume": np.random.randint(1000, 5000, 200),
        "amount": np.random.randint(100000, 500000, 200)
    })
    df_a.to_csv(os.path.join(temp_dir, "STOCK_A.csv"), index=False)

    # Stock B: 200 days, with some NaNs and flat pricing (zero std risk)
    dates_b = pd.date_range(start="2022-01-01", periods=200, freq="D")
    df_b = pd.DataFrame({
        "timestamps": dates_b,
        "open": np.full(200, 50.0),
        "high": np.full(200, 50.0),
        "low": np.full(200, 50.0),
        "close": np.full(200, 50.0),
        "volume": np.zeros(200),  # Flat volume -> std = 0
        "amount": np.zeros(200)   # Flat amount -> std = 0
    })
    # Inject NaNs to check filtering
    df_b.loc[:20, ["open", "high", "low", "close"]] = np.nan
    df_b.to_csv(os.path.join(temp_dir, "STOCK_B.csv"), index=False)


def test_no_stock_boundary_crossing():
    with tempfile.TemporaryDirectory() as temp_dir:
        create_mock_stock_data(temp_dir)
        
        # Instantiate dataset
        dataset = CustomKlineDataset(
            data_path=temp_dir,
            data_type="train",
            lookback_window=50,
            predict_window=5,
            clip=5.0,
            seed=42,
            train_end_date="2022-06-01",
            val_end_date="2022-08-01"
        )
        
        # Verify that all windows belong to a single stock
        for idx in range(len(dataset)):
            symbol, start_idx = dataset.global_index_map[idx]
            # Verify the start index fits within the length of the stock df
            df = dataset.stock_data[symbol]
            assert start_idx >= 0
            assert start_idx + dataset.window <= len(df)


def test_temporal_leakage():
    with tempfile.TemporaryDirectory() as temp_dir:
        create_mock_stock_data(temp_dir)
        
        train_end = "2022-06-01"
        val_end = "2022-07-15"
        
        train_dataset = CustomKlineDataset(
            data_path=temp_dir,
            data_type="train",
            lookback_window=30,
            predict_window=5,
            clip=5.0,
            train_end_date=train_end,
            val_end_date=val_end
        )
        
        val_dataset = CustomKlineDataset(
            data_path=temp_dir,
            data_type="val",
            lookback_window=30,
            predict_window=5,
            clip=5.0,
            train_end_date=train_end,
            val_end_date=val_end
        )
        
        test_dataset = CustomKlineDataset(
            data_path=temp_dir,
            data_type="test",
            lookback_window=30,
            predict_window=5,
            clip=5.0,
            train_end_date=train_end,
            val_end_date=val_end
        )
        
        train_end_dt = pd.to_datetime(train_end)
        val_end_dt = pd.to_datetime(val_end)
        
        # Train dataset windows must end BEFORE train_end
        for idx in range(len(train_dataset)):
            symbol, start_idx = train_dataset.global_index_map[idx]
            df = train_dataset.stock_data[symbol]
            end_time = df.loc[start_idx + train_dataset.window - 1, "timestamps"]
            assert end_time < train_end_dt
            
        # Val dataset windows must end before val_end and target starts after train_end + gap_buffer (5 days)
        for idx in range(len(val_dataset)):
            symbol, start_idx = val_dataset.global_index_map[idx]
            df = val_dataset.stock_data[symbol]
            
            first_val_idx = df[df['timestamps'] >= train_end_dt].index[0]
            target_start_idx = start_idx + val_dataset.lookback_window
            
            assert target_start_idx >= first_val_idx + 5, "Val target started too early (gap buffer violated)"
            
            end_time = df.loc[start_idx + val_dataset.window - 1, "timestamps"]
            assert end_time < val_end_dt
            
        # Test dataset windows target starts after val_end + gap_buffer (5 days)
        for idx in range(len(test_dataset)):
            symbol, start_idx = test_dataset.global_index_map[idx]
            df = test_dataset.stock_data[symbol]
            
            first_test_idx = df[df['timestamps'] >= val_end_dt].index[0]
            target_start_idx = start_idx + test_dataset.lookback_window
            
            assert target_start_idx >= first_test_idx + 5, "Test target started too early (gap buffer violated)"


def test_zero_division_protection():
    with tempfile.TemporaryDirectory() as temp_dir:
        create_mock_stock_data(temp_dir)
        
        # Stock B contains flat volume and amount (std = 0)
        # Verify that loading from Stock B does not throw division by zero and has no NaNs/Infs
        dataset = CustomKlineDataset(
            data_path=temp_dir,
            data_type="all", # Train/Val/Test filters won't apply to "all" (fallback to full df)
            lookback_window=30,
            predict_window=5,
            clip=5.0,
            train_end_date="2099-01-01", # High end date to include all
            val_end_date="2099-01-01"
        )
        
        # Verify indices pointing to STOCK_B
        stock_b_windows = [i for i, (sym, _) in enumerate(dataset.global_index_map) if sym == "STOCK_B"]
        assert len(stock_b_windows) > 0, "No valid windows extracted for Stock B"
        
        # Fetch a window and verify Z-scored values are valid finite numbers
        idx = stock_b_windows[0]
        x_tensor, x_stamp_tensor = dataset[idx]
        
        assert not torch.isnan(x_tensor).any(), "Z-scored tensor contains NaNs"
        assert not torch.isinf(x_tensor).any(), "Z-scored tensor contains Infs"
        
        # Flat volume and amount should become 0 after subtraction and division by epsilon
        # Let's check volume and amount columns (indexes 4 and 5)
        assert torch.allclose(x_tensor[:, 4], torch.zeros_like(x_tensor[:, 4])), "Flat volume did not resolve to 0"
        assert torch.allclose(x_tensor[:, 5], torch.zeros_like(x_tensor[:, 5])), "Flat amount did not resolve to 0"


def test_zscore_no_leakage():
    with tempfile.TemporaryDirectory() as temp_dir:
        # We will create two directories with identical historical (first 100 days) data, 
        # but different future/target data (next 11 days).
        dir_1 = os.path.join(temp_dir, "dir_1")
        dir_2 = os.path.join(temp_dir, "dir_2")
        os.makedirs(dir_1)
        os.makedirs(dir_2)
        
        # Lookback = 100, predict = 10, window = 111
        lookback = 100
        predict = 10
        dates = pd.date_range(start="2022-01-01", periods=111, freq="D")
        
        # First 100 days are identical
        prices_base = np.linspace(100, 120, 100)
        # Next 11 days (predict + 1 target) are different
        prices_future_1 = np.linspace(120, 130, 11)
        prices_future_2 = np.linspace(120, 1000, 11) # massive jump
        
        open_1 = np.concatenate([prices_base, prices_future_1])
        open_2 = np.concatenate([prices_base, prices_future_2])
        
        df_1 = pd.DataFrame({
            "timestamps": dates,
            "open": open_1,
            "high": open_1 + 2,
            "low": open_1 - 2,
            "close": open_1 + 1,
            "volume": np.ones(111) * 1000,
            "amount": np.ones(111) * 100000
        })
        
        df_2 = pd.DataFrame({
            "timestamps": dates,
            "open": open_2,
            "high": open_2 + 2,
            "low": open_2 - 2,
            "close": open_2 + 1,
            "volume": np.ones(111) * 1000,
            "amount": np.ones(111) * 100000
        })
        
        df_1.to_csv(os.path.join(dir_1, "STOCK.csv"), index=False)
        df_2.to_csv(os.path.join(dir_2, "STOCK.csv"), index=False)
        
        # Load dataset 1
        ds_1 = CustomKlineDataset(
            data_path=dir_1,
            data_type="train",
            lookback_window=lookback,
            predict_window=predict,
            clip=5.0,
            train_end_date="2099-01-01",
            val_end_date="2099-01-01"
        )
        
        # Load dataset 2
        ds_2 = CustomKlineDataset(
            data_path=dir_2,
            data_type="train",
            lookback_window=lookback,
            predict_window=predict,
            clip=5.0,
            train_end_date="2099-01-01",
            val_end_date="2099-01-01"
        )
        
        x_1, _ = ds_1[0]
        x_2, _ = ds_2[0]
        
        # Lookback parts (first 100 rows) of the normalized tensors should be identical
        # If there is leakage, the massive jump in df_2 future window will pull up the mean
        # and standard deviation of the entire window, resulting in different normalized values for the first 100 rows.
        assert torch.allclose(x_1[:lookback], x_2[:lookback], atol=1e-4), "Z-score leakage detected! Lookback normalization is affected by future values."

