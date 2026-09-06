"""Pin the checkable claims of the SPEC 8.12 registration.

The registration says the run is prospective because its dates are the exact
complement of every date an earlier Kronos run has seen. That is a fact about
the configs, so it is tested rather than asserted.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.run_zero_shot_screen import load_screen_config, select_dates

CONFIGS = ROOT / "evaluation" / "configs"
FULL = CONFIGS / "m2_10_full_registry.yaml"
PAIRED = CONFIGS / "m2_10_paired_inference.yaml"
SCREEN = CONFIGS / "m2_5_zero_shot_screen.yaml"
CONFIRMATION = CONFIGS / "m2_7_confirmation.yaml"
REGISTRY = ROOT / "data" / "evaluation" / "m2_1" / "common_origins.csv.gz"


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registry_dates():
    frame = pd.read_csv(REGISTRY, usecols=["origin_date"])
    return np.sort(pd.to_datetime(frame["origin_date"]).unique())


def test_the_three_runs_partition_the_registry(registry_dates):
    # m2_5 predates the date_residues field and relies on the loader's default,
    # so the residues come from the loaded config rather than the raw YAML.
    screen = select_dates(registry_dates, 10, load_screen_config(SCREEN).date_residues)
    confirmation = select_dates(
        registry_dates, 10, load_screen_config(CONFIRMATION).date_residues
    )
    primary = select_dates(registry_dates, 10, load_screen_config(FULL).date_residues)

    assert (screen.size, confirmation.size, primary.size) == (98, 196, 683)
    assert screen.size + confirmation.size + primary.size == registry_dates.size
    assert set(primary).isdisjoint(screen)
    assert set(primary).isdisjoint(confirmation)
    assert set(primary) | set(screen) | set(confirmation) == set(registry_dates)


def test_the_run_is_sized_as_registered(registry_dates):
    frame = pd.read_csv(REGISTRY, usecols=["origin_date", "fold_id"])
    frame["origin_date"] = pd.to_datetime(frame["origin_date"])
    primary = select_dates(registry_dates, 10, _load(FULL)["date_residues"])
    selected = frame[frame["origin_date"].isin(primary)]
    assert len(selected) == 93637
    assert sorted(selected["fold_id"].unique()) == [
        "eval_2022",
        "eval_2023",
        "eval_2024",
        "eval_2025",
    ]


def test_only_the_two_confirmed_arms_run():
    arms = _load(FULL)["arms"]
    assert [arm["arm_id"] for arm in arms] == ["small_l126", "base_l126"]
    assert {(arm["lookback"], arm["normalizer_lookback"]) for arm in arms} == {(126, 126)}


def test_the_sampler_is_unchanged_from_the_earlier_runs():
    """A difference against M2.7 or M2.9 must not be attributable to sampling."""
    full = _load(FULL)
    confirmation = _load(CONFIRMATION)
    assert full["sampling"] == confirmation["sampling"]
    assert full["runtime"] == confirmation["runtime"]
    assert full["horizon"] == confirmation["horizon"]
    assert full["date_stride"] == confirmation["date_stride"]


def test_the_primary_family_is_registered():
    pairs = {
        (row["left"], row["right"]) for row in _load(PAIRED)["comparisons"]
    }
    primary = {
        ("small_l126", "short_term_reversal"),
        ("base_l126", "short_term_reversal"),
        ("small_l126", "recent_return_bootstrap"),
        ("base_l126", "recent_return_bootstrap"),
        ("small_l126", "base_l126"),
    }
    assert primary <= pairs
    assert _load(PAIRED)["restrict_dates_to"] == "small_l126"
    assert _load(PAIRED)["bootstrap"]["replicates"] >= 1000


def test_the_reference_inputs_are_reachable():
    directories = _load(PAIRED)["input_dirs"]
    assert "data/evaluation/m2_2" in directories
    assert "data/evaluation/m2_8" in directories
    assert "data/evaluation/m2_10" in directories
