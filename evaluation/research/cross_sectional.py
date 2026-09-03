import numpy as np


# Locked M2.8 conventions:
# - These are cross-sectional reference signals: unlike `persistence` and
#   `recent_return_bootstrap`, they carry real ranking information, so they test
#   whether a model beats a cheap known effect rather than only beating noise.
# - Both read closes up to the forecast origin and nothing after it.
# - Both are deterministic. They take no seed, so a paired comparison against
#   them carries no Monte Carlo noise from this side.
# - Both emit point forecasts replicated across samples. CRPS, interval
#   coverage, and interval width are therefore meaningless for them and MUST NOT
#   be read as a probabilistic comparison. RankIC, HitRate@Top10, DA, and MW-DA
#   are the metrics these references exist to contest.
# - Formation returns are rescaled to the forecast horizon by simple proportion.
#   That is unit conversion, not calibration: no coefficient is fitted, and
#   RankIC is invariant to it because the rescaling is a positive constant.
SCHEMA_VERSION = "m2_8_cross_sectional_v1"

CROSS_SECTIONAL_IDS = ("short_term_reversal", "momentum_126_21")

# Short-term reversal over one trading week, the horizon this project forecasts.
REVERSAL_LOOKBACK = 5

# Six-month formation skipping the most recent month, one of the formation
# periods in the original momentum study.
MOMENTUM_FORMATION = 126
MOMENTUM_SKIP = 21

REQUIRED_HISTORY = MOMENTUM_FORMATION


def _window(history_close, length):
    close = np.asarray(history_close, dtype=np.float64)
    if close.size < length:
        raise ValueError(f"Signal needs {length} closes, received {close.size}")
    window = close[-length:]
    if not np.isfinite(window).all() or (window <= 0).any():
        raise ValueError("Signal window contains a non-positive or non-finite close")
    return window


def reversal_signal(history_close):
    """Negative of the trailing five-session return."""
    window = _window(history_close, REVERSAL_LOOKBACK + 1)
    return float(-(window[-1] / window[0] - 1.0))


def momentum_signal(history_close, horizon):
    """Six-month formation return skipping the last month, scaled to the horizon."""
    window = _window(history_close, MOMENTUM_FORMATION)
    formation = float(window[-1 - MOMENTUM_SKIP] / window[0] - 1.0)
    sessions = MOMENTUM_FORMATION - 1 - MOMENTUM_SKIP
    return formation * horizon / sessions


def signal_paths(signal, horizon, sample_count):
    """Spread one point forecast linearly over the horizon, identical per sample."""
    if horizon < 1 or sample_count < 1:
        raise ValueError("horizon and sample_count must be positive")
    steps = np.arange(1, horizon + 1, dtype=np.float64) / horizon
    return np.tile(signal * steps, (sample_count, 1))


def forecast_cross_sectional(history_close, horizon, sample_count):
    """Return one point-forecast path set per cross-sectional reference."""
    return {
        "short_term_reversal": signal_paths(
            reversal_signal(history_close), horizon, sample_count
        ),
        "momentum_126_21": signal_paths(
            momentum_signal(history_close, horizon), horizon, sample_count
        ),
    }
