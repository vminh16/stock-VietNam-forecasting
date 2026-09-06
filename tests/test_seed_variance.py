import itertools
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.run_seed_variance import (
    SIGMA_DATE,
    TOLERATED_RATIO,
    load_replicates,
    read_decision,
    spread,
)
from evaluation.run_zero_shot_screen import _origin_seed, select_arms

VARIANCE_CONFIG = ROOT / "evaluation" / "configs" / "m2_9_seed_variance.yaml"
PAIRED_CONFIG = ROOT / "evaluation" / "configs" / "m2_9_paired_inference.yaml"
CONFIRMATION_CONFIG = ROOT / "evaluation" / "configs" / "m2_7_confirmation.yaml"


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_replicates_differ_in_nothing_but_their_identifier():
    arms = _load(VARIANCE_CONFIG)["arms"]
    assert len(arms) == 5
    shapes = {
        (arm["model_path"], arm["lookback"], arm["normalizer_lookback"]) for arm in arms
    }
    assert shapes == {("pretrained/Kronos-small", 126, 126)}
    assert len({arm["arm_id"] for arm in arms}) == 5


def test_replicates_reuse_the_confirmation_dates_and_sampling():
    variance = _load(VARIANCE_CONFIG)
    confirmation = _load(CONFIRMATION_CONFIG)
    assert variance["date_stride"] == confirmation["date_stride"]
    assert variance["date_residues"] == confirmation["date_residues"]
    assert variance["sampling"] == confirmation["sampling"]
    assert variance["horizon"] == confirmation["horizon"]
    assert variance["runtime"] == confirmation["runtime"]


def test_identifier_alone_moves_the_rng_stream():
    """The whole design rests on this: same seed and date, different stream."""
    arm_ids = [arm["arm_id"] for arm in _load(VARIANCE_CONFIG)["arms"]]
    seeds = {_origin_seed(20260901, arm_id, "2024-03-15") for arm_id in arm_ids}
    assert len(seeds) == len(arm_ids)


def test_an_identifier_keeps_its_stream_across_calls():
    first = _origin_seed(20260901, "small_l126_r1", "2024-03-15")
    second = _origin_seed(20260901, "small_l126_r1", "2024-03-15")
    assert first == second
    assert first != _origin_seed(20260901, "small_l126_r1", "2024-03-18")


def test_paired_config_covers_every_unordered_replicate_pair():
    arm_ids = [arm["arm_id"] for arm in _load(VARIANCE_CONFIG)["arms"]]
    comparisons = _load(PAIRED_CONFIG)["comparisons"]
    pairs = {frozenset((row["left"], row["right"])) for row in comparisons}
    assert len(comparisons) == 10
    assert len(pairs) == 10
    assert pairs == {frozenset(pair) for pair in itertools.combinations(arm_ids, 2)}
    assert all(row["left"] != row["right"] for row in comparisons)


def test_decision_threshold_matches_the_registered_rule():
    threshold = TOLERATED_RATIO * SIGMA_DATE
    assert threshold == pytest.approx(0.00376, abs=5e-6)

    quiet = read_decision(threshold * 0.5)
    assert not quiet["material"]
    assert quiet["rule"] == "8.11.4"
    assert quiet["interval_inflation_factor"] < 1.01

    loud = read_decision(threshold * 4.0)
    assert loud["material"]
    assert loud["rule"] == "8.11.5"
    assert loud["interval_inflation_factor"] > 1.4


def test_a_sd_exactly_on_the_threshold_is_not_material():
    """Rule 4 reads `<=`, so the boundary passes rather than fails."""
    assert not read_decision(TOLERATED_RATIO * SIGMA_DATE)["material"]


def test_spread_uses_the_sample_standard_deviation():
    summaries = {f"r{index}": {"RankIC": value} for index, value in enumerate([1.0, 2.0, 3.0])}
    result = spread(summaries, list(summaries), "RankIC")
    assert result["sd"] == pytest.approx(1.0)
    assert result["mean"] == pytest.approx(2.0)
    assert result["range"] == pytest.approx(2.0)


def test_missing_replicate_is_named_rather_than_silently_skipped(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "output_dir": "data/evaluation/does_not_exist",
                "report_dir": "reports/does_not_exist",
                "arms": [{"arm_id": f"r{index}"} for index in range(3)],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError, match="r0_per_date_metrics"):
        load_replicates(config)


def test_two_replicates_are_refused(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "output_dir": "data/evaluation/m2_9",
                "report_dir": "reports/x",
                "arms": [{"arm_id": "r0"}, {"arm_id": "r1"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="fewer than 3"):
        load_replicates(config)


# The five replicates are independent, so they can be split across processes.
# These guard the one property that makes that safe.


def test_a_filtered_arm_lands_on_the_same_cache_key_as_a_full_run():
    from evaluation.run_zero_shot_screen import arm_cache_key, load_screen_config

    config = load_screen_config(VARIANCE_CONFIG)
    subset = select_arms(config, ["small_l126_r3"])
    full = {arm.arm_id: arm_cache_key(config, arm, "reg", "sel") for arm in config.arms}
    assert arm_cache_key(subset, subset.arms[0], "reg", "sel") == full["small_l126_r3"]
    assert len(set(full.values())) == 5


def test_select_arms_keeps_the_requested_order_without_repeats():
    from evaluation.run_zero_shot_screen import load_screen_config

    config = load_screen_config(VARIANCE_CONFIG)
    subset = select_arms(config, ["small_l126_r4", "small_l126_r1", "small_l126_r4"])
    assert [arm.arm_id for arm in subset.arms] == ["small_l126_r4", "small_l126_r1"]


def test_select_arms_names_an_unknown_arm():
    from evaluation.run_zero_shot_screen import load_screen_config

    config = load_screen_config(VARIANCE_CONFIG)
    with pytest.raises(ValueError, match="small_l126_r9"):
        select_arms(config, ["small_l126_r9"])
