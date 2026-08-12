import numpy as np


def normalize_lookback_window(values, lookback_length, clip=5.0):
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("values must be a two-dimensional array")
    if lookback_length <= 0 or lookback_length > len(values):
        raise ValueError("lookback_length must be inside the input window")

    lookback = values[:lookback_length]
    mean = lookback.mean(axis=0)
    raw_std = lookback.std(axis=0)
    scale = np.where(raw_std < 1e-6, 1.0, raw_std)
    normalized = np.clip((values - mean) / (scale + 1e-5), -clip, clip)
    return normalized, mean, scale
