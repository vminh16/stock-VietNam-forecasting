import numpy as np
import pandas as pd

from .metrics import DATE_COLUMNS


# Locked M2 inference conventions:
# - Overlapping horizons and market-wide factors break independent-window tests,
#   so every metric is aggregated by forecast date first and dates are resampled
#   in contiguous blocks (Politis-Romano stationary bootstrap).
# - Paired candidates share one resampled date index; a comparison is refused
#   unless both candidates cover identical dates with identical origin counts.
# - Ratio metrics are recomputed from resampled numerator and denominator sums
#   inside each replicate; daily ratios are never averaged.
# - `verdict` states the sign of the paired difference only. Higher is better for
#   DA, MW-DA, RankIC, and HitRate@Top10; lower is better for CRPS and
#   interval_width; coverage is judged against its nominal 0.80 target.
SCHEMA_VERSION = "m2_3_block_bootstrap_v1"
DEFAULT_MEAN_BLOCK_DATES = 10
DEFAULT_REPLICATES = 5000
DEFAULT_CONFIDENCE = 0.95

RATIO_METRICS = {
    "DA": ("correct_count", "origin_count", 100.0),
    "MW-DA": ("correct_abs_return", "total_abs_return", 100.0),
    "CRPS": ("crps_sum", "origin_count", 1.0),
    "coverage": ("coverage_sum", "origin_count", 1.0),
    "interval_width": ("width_sum", "origin_count", 1.0),
}

DATE_MEAN_METRICS = {
    "RankIC": ("rank_ic", 1.0),
    "HitRate@Top10": ("hit_rate_top10", 100.0),
}

POOLED_METRICS = (
    "DA",
    "MW-DA",
    "RankIC",
    "HitRate@Top10",
    "CRPS",
    "coverage",
    "interval_width",
)

COMPARISON_COLUMNS = [
    "metric",
    "left_id",
    "right_id",
    "left_estimate",
    "right_estimate",
    "difference",
    "ci_low",
    "ci_high",
    "confidence",
    "replicates",
    "mean_block_dates",
    "n_paired_dates",
    "verdict",
]


def _validate_dates(frame, label):
    missing = [column for column in DATE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing columns: {missing}")
    if frame.empty:
        raise ValueError(f"{label} is empty")
    if frame.duplicated(["fold_id", "origin_date"]).any():
        raise ValueError(f"{label} has a duplicate evaluation date")
    return frame.sort_values(["fold_id", "origin_date"], kind="mergesort").reset_index(
        drop=True
    )


def pooled_metric(dates, metric):
    if metric in RATIO_METRICS:
        numerator, denominator, scale = RATIO_METRICS[metric]
        total = float(dates[denominator].sum())
        if total == 0.0:
            raise ValueError(f"{metric} is undefined without a positive denominator")
        return float(dates[numerator].sum()) / total * scale
    if metric in DATE_MEAN_METRICS:
        column, scale = DATE_MEAN_METRICS[metric]
        return float(np.nanmean(dates[column].to_numpy(dtype=np.float64))) * scale
    raise ValueError(f"Unknown pooled metric: {metric}")


def stationary_block_indices(n_dates, mean_block, replicates, seed):
    if n_dates < 1 or replicates < 1:
        raise ValueError("n_dates and replicates must be positive")
    if mean_block < 1:
        raise ValueError("mean_block must be at least one date")

    generator = np.random.default_rng(seed)
    restart = 1.0 / mean_block
    indices = np.empty((replicates, n_dates), dtype=np.int64)
    indices[:, 0] = generator.integers(0, n_dates, size=replicates)
    restarts = generator.random((replicates, n_dates - 1)) < restart
    fresh = generator.integers(0, n_dates, size=(replicates, n_dates - 1))
    for position in range(1, n_dates):
        continued = (indices[:, position - 1] + 1) % n_dates
        indices[:, position] = np.where(
            restarts[:, position - 1], fresh[:, position - 1], continued
        )
    return indices


def _replicate_values(dates, metric, indices):
    if metric in RATIO_METRICS:
        numerator, denominator, scale = RATIO_METRICS[metric]
        top = dates[numerator].to_numpy(dtype=np.float64)[indices].sum(axis=1)
        bottom = dates[denominator].to_numpy(dtype=np.float64)[indices].sum(axis=1)
        return np.divide(
            top, bottom, out=np.full_like(top, np.nan), where=bottom != 0.0
        ) * scale
    column, scale = DATE_MEAN_METRICS[metric]
    return np.nanmean(dates[column].to_numpy(dtype=np.float64)[indices], axis=1) * scale


def compare_candidates(
    left,
    right,
    left_id,
    right_id,
    metrics=POOLED_METRICS,
    mean_block=DEFAULT_MEAN_BLOCK_DATES,
    replicates=DEFAULT_REPLICATES,
    seed=None,
    confidence=DEFAULT_CONFIDENCE,
):
    if seed is None:
        raise ValueError("A registered seed is required for reproducible inference")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie in (0, 1)")

    left = _validate_dates(left, f"Date frame {left_id}")
    right = _validate_dates(right, f"Date frame {right_id}")
    keys = ["fold_id", "origin_date"]
    if not left[keys].equals(right[keys]):
        raise ValueError("Paired candidate date sets differ")
    if not left["origin_count"].equals(right["origin_count"]):
        raise ValueError("Paired candidate origin counts differ")

    indices = stationary_block_indices(len(left), mean_block, replicates, seed)
    tail = (1.0 - confidence) / 2.0 * 100.0

    records = []
    for metric in metrics:
        difference = _replicate_values(left, metric, indices) - _replicate_values(
            right, metric, indices
        )
        low, high = np.nanpercentile(difference, [tail, 100.0 - tail])
        point = pooled_metric(left, metric) - pooled_metric(right, metric)
        if low > 0.0:
            verdict = f"{left_id} higher"
        elif high < 0.0:
            verdict = f"{right_id} higher"
        else:
            verdict = "insufficient evidence"
        records.append(
            {
                "metric": metric,
                "left_id": left_id,
                "right_id": right_id,
                "left_estimate": pooled_metric(left, metric),
                "right_estimate": pooled_metric(right, metric),
                "difference": point,
                "ci_low": float(low),
                "ci_high": float(high),
                "confidence": confidence,
                "replicates": replicates,
                "mean_block_dates": mean_block,
                "n_paired_dates": len(left),
                "verdict": verdict,
            }
        )
    return pd.DataFrame(records, columns=COMPARISON_COLUMNS)
