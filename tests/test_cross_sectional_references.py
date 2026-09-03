import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.research.cross_sectional import (
    CROSS_SECTIONAL_IDS,
    MOMENTUM_FORMATION,
    MOMENTUM_SKIP,
    REVERSAL_LOOKBACK,
    REQUIRED_HISTORY,
    forecast_cross_sectional,
    momentum_signal,
    reversal_signal,
    signal_paths,
)

HORIZON = 5


def _history(values):
    return np.asarray(values, dtype=np.float64)


def _ramp(length, step=1.0, start=100.0):
    return _history(start + step * np.arange(length))


def test_reversal_signal_flips_the_sign_of_the_recent_move():
    close = _history([100.0, 101.0, 102.0, 103.0, 104.0, 110.0])
    # The window is the last REVERSAL_LOOKBACK returns: 110 / 100 - 1 = +0.10.
    assert reversal_signal(close) == pytest.approx(-0.10)


def test_reversal_signal_reads_only_the_last_six_closes():
    close = _history([1.0, 2.0, 3.0] + [100.0, 101.0, 102.0, 103.0, 104.0, 110.0])
    assert reversal_signal(close) == pytest.approx(-0.10)


def test_momentum_signal_skips_the_most_recent_month():
    close = _ramp(REQUIRED_HISTORY)
    formation = close[-1 - MOMENTUM_SKIP] / close[-MOMENTUM_FORMATION] - 1.0
    scale = HORIZON / (MOMENTUM_FORMATION - 1 - MOMENTUM_SKIP)
    assert momentum_signal(close, HORIZON) == pytest.approx(formation * scale)


def test_momentum_signal_ignores_the_skipped_window():
    close = _ramp(REQUIRED_HISTORY)
    quiet = momentum_signal(close, HORIZON)
    spiked = close.copy()
    spiked[-MOMENTUM_SKIP:] *= 3.0
    assert momentum_signal(spiked, HORIZON) == pytest.approx(quiet)


def test_signals_refuse_a_short_history():
    for signal in (reversal_signal,):
        with pytest.raises(ValueError):
            signal(_history([100.0, 101.0]))
    with pytest.raises(ValueError):
        momentum_signal(_ramp(REQUIRED_HISTORY - 1), HORIZON)


def test_signal_paths_reach_the_signal_at_the_final_step():
    paths = signal_paths(0.02, horizon=HORIZON, sample_count=4)
    assert paths.shape == (4, HORIZON)
    assert paths[:, -1] == pytest.approx(0.02)
    # Every sample is identical: these are point forecasts, not distributions.
    assert np.ptp(paths, axis=0) == pytest.approx(np.zeros(HORIZON))
    # Steps increase monotonically toward the signal.
    assert np.all(np.diff(paths[0]) > 0)


def test_signal_paths_handle_a_negative_signal():
    paths = signal_paths(-0.03, horizon=HORIZON, sample_count=2)
    assert paths[:, -1] == pytest.approx(-0.03)
    assert np.all(np.diff(paths[0]) < 0)


def test_forecast_cross_sectional_returns_every_registered_candidate():
    close = _ramp(REQUIRED_HISTORY)
    paths = forecast_cross_sectional(close, horizon=HORIZON, sample_count=3)
    assert set(paths) == set(CROSS_SECTIONAL_IDS)
    for values in paths.values():
        assert values.shape == (3, HORIZON)
        assert np.isfinite(values).all()


def test_forecast_cross_sectional_never_reads_beyond_the_origin():
    close = _ramp(REQUIRED_HISTORY + 10)
    truncated = close[: REQUIRED_HISTORY]
    full = forecast_cross_sectional(truncated, horizon=HORIZON, sample_count=2)
    # Appending future sessions must not change a forecast made at the origin.
    assert set(full) == set(CROSS_SECTIONAL_IDS)
    for candidate, values in full.items():
        assert values == pytest.approx(
            forecast_cross_sectional(truncated, horizon=HORIZON, sample_count=2)[candidate]
        )


def test_required_history_fits_the_registered_l126_window():
    assert REQUIRED_HISTORY <= 126
    assert REVERSAL_LOOKBACK < REQUIRED_HISTORY
