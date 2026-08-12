"""Legacy M0 dataset behavior kept only for baseline reproducibility."""

import glob
import os
import random

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


class CustomKlineDataset(Dataset):
    """Frozen legacy loader; new research code must use StrictKlineDataset."""

    def __init__(self, data_path, data_type='train', lookback_window=90, predict_window=10,
                 clip=5.0, seed=100, train_end_date='2023-01-01', val_end_date='2024-01-01'):
        self.data_path = data_path
        self.data_type = data_type
        self.lookback_window = lookback_window
        self.predict_window = predict_window
        self.window = lookback_window + predict_window + 1
        self.clip = clip
        self.seed = seed
        self.train_end_date = pd.to_datetime(train_end_date)
        self.val_end_date = pd.to_datetime(val_end_date)

        self.feature_list = ['open', 'high', 'low', 'close', 'volume', 'amount']
        self.time_feature_list = ['minute', 'hour', 'weekday', 'day', 'month']

        self.py_rng = random.Random(seed)

        self._load_and_preprocess_multi_stock()
        self._build_global_index_map()

        print(f"[{data_type.upper()}] Loaded {len(self.stock_data)} stocks, Total available windows: {len(self.global_index_map)}")

    def _load_and_preprocess_multi_stock(self):
        if os.path.isdir(self.data_path):
            csv_files = glob.glob(os.path.join(self.data_path, "*.csv"))
        else:
            csv_files = [self.data_path]

        self.stock_data = {}

        for fpath in csv_files:
            symbol = os.path.splitext(os.path.basename(fpath))[0]
            df = pd.read_csv(fpath)

            df['timestamps'] = pd.to_datetime(df['timestamps'])
            df = df.sort_values('timestamps').reset_index(drop=True)

            if 'amount' not in df.columns:
                df['amount'] = df['volume'] * (df['open'] + df['high'] + df['low'] + df['close']) / 4.0

            df['minute'] = 0
            df['hour'] = 9
            df['weekday'] = df['timestamps'].dt.weekday
            df['day'] = df['timestamps'].dt.day
            df['month'] = df['timestamps'].dt.month

            self.stock_data[symbol] = df

    def _build_global_index_map(self):
        self.global_index_map = []
        gap_buffer = 5

        for symbol, df in self.stock_data.items():
            data_len = len(df)
            if data_len < self.window:
                continue

            val_start_series = df['timestamps'] >= self.train_end_date
            test_start_series = df['timestamps'] >= self.val_end_date

            first_val_idx = df[val_start_series].index[0] if val_start_series.any() else data_len
            first_test_idx = df[test_start_series].index[0] if test_start_series.any() else data_len

            for i in range(data_len - self.window + 1):
                target_start_idx = i + self.lookback_window
                target_end_time = df.loc[i + self.window - 1, 'timestamps']

                if self.data_type == 'train':
                    if target_end_time >= self.train_end_date:
                        continue
                elif self.data_type == 'val':
                    if target_start_idx < first_val_idx + gap_buffer:
                        continue
                    if target_end_time >= self.val_end_date:
                        continue
                elif self.data_type == 'test':
                    if target_start_idx < first_test_idx + gap_buffer:
                        continue

                window_df = df.iloc[i:i + self.window]
                nan_count = window_df[self.feature_list].isnull().sum().sum()
                total_elements = len(window_df) * len(self.feature_list)
                nan_ratio = nan_count / total_elements

                if nan_ratio > 0.10:
                    continue

                self.global_index_map.append((symbol, i))

    def set_epoch_seed(self, epoch):
        pass

    def __len__(self):
        return len(self.global_index_map)

    def __getitem__(self, idx):
        if idx >= len(self.global_index_map):
            raise IndexError("Index out of bounds")

        symbol, start_idx = self.global_index_map[idx]
        df = self.stock_data[symbol]
        window_df = df.iloc[start_idx:start_idx + self.window].copy()

        if window_df[self.feature_list].isnull().any().any():
            window_df[self.feature_list] = window_df[self.feature_list].ffill().fillna(0.0)

        x_double = window_df[self.feature_list].values.astype(np.float64)
        x_stamp = window_df[self.time_feature_list].values.astype(np.float32)

        x_lookback = x_double[:self.lookback_window]
        x_mean = np.mean(x_lookback, axis=0)
        x_std = np.std(x_lookback, axis=0)
        x_std = np.where(x_std < 1e-6, 1.0, x_std)
        x_norm = (x_double - x_mean) / (x_std + 1e-5)
        x_norm = np.clip(x_norm, -self.clip, self.clip).astype(np.float32)

        x_tensor = torch.from_numpy(x_norm)
        x_stamp_tensor = torch.from_numpy(x_stamp)

        return x_tensor, x_stamp_tensor
