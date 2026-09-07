"""What the locked interval metric can reach when the model is perfect.

`INTERVAL_QUANTILES = (0.10, 0.90)` is read with `np.quantile` over the sample
axis, and every run so far has drawn 10 samples. Ten draws do not resolve a 10th
and 90th percentile, so the interval is narrower than the distribution it comes
from and a perfectly calibrated sampler cannot cover 0.80 of outcomes.

These tests measure that ceiling, so the reported coverage of a real arm is read
against what the measurement can deliver rather than against the nominal level.
They test the metric definition, not project code, which is why the simulation
lives here.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.research.metrics import INTERVAL_QUANTILES

TRIALS = 60000
SEED = 20260901


def empirical_coverage(draw, sample_count, trials=TRIALS):
    """Coverage of a fresh draw by the sample interval of `sample_count` draws."""
    samples = draw((trials, sample_count))
    observed = draw(trials)
    low = np.quantile(samples, INTERVAL_QUANTILES[0], axis=1)
    high = np.quantile(samples, INTERVAL_QUANTILES[1], axis=1)
    return float(((observed >= low) & (observed <= high)).mean())


def test_ten_samples_cannot_reach_the_nominal_level():
    rng = np.random.default_rng(SEED)
    coverage = empirical_coverage(rng.standard_normal, 10)
    assert coverage == pytest.approx(0.66, abs=0.02)
    assert coverage < 0.70


def test_the_ceiling_rises_with_the_sample_count():
    rng = np.random.default_rng(SEED)
    ceilings = [empirical_coverage(rng.standard_normal, n) for n in (10, 20, 50)]
    assert ceilings == sorted(ceilings)
    assert ceilings[1] == pytest.approx(0.73, abs=0.02)
    assert ceilings[2] == pytest.approx(0.77, abs=0.02)


@pytest.mark.parametrize(
    "name",
    ["normal", "t3", "laplace", "lognormal", "uniform"],
)
def test_the_ceiling_barely_depends_on_the_shape(name):
    """A heavy tail or a skew moves it by less than two points."""
    rng = np.random.default_rng(SEED)
    draws = {
        "normal": rng.standard_normal,
        "t3": lambda shape: rng.standard_t(3, shape),
        "laplace": lambda shape: rng.laplace(0.0, 1.0, shape),
        "lognormal": lambda shape: rng.lognormal(0.0, 0.5, shape),
        "uniform": lambda shape: rng.uniform(-1.0, 1.0, shape),
    }
    assert empirical_coverage(draws[name], 10) == pytest.approx(0.66, abs=0.02)


def test_the_measured_arms_sit_well_below_the_ceiling():
    """The M2.10 numbers are a model deficit, not only an estimator artifact."""
    rng = np.random.default_rng(SEED)
    ceiling = empirical_coverage(rng.standard_normal, 10)
    small_l126, base_l126 = 0.392687, 0.352628
    assert small_l126 < ceiling - 0.20
    assert base_l126 < small_l126
    # And the naive reference sits at the ceiling rather than below it.
    assert 0.689 > ceiling
