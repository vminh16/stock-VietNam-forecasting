import inspect

import numpy as np
import pytest

from evaluation.research.baselines import (
    BASELINE_IDS,
    RECENT_RETURN_LOOKBACK,
    forecast_baselines,
    persistence_paths,
    recent_return_bootstrap_paths,
)


@pytest.fixture
def history_close():
    generator = np.random.default_rng(20260901)
    steps = generator.normal(loc=0.0005, scale=0.02, size=200)
    return 30.0 * np.exp(np.cumsum(steps))


def test_persistence_predicts_zero_cumulative_return_for_every_path(history_close):
    paths = persistence_paths(history_close, horizon=5, sample_count=20)

    assert paths.shape == (20, 5)
    np.testing.assert_array_equal(paths, np.zeros((20, 5)))


def test_recent_bootstrap_is_reproducible_for_a_given_seed(history_close):
    first = recent_return_bootstrap_paths(history_close, 5, 20, seed=17)
    second = recent_return_bootstrap_paths(history_close, 5, 20, seed=17)
    other = recent_return_bootstrap_paths(history_close, 5, 20, seed=18)

    assert first.shape == (20, 5)
    np.testing.assert_array_equal(first, second)
    assert not np.array_equal(first, other)


def test_recent_bootstrap_reads_only_the_trailing_lookback(history_close):
    tampered = history_close.copy()
    tampered[:-RECENT_RETURN_LOOKBACK] *= 100.0

    baseline = recent_return_bootstrap_paths(history_close, 5, 20, seed=17)
    changed = recent_return_bootstrap_paths(tampered, 5, 20, seed=17)

    np.testing.assert_array_equal(baseline, changed)


def test_recent_bootstrap_samples_contiguous_blocks_of_observed_returns(history_close):
    paths = recent_return_bootstrap_paths(history_close, 5, 20, seed=17)

    window = history_close[-RECENT_RETURN_LOOKBACK:]
    observed = np.diff(np.log(window))
    blocks = np.array(
        [observed[start : start + 5] for start in range(len(observed) - 4)]
    )
    expected_paths = np.expm1(np.cumsum(blocks, axis=1))

    for path in paths:
        assert np.isclose(path, expected_paths).all(axis=1).any()


def test_recent_bootstrap_rejects_history_shorter_than_the_lookback(history_close):
    with pytest.raises(ValueError, match="63 observed closes"):
        recent_return_bootstrap_paths(history_close[-62:], 5, 20, seed=17)


def test_forecast_baselines_returns_both_causal_references(history_close):
    paths = forecast_baselines(history_close, horizon=5, sample_count=20, seed=17)

    assert tuple(paths) == BASELINE_IDS == ("persistence", "recent_return_bootstrap")
    assert all(value.shape == (20, 5) for value in paths.values())
    np.testing.assert_array_equal(
        paths["recent_return_bootstrap"],
        recent_return_bootstrap_paths(history_close, 5, 20, seed=17),
    )


def test_baseline_signatures_cannot_accept_future_observations():
    for function in (persistence_paths, recent_return_bootstrap_paths, forecast_baselines):
        parameters = set(inspect.signature(function).parameters)
        assert not {"future", "future_close", "target", "actual"} & parameters
