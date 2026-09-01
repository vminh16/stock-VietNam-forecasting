import numpy as np

from data_pipeline.transforms import normalize_lookback_window


# M2.4 data diagnostics. These functions describe the data, not a model.
# - variance_ratio implements Lo-MacKinlay (1988) with overlapping q-period
#   returns and their heteroskedasticity-consistent statistic. VR = 1 is the
#   random-walk case that makes cumulative variance grow like h; VR < 1 is mean
#   reversion and VR > 1 is trending. z_star is asymptotically standard normal.
# - normalization_variants isolates the normalization effect inside a lookback
#   comparison: variant `short` and variant `short_scaled_by_long` cover exactly
#   the same rows and differ only in which window supplied mean and scale.
MIN_VARIANCE_RATIO_RETURNS = 30
CLIP = 5.0


def variance_ratio(returns, q):
    values = np.asarray(returns, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("returns must be one-dimensional")
    if q < 2:
        raise ValueError("q must be at least two periods")
    if values.size < max(MIN_VARIANCE_RATIO_RETURNS, q + 1):
        raise ValueError("Return series is too short for a variance ratio")

    total = values.size
    mean = values.mean()
    deviations = values - mean
    sum_squares = float((deviations**2).sum())
    if sum_squares == 0.0:
        raise ValueError("Return series has no variance")

    single_variance = sum_squares / (total - 1)
    cumulative = np.convolve(values, np.ones(q), mode="valid") - q * mean
    scale = q * (total - q + 1) * (1.0 - q / total)
    q_variance = float((cumulative**2).sum()) / scale
    ratio = q_variance / single_variance

    squared = deviations**2
    theta = 0.0
    for lag in range(1, q):
        delta = float((squared[lag:] * squared[:-lag]).sum()) / sum_squares**2
        theta += (2.0 * (q - lag) / q) ** 2 * delta
    z_star = (ratio - 1.0) / np.sqrt(theta) if theta > 0.0 else np.nan
    return ratio, float(z_star)


def normalization_variants(window, short_lookback, clip=CLIP):
    values = np.asarray(window, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("window must be two-dimensional")
    long_lookback = len(values)
    if not 0 < short_lookback < long_lookback:
        raise ValueError("short_lookback must be shorter than the window")

    tail = values[-short_lookback:]
    short_normalized, short_mean, short_scale = normalize_lookback_window(
        tail, short_lookback, clip=clip
    )
    long_normalized, long_mean, long_scale = normalize_lookback_window(
        values, long_lookback, clip=clip
    )
    raw_short = (tail - short_mean) / (short_scale + 1e-5)
    raw_long = (values - long_mean) / (long_scale + 1e-5)
    raw_scaled_by_long = (tail - long_mean) / (long_scale + 1e-5)
    return {
        "short": short_normalized,
        "long": long_normalized,
        "short_scaled_by_long": np.clip(raw_scaled_by_long, -clip, clip),
        "scale_ratio": short_scale / long_scale,
        "mean_shift": (short_mean - long_mean) / long_scale,
        "clip_rate": {
            "short": float((np.abs(raw_short) >= clip).mean()),
            "long": float((np.abs(raw_long) >= clip).mean()),
            "short_scaled_by_long": float((np.abs(raw_scaled_by_long) >= clip).mean()),
        },
        "abs_z_mean": {
            "short": float(np.abs(raw_short).mean()),
            "long": float(np.abs(raw_long).mean()),
            "short_scaled_by_long": float(np.abs(raw_scaled_by_long).mean()),
        },
    }


def clip_rate(window, lookback, clip=CLIP):
    values = np.asarray(window, dtype=np.float64)
    reference = values[:lookback]
    mean = reference.mean(axis=0)
    raw_scale = reference.std(axis=0)
    scale = np.where(raw_scale < 1e-6, 1.0, raw_scale)
    raw = (values - mean) / (scale + 1e-5)
    return float((np.abs(raw) >= clip).mean())
