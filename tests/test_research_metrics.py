import numpy as np
import pandas as pd
import pytest
from scipy import stats

from evaluation.research.metrics import (
    DATE_COLUMNS,
    FORECAST_COLUMNS,
    ORIGIN_COLUMNS,
    aggregate_dates,
    direction,
    ensemble_crps,
    hit_rate_top10,
    interval_metrics,
    rank_ic,
    summarize_metrics,
    summarize_origins,
)


HAND_CALCULATED = {
    "S00": (-0.010, 0.02),
    "S01": (0.030, 0.04),
    "S02": (0.050, 0.06),
    "S03": (0.070, 0.08),
    "S04": (0.090, 0.10),
    "S05": (0.110, 0.12),
    "S06": (0.010, -0.02),
    "S07": (-0.030, -0.04),
    "S08": (-0.050, -0.06),
    "S09": (-0.070, -0.08),
    "S10": (-0.090, -0.10),
    "S11": (0.050, -0.12),
}


def build_forecasts(paths, fold_id="eval_2022", origin_date="2022-03-01"):
    records = []
    for security_id, (samples, actual) in sorted(paths.items()):
        samples = np.asarray(samples, dtype=float)
        actual = np.asarray(actual, dtype=float)
        for sample_id in range(samples.shape[0]):
            for step in range(samples.shape[1]):
                records.append(
                    {
                        "fold_id": fold_id,
                        "origin_id": f"origin_{security_id}",
                        "security_id": security_id,
                        "origin_date": pd.Timestamp(origin_date),
                        "sample_id": sample_id,
                        "horizon_step": step + 1,
                        "predicted_return": samples[sample_id, step],
                        "actual_return": actual[step],
                    }
                )
    return pd.DataFrame(records, columns=FORECAST_COLUMNS)


def build_point_forecasts(points, **kwargs):
    paths = {
        security_id: (np.full((2, 1), predicted), np.array([actual]))
        for security_id, (predicted, actual) in points.items()
    }
    return build_forecasts(paths, **kwargs)


def test_direction_treats_zero_as_non_positive():
    assert direction(np.array([0.0, 0.1, -0.1])).tolist() == [-1, 1, -1]


def test_ensemble_crps_matches_the_two_sample_formula():
    assert ensemble_crps(np.array([0.0, 2.0]), 1.0) == pytest.approx(0.5)


def test_ensemble_crps_is_zero_for_a_perfect_deterministic_forecast():
    assert ensemble_crps(np.full(8, 0.03), 0.03) == pytest.approx(0.0)


def test_ensemble_crps_penalises_a_confidently_wrong_forecast():
    confident = ensemble_crps(np.full(8, 0.03), -0.05)
    dispersed = ensemble_crps(np.linspace(-0.05, 0.03, 8), -0.05)

    assert confident > dispersed


def test_interval_metrics_use_the_tenth_and_ninetieth_percentiles():
    samples = np.arange(10, dtype=float)

    covered, width = interval_metrics(samples, 4.5, lower=0.10, upper=0.90)

    assert covered == 1.0
    assert width == pytest.approx(np.quantile(samples, 0.90) - np.quantile(samples, 0.10))


def test_interval_metrics_report_a_miss_outside_the_band():
    covered, _ = interval_metrics(np.arange(10, dtype=float), 42.0)

    assert covered == 0.0


def test_summarize_origins_reduces_samples_to_locked_statistics():
    samples = np.array([[0.01, 0.02], [0.03, 0.06]])
    frame = build_forecasts({"S00": (samples, np.array([0.015, 0.05]))})

    origins = summarize_origins(frame)

    assert list(origins.columns) == ORIGIN_COLUMNS
    assert len(origins) == 1
    row = origins.iloc[0]
    assert row["predicted_return"] == pytest.approx(0.04)
    assert row["actual_return"] == pytest.approx(0.05)
    assert row["sample_count"] == 2
    assert row["horizon"] == 2
    expected_crps = np.mean(
        [
            ensemble_crps(samples[:, 0], 0.015),
            ensemble_crps(samples[:, 1], 0.05),
        ]
    )
    assert row["crps"] == pytest.approx(expected_crps)
    covered, width = interval_metrics(samples[:, 1], 0.05)
    assert row["interval_covered"] == pytest.approx(covered)
    assert row["interval_width"] == pytest.approx(width)


def test_summarize_origins_rejects_a_ragged_sample_grid():
    frame = build_forecasts(
        {"S00": (np.array([[0.01, 0.02], [0.03, 0.04]]), np.array([0.0, 0.0]))}
    )

    with pytest.raises(ValueError, match="sample grid"):
        summarize_origins(frame.iloc[:-1])


def test_summarize_origins_rejects_an_actual_that_varies_across_samples():
    frame = build_forecasts({"S00": (np.zeros((2, 1)), np.array([0.01]))})
    frame.loc[0, "actual_return"] = 0.99

    with pytest.raises(ValueError, match="actual return"):
        summarize_origins(frame)


def test_hit_rate_top10_requires_ten_eligible_symbols():
    origins = summarize_origins(
        build_point_forecasts(dict(list(HAND_CALCULATED.items())[:9]))
    )

    with pytest.raises(ValueError, match="fewer than 10"):
        hit_rate_top10(origins)


def test_hit_rate_top10_breaks_predicted_ties_by_security_id():
    points = {f"S{index:02d}": (0.05, 0.01) for index in range(9)}
    points["S09"] = (0.01, -1.0)
    points["S10"] = (0.01, 1.0)
    origins = summarize_origins(build_point_forecasts(points))

    assert hit_rate_top10(origins) == pytest.approx(0.9)


def test_pooled_point_metrics_match_the_hand_calculation():
    origins = summarize_origins(build_point_forecasts(HAND_CALCULATED))

    summary = summarize_metrics(aggregate_dates(origins))

    assert summary["DA"] == pytest.approx(75.0)
    assert summary["MW-DA"] == pytest.approx(68.0 / 84.0 * 100.0)
    assert summary["HitRate@Top10"] == pytest.approx(60.0)
    predicted = [value[0] for value in HAND_CALCULATED.values()]
    actual = [value[1] for value in HAND_CALCULATED.values()]
    assert summary["RankIC"] == pytest.approx(stats.spearmanr(predicted, actual).statistic)


def test_rankic_is_one_for_a_perfectly_ordered_cross_section():
    points = {
        f"S{index:02d}": (index / 100.0, index / 50.0) for index in range(12)
    }

    summary = summarize_metrics(aggregate_dates(summarize_origins(build_point_forecasts(points))))

    assert summary["RankIC"] == pytest.approx(1.0)


def test_rankic_ignores_float_noise_instead_of_ranking_it():
    noisy = np.full(12, 0.01) + np.arange(12) * 1e-18
    actual = np.linspace(-0.05, 0.05, 12)

    assert rank_ic(noisy, actual) == 0.0
    assert rank_ic(np.full(12, 0.01), actual) == 0.0


def test_pooled_rankic_stays_finite_for_a_flat_prediction_date():
    points = {f"S{index:02d}": (0.01, (index - 6) / 100.0) for index in range(12)}

    summary = summarize_metrics(
        aggregate_dates(summarize_origins(build_point_forecasts(points)))
    )

    assert summary["RankIC"] == pytest.approx(0.0)


def test_rankic_is_zero_when_every_prediction_is_identical():
    points = {f"S{index:02d}": (0.0, (index - 6) / 100.0) for index in range(12)}

    summary = summarize_metrics(aggregate_dates(summarize_origins(build_point_forecasts(points))))

    assert summary["RankIC"] == pytest.approx(0.0)


def test_aggregate_dates_keeps_locked_sufficient_statistics():
    origins = summarize_origins(build_point_forecasts(HAND_CALCULATED))

    dates = aggregate_dates(origins)

    assert list(dates.columns) == DATE_COLUMNS
    assert len(dates) == 1
    row = dates.iloc[0]
    assert row["origin_count"] == 12
    assert row["symbol_count"] == 12
    assert row["correct_count"] == 9
    assert row["correct_abs_return"] == pytest.approx(0.68)
    assert row["total_abs_return"] == pytest.approx(0.84)


def test_magnitude_weighted_da_is_a_ratio_of_sums_not_a_mean_of_ratios():
    quiet = {f"S{index:02d}": (0.01, 0.001) for index in range(12)}
    violent = {f"S{index:02d}": (0.01, -0.20) for index in range(12)}
    dates = pd.concat(
        [
            aggregate_dates(
                summarize_origins(build_point_forecasts(quiet, origin_date="2022-03-01"))
            ),
            aggregate_dates(
                summarize_origins(
                    build_point_forecasts(violent, origin_date="2022-03-02")
                )
            ),
        ],
        ignore_index=True,
    )

    summary = summarize_metrics(dates)

    assert summary["DA"] == pytest.approx(50.0)
    assert summary["MW-DA"] == pytest.approx(0.012 / 2.412 * 100.0)


def test_summary_reports_coverage_counts_and_horizon():
    origins = summarize_origins(build_point_forecasts(HAND_CALCULATED))

    summary = summarize_metrics(aggregate_dates(origins))

    assert summary["valid_dates"] == 1
    assert summary["valid_top10_dates"] == 1
    assert summary["origin_rows"] == 12
    assert summary["min_symbols_per_date"] == 12
    assert summary["max_symbols_per_date"] == 12
    assert summary["horizon"] == 1
    assert summary["sample_count"] == 2
    assert summary["CRPS"] == pytest.approx(
        origins["crps"].mean()
    )
    assert summary["coverage"] == pytest.approx(origins["interval_covered"].mean())
    assert summary["interval_width"] == pytest.approx(origins["interval_width"].mean())
