import numpy as np
import pandas as pd
import pytest

from evaluation.research.bootstrap import (
    COMPARISON_COLUMNS,
    POOLED_METRICS,
    compare_candidates,
    pooled_metric,
    stationary_block_indices,
)
from evaluation.research.metrics import DATE_COLUMNS


def build_dates(values, fold_id="eval_2022", start="2022-01-03"):
    sessions = pd.bdate_range(start, periods=len(values))
    records = []
    for session, value in zip(sessions, values):
        record = {
            "fold_id": fold_id,
            "origin_date": session,
            "horizon": 5,
            "sample_count": 20,
            "origin_count": 100,
            "symbol_count": 100,
            "correct_count": 50,
            "correct_abs_return": 1.0,
            "total_abs_return": 2.0,
            "rank_ic": 0.0,
            "hit_rate_top10": 0.5,
            "crps_sum": 1.0,
            "coverage_sum": 80.0,
            "width_sum": 10.0,
        }
        record.update(value)
        records.append(record)
    return pd.DataFrame(records, columns=DATE_COLUMNS)


def test_stationary_indices_are_reproducible_and_inside_the_series():
    first = stationary_block_indices(50, mean_block=10, replicates=200, seed=7)
    second = stationary_block_indices(50, mean_block=10, replicates=200, seed=7)
    other = stationary_block_indices(50, mean_block=10, replicates=200, seed=8)

    assert first.shape == (200, 50)
    np.testing.assert_array_equal(first, second)
    assert not np.array_equal(first, other)
    assert first.min() >= 0 and first.max() < 50


def test_stationary_blocks_are_contiguous_with_the_registered_mean_length():
    indices = stationary_block_indices(400, mean_block=10, replicates=400, seed=11)

    steps = (indices[:, 1:] - indices[:, :-1]) % 400
    continued = float((steps == 1).mean())

    assert continued == pytest.approx(0.9, abs=0.02)


def test_pooled_metrics_are_ratios_of_sums_not_means_of_ratios():
    dates = build_dates(
        [
            {"correct_abs_return": 0.01, "total_abs_return": 0.01},
            {"correct_abs_return": 0.00, "total_abs_return": 2.40},
        ]
    )

    assert pooled_metric(dates, "MW-DA") == pytest.approx(0.01 / 2.41 * 100.0)
    assert pooled_metric(dates, "DA") == pytest.approx(50.0)


def test_pooled_date_metrics_average_over_dates():
    dates = build_dates([{"rank_ic": 0.2}, {"rank_ic": -0.4}, {"rank_ic": 0.5}])

    assert pooled_metric(dates, "RankIC") == pytest.approx(0.1)
    assert pooled_metric(dates, "HitRate@Top10") == pytest.approx(50.0)


def test_comparison_reports_every_locked_metric_with_paired_intervals():
    left = build_dates([{"rank_ic": 0.01 * index} for index in range(40)])
    right = build_dates([{"rank_ic": 0.01 * index - 0.02} for index in range(40)])

    comparison = compare_candidates(left, right, "left", "right", replicates=200, seed=7)

    assert list(comparison.columns) == COMPARISON_COLUMNS
    assert list(comparison["metric"]) == list(POOLED_METRICS)
    row = comparison.set_index("metric").loc["RankIC"]
    assert row["left_estimate"] - row["right_estimate"] == pytest.approx(0.02)
    assert row["difference"] == pytest.approx(0.02)
    assert row["ci_low"] <= row["difference"] <= row["ci_high"]
    assert row["n_paired_dates"] == 40


def test_comparing_a_candidate_with_itself_gives_a_zero_width_interval():
    dates = build_dates([{"rank_ic": 0.01 * index} for index in range(30)])

    comparison = compare_candidates(dates, dates, "left", "right", replicates=100, seed=7)

    assert (comparison["difference"] == 0.0).all()
    assert (comparison["ci_low"] == 0.0).all()
    assert (comparison["ci_high"] == 0.0).all()


def test_comparison_is_reproducible_for_a_seed():
    left = build_dates([{"rank_ic": 0.01 * index} for index in range(30)])
    right = build_dates([{"rank_ic": -0.01 * index} for index in range(30)])

    first = compare_candidates(left, right, "left", "right", replicates=200, seed=7)
    second = compare_candidates(left, right, "left", "right", replicates=200, seed=7)

    pd.testing.assert_frame_equal(first, second)


def test_comparison_rejects_nonmatching_dates():
    left = build_dates([{"rank_ic": 0.0} for _ in range(30)])
    right = build_dates([{"rank_ic": 0.0} for _ in range(29)])

    with pytest.raises(ValueError, match="date sets differ"):
        compare_candidates(left, right, "left", "right", replicates=50, seed=7)


def test_comparison_rejects_nonmatching_origin_counts():
    left = build_dates([{"rank_ic": 0.0} for _ in range(30)])
    right = build_dates([{"rank_ic": 0.0} for _ in range(30)])
    right.loc[3, "origin_count"] = 99

    with pytest.raises(ValueError, match="origin counts differ"):
        compare_candidates(left, right, "left", "right", replicates=50, seed=7)


def test_interval_widens_when_the_paired_difference_is_noisy():
    generator = np.random.default_rng(3)
    stable = build_dates([{"rank_ic": 0.10} for _ in range(60)])
    noisy_left = build_dates(
        [{"rank_ic": float(value)} for value in generator.normal(0.10, 0.30, 60)]
    )
    flat = build_dates([{"rank_ic": 0.0} for _ in range(60)])

    tight = compare_candidates(stable, flat, "a", "b", replicates=400, seed=5)
    wide = compare_candidates(noisy_left, flat, "a", "b", replicates=400, seed=5)

    tight_row = tight.set_index("metric").loc["RankIC"]
    wide_row = wide.set_index("metric").loc["RankIC"]

    assert tight_row["ci_high"] - tight_row["ci_low"] == pytest.approx(0.0, abs=1e-12)
    assert wide_row["ci_high"] - wide_row["ci_low"] > 0.05


def test_comparison_records_an_inconclusive_verdict_when_zero_is_inside():
    generator = np.random.default_rng(17)
    noise = generator.normal(0.0, 0.2, 80)
    noise -= noise.mean()
    left = build_dates([{"rank_ic": float(value)} for value in noise])
    right = build_dates([{"rank_ic": 0.0} for _ in range(80)])

    comparison = compare_candidates(left, right, "left", "right", replicates=400, seed=7)
    row = comparison.set_index("metric").loc["RankIC"]

    assert row["ci_low"] < 0.0 < row["ci_high"]
    assert row["verdict"] == "insufficient evidence"
