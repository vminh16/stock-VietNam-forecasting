import numpy as np
import pandas as pd
from scipy import stats


# Locked M2 conventions:
# - direction(0) is -1, matching the frozen M0 implementation.
# - Point metrics use the ensemble mean cumulative return at the final horizon step.
# - CRPS is the marginal ensemble score averaged over horizon steps 1..H.
# - Interval coverage and width use the 10th and 90th sample percentiles at step H.
# - RankIC is 0.0 when a date carries no predicted dispersion above
#   DISPERSION_TOLERANCE; Spearman is undefined there, ranking float noise would
#   invent a correlation, and dropping the date would break paired origins.
# - HitRate@Top10 is NaN for a date with fewer than ten eligible symbols.
SCHEMA_VERSION = "m2_2_metrics_v1"
INTERVAL_QUANTILES = (0.10, 0.90)
TOP_K = 10
DISPERSION_TOLERANCE = 1e-12

FORECAST_COLUMNS = [
    "fold_id",
    "origin_id",
    "security_id",
    "origin_date",
    "sample_id",
    "horizon_step",
    "predicted_return",
    "actual_return",
]

ORIGIN_COLUMNS = [
    "fold_id",
    "origin_id",
    "security_id",
    "origin_date",
    "horizon",
    "sample_count",
    "predicted_return",
    "actual_return",
    "crps",
    "interval_covered",
    "interval_width",
]

DATE_COLUMNS = [
    "fold_id",
    "origin_date",
    "horizon",
    "sample_count",
    "origin_count",
    "symbol_count",
    "correct_count",
    "correct_abs_return",
    "total_abs_return",
    "rank_ic",
    "hit_rate_top10",
    "crps_sum",
    "coverage_sum",
    "width_sum",
]


def direction(values):
    return np.where(np.asarray(values, dtype=np.float64) > 0, 1, -1)


def ensemble_crps(samples, observation):
    values = np.sort(np.asarray(samples, dtype=np.float64))
    if values.size == 0:
        raise ValueError("CRPS needs at least one sample")
    weights = 2.0 * np.arange(values.size) - values.size + 1.0
    pairwise = 2.0 / values.size**2 * float((values * weights).sum())
    return float(np.abs(values - observation).mean() - 0.5 * pairwise)


def interval_metrics(samples, observation, lower=INTERVAL_QUANTILES[0], upper=INTERVAL_QUANTILES[1]):
    values = np.asarray(samples, dtype=np.float64)
    low = float(np.quantile(values, lower))
    high = float(np.quantile(values, upper))
    covered = float(low <= observation <= high)
    return covered, high - low


def _require_columns(frame, columns, label):
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing columns: {missing}")


def summarize_origins(forecasts, quantiles=INTERVAL_QUANTILES):
    _require_columns(forecasts, FORECAST_COLUMNS, "Forecast frame")
    if forecasts.empty:
        raise ValueError("Forecast frame is empty")

    frame = forecasts.sort_values(
        ["fold_id", "origin_id", "horizon_step", "sample_id"], kind="mergesort"
    ).reset_index(drop=True)

    horizon = int(frame["horizon_step"].max())
    sample_ids = np.sort(frame["sample_id"].unique())
    sample_count = int(sample_ids.size)
    block = horizon * sample_count
    if len(frame) % block != 0:
        raise ValueError("Forecast frame is not a complete origin sample grid")

    origin_count = len(frame) // block
    origin_ids = frame["origin_id"].to_numpy().reshape(origin_count, block)
    if not (origin_ids == origin_ids[:, :1]).all():
        raise ValueError("Forecast frame is not a complete origin sample grid")

    steps = frame["horizon_step"].to_numpy().reshape(origin_count, horizon, sample_count)
    if not (steps == np.arange(1, horizon + 1)[None, :, None]).all():
        raise ValueError("Forecast frame is not a complete origin sample grid")
    samples = frame["sample_id"].to_numpy().reshape(origin_count, horizon, sample_count)
    if not (samples == sample_ids[None, None, :]).all():
        raise ValueError("Forecast frame is not a complete origin sample grid")

    predicted = frame["predicted_return"].to_numpy(dtype=np.float64).reshape(
        origin_count, horizon, sample_count
    )
    actual = frame["actual_return"].to_numpy(dtype=np.float64).reshape(
        origin_count, horizon, sample_count
    )
    if not np.isfinite(predicted).all() or not np.isfinite(actual).all():
        raise ValueError("Forecast frame contains non-finite returns")
    if not (actual == actual[:, :, :1]).all():
        raise ValueError("An actual return varies across samples of one origin")
    actual_steps = actual[:, :, 0]

    ordered = np.sort(predicted, axis=2)
    weights = 2.0 * np.arange(sample_count) - sample_count + 1.0
    pairwise = 2.0 / sample_count**2 * (ordered * weights[None, None, :]).sum(axis=2)
    absolute = np.abs(predicted - actual_steps[:, :, None]).mean(axis=2)
    crps = (absolute - 0.5 * pairwise).mean(axis=1)

    terminal = predicted[:, -1, :]
    actual_terminal = actual_steps[:, -1]
    low = np.quantile(terminal, quantiles[0], axis=1)
    high = np.quantile(terminal, quantiles[1], axis=1)

    keys = frame.iloc[::block].reset_index(drop=True)
    origins = pd.DataFrame(
        {
            "fold_id": keys["fold_id"],
            "origin_id": keys["origin_id"],
            "security_id": keys["security_id"],
            "origin_date": keys["origin_date"],
            "horizon": horizon,
            "sample_count": sample_count,
            "predicted_return": terminal.mean(axis=1),
            "actual_return": actual_terminal,
            "crps": crps,
            "interval_covered": (
                (actual_terminal >= low) & (actual_terminal <= high)
            ).astype(np.float64),
            "interval_width": high - low,
        },
        columns=ORIGIN_COLUMNS,
    )
    if origins["origin_id"].duplicated().any():
        raise ValueError("Duplicate origin_id in forecast frame")
    return origins.sort_values(
        ["fold_id", "origin_date", "security_id"], kind="mergesort"
    ).reset_index(drop=True)


def rank_ic(predicted, actual, tolerance=DISPERSION_TOLERANCE):
    predicted = np.asarray(predicted, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    if predicted.size < 2:
        raise ValueError("RankIC needs at least two symbols")
    if np.ptp(predicted) <= tolerance or np.ptp(actual) <= tolerance:
        return 0.0
    value = stats.spearmanr(predicted, actual).statistic
    return 0.0 if np.isnan(value) else float(value)


def hit_rate_top10(origins):
    _require_columns(origins, ["security_id", "predicted_return", "actual_return"], "Origin frame")
    if origins.duplicated(["security_id"]).any():
        raise ValueError("HitRate@Top10 needs one row per symbol on one date")
    if len(origins) < TOP_K:
        raise ValueError(f"Date has fewer than {TOP_K} eligible symbols")

    ranked = origins.sort_values(
        ["predicted_return", "security_id"],
        ascending=[False, True],
        kind="mergesort",
    )
    selected = ranked.head(TOP_K)
    return float((selected["actual_return"] > 0).sum()) / TOP_K


def aggregate_dates(origins):
    _require_columns(origins, ORIGIN_COLUMNS, "Origin frame")
    if origins.empty:
        raise ValueError("Origin frame is empty")
    if origins["horizon"].nunique() != 1 or origins["sample_count"].nunique() != 1:
        raise ValueError("Origin frame mixes horizons or sample counts")

    records = []
    for (fold_id, origin_date), group in origins.groupby(
        ["fold_id", "origin_date"], sort=True
    ):
        predicted = group["predicted_return"].to_numpy(dtype=np.float64)
        actual = group["actual_return"].to_numpy(dtype=np.float64)
        correct = direction(predicted) == direction(actual)
        magnitude = np.abs(actual)
        records.append(
            {
                "fold_id": fold_id,
                "origin_date": origin_date,
                "horizon": int(group["horizon"].iloc[0]),
                "sample_count": int(group["sample_count"].iloc[0]),
                "origin_count": len(group),
                "symbol_count": int(group["security_id"].nunique()),
                "correct_count": int(correct.sum()),
                "correct_abs_return": float(magnitude[correct].sum()),
                "total_abs_return": float(magnitude.sum()),
                "rank_ic": rank_ic(predicted, actual),
                "hit_rate_top10": (
                    hit_rate_top10(group) if len(group) >= TOP_K else np.nan
                ),
                "crps_sum": float(group["crps"].sum()),
                "coverage_sum": float(group["interval_covered"].sum()),
                "width_sum": float(group["interval_width"].sum()),
            }
        )

    return pd.DataFrame(records, columns=DATE_COLUMNS)


def summarize_metrics(dates):
    _require_columns(dates, DATE_COLUMNS, "Date frame")
    if dates.empty:
        raise ValueError("Date frame is empty")
    if dates.duplicated(["fold_id", "origin_date"]).any():
        raise ValueError("Duplicate evaluation date")

    origin_rows = int(dates["origin_count"].sum())
    total_abs_return = float(dates["total_abs_return"].sum())
    if total_abs_return == 0.0:
        raise ValueError("MW-DA is undefined without realized magnitude")

    return {
        "schema_version": SCHEMA_VERSION,
        "DA": float(dates["correct_count"].sum()) / origin_rows * 100.0,
        "MW-DA": float(dates["correct_abs_return"].sum()) / total_abs_return * 100.0,
        "RankIC": float(dates["rank_ic"].mean()),
        "HitRate@Top10": float(dates["hit_rate_top10"].mean()) * 100.0,
        "CRPS": float(dates["crps_sum"].sum()) / origin_rows,
        "coverage": float(dates["coverage_sum"].sum()) / origin_rows,
        "interval_width": float(dates["width_sum"].sum()) / origin_rows,
        "valid_dates": len(dates),
        "valid_top10_dates": int(dates["hit_rate_top10"].notna().sum()),
        "origin_rows": origin_rows,
        "min_symbols_per_date": int(dates["symbol_count"].min()),
        "max_symbols_per_date": int(dates["symbol_count"].max()),
        "horizon": int(dates["horizon"].iloc[0]),
        "sample_count": int(dates["sample_count"].iloc[0]),
    }
