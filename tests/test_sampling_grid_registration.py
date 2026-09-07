"""Pin the checkable claims of the SPEC 8.13 registration."""

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.run_zero_shot_screen import load_screen_config

CONFIGS = ROOT / "evaluation" / "configs"
CELLS = {
    "t06_p90": (0.6, 0.9),
    "t10_p90": (1.0, 0.9),
    "t06_p100": (0.6, 1.0),
    "t10_p100": (1.0, 1.0),
}
FULL_REGISTRY = CONFIGS / "m2_10_full_registry.yaml"


def _config(cell):
    return load_screen_config(CONFIGS / f"m2_11_sampling_{cell}.yaml")


def test_the_grid_is_a_full_two_by_two():
    observed = {cell: (_config(cell).temperature, _config(cell).top_p) for cell in CELLS}
    assert observed == CELLS


def test_only_the_sampler_varies_across_cells():
    fixed = {
        (
            c.sample_count,
            c.seed,
            c.top_k,
            c.horizon,
            c.max_context,
            c.clip,
            c.batch_size,
            c.date_stride,
            c.date_residues,
        )
        for c in (_config(cell) for cell in CELLS)
    }
    assert len(fixed) == 1


def test_the_grid_never_touches_the_confirmatory_dates():
    """SPEC 8.13: this study selects, so it must stay off M2.10's 683 dates."""
    confirmatory = set(load_screen_config(FULL_REGISTRY).date_residues)
    for cell in CELLS:
        selection = set(_config(cell).date_residues)
        assert selection == {0}
        assert selection.isdisjoint(confirmatory)


def test_the_undistorted_corner_applies_no_filtering():
    """model/kronos.py filters only when top_k > 0 or top_p < 1.0."""
    config = _config("t10_p100")
    assert config.top_k == 0
    assert config.top_p == 1.0


def test_every_cell_carries_its_own_identifier_and_report():
    arm_ids, report_dirs = set(), set()
    for cell in CELLS:
        config = _config(cell)
        assert len(config.arms) == 1
        assert config.arms[0].arm_id == f"small_l126_{cell}"
        arm_ids.add(config.arms[0].arm_id)
        report_dirs.add(str(config.report_dir))
    assert len(arm_ids) == len(CELLS)
    assert len(report_dirs) == len(CELLS)


def test_the_incumbent_corner_matches_the_registered_sampler():
    """t06_p90 reproduces the setting every earlier run used."""
    incumbent = _config("t06_p90")
    registered = load_screen_config(FULL_REGISTRY)
    assert (incumbent.temperature, incumbent.top_p, incumbent.top_k) == (
        registered.temperature,
        registered.top_p,
        registered.top_k,
    )
    assert incumbent.sample_count == registered.sample_count
