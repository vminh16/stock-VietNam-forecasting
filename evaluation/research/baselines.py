import numpy as np


BASELINE_IDS = ("persistence", "recent_return_bootstrap")
RECENT_RETURN_LOOKBACK = 63


def _observed_window(history_close):
    close = np.asarray(history_close, dtype=np.float64)
    if close.ndim != 1:
        raise ValueError("history_close must be a one-dimensional close series")
    if close.size < RECENT_RETURN_LOOKBACK:
        raise ValueError(
            f"recent_return_bootstrap needs at least {RECENT_RETURN_LOOKBACK} "
            "observed closes"
        )
    window = close[-RECENT_RETURN_LOOKBACK:]
    if not np.isfinite(window).all() or (window <= 0).any():
        raise ValueError("Observed closes must be finite and positive")
    return window


def persistence_paths(history_close, horizon, sample_count):
    _observed_window(history_close)
    if horizon < 1 or sample_count < 1:
        raise ValueError("horizon and sample_count must be positive")
    return np.zeros((sample_count, horizon), dtype=np.float64)


def recent_return_bootstrap_paths(history_close, horizon, sample_count, seed):
    window = _observed_window(history_close)
    if horizon < 1 or sample_count < 1:
        raise ValueError("horizon and sample_count must be positive")

    observed = np.diff(np.log(window))
    if observed.size < horizon:
        raise ValueError("Observed history is shorter than the forecast horizon")

    generator = np.random.default_rng(seed)
    starts = generator.integers(0, observed.size - horizon + 1, size=sample_count)
    blocks = observed[starts[:, None] + np.arange(horizon)[None, :]]
    return np.expm1(np.cumsum(blocks, axis=1))


def forecast_baselines(history_close, horizon, sample_count, seed):
    return {
        "persistence": persistence_paths(history_close, horizon, sample_count),
        "recent_return_bootstrap": recent_return_bootstrap_paths(
            history_close, horizon, sample_count, seed
        ),
    }
