import numpy as np
import pytest

from evaluation.research.diagnostics import (
    clip_rate,
    normalization_variants,
    variance_ratio,
)


def test_random_walk_has_a_variance_ratio_near_one():
    generator = np.random.default_rng(2026)
    returns = generator.normal(0.0, 0.02, 20000)

    for q in (2, 5, 10):
        ratio, z_star = variance_ratio(returns, q)
        assert ratio == pytest.approx(1.0, abs=0.05)
        assert abs(z_star) < 3.0


def test_mean_reverting_series_has_a_variance_ratio_below_one():
    generator = np.random.default_rng(7)
    shocks = generator.normal(0.0, 0.02, 20001)
    returns = shocks[1:] - 0.6 * shocks[:-1]

    ratio, z_star = variance_ratio(returns, 5)

    assert ratio < 0.8
    assert z_star < -3.0


def test_trending_series_has_a_variance_ratio_above_one():
    generator = np.random.default_rng(11)
    shocks = generator.normal(0.0, 0.02, 20001)
    returns = shocks[1:] + 0.6 * shocks[:-1]

    ratio, z_star = variance_ratio(returns, 5)

    assert ratio > 1.2
    assert z_star > 3.0


def test_variance_ratio_rejects_short_or_degenerate_input():
    generator = np.random.default_rng(3)

    with pytest.raises(ValueError, match="too short"):
        variance_ratio(generator.normal(size=20), 5)
    with pytest.raises(ValueError, match="at least two"):
        variance_ratio(generator.normal(size=200), 1)
    with pytest.raises(ValueError, match="no variance"):
        variance_ratio(np.zeros(200), 5)


def test_normalization_variants_agree_when_both_windows_share_moments():
    generator = np.random.default_rng(5)
    window = generator.normal(10.0, 1.0, size=(126, 6))

    variants = normalization_variants(window, short_lookback=63)

    assert variants["short"].shape == (63, 6)
    assert variants["long"].shape == (126, 6)
    np.testing.assert_allclose(variants["scale_ratio"], 1.0, atol=0.35)
    np.testing.assert_allclose(
        variants["short"], variants["short_scaled_by_long"], atol=0.5
    )


def test_normalization_variants_separate_the_scale_change_from_the_rows():
    window = np.zeros((126, 1))
    window[:63, 0] = np.linspace(0.0, 100.0, 63)
    window[63:, 0] = np.linspace(100.0, 101.0, 63)

    variants = normalization_variants(window, short_lookback=63)

    assert variants["scale_ratio"][0] < 0.05
    assert variants["mean_shift"][0] > 0.5
    assert not np.allclose(variants["short"], variants["short_scaled_by_long"])


def test_clip_rate_counts_values_outside_the_normalized_band():
    window = np.zeros((126, 1))
    window[:126, 0] = np.random.default_rng(1).normal(0.0, 1.0, 126)

    assert clip_rate(window, 126) == pytest.approx(0.0, abs=0.02)

    spiked = window.copy()
    spiked[-1, 0] = 500.0
    assert clip_rate(spiked, 63) > 0.0
