import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.run_zero_shot_screen import load_screen_config, select_dates

SCREEN_CONFIG = ROOT / "evaluation" / "configs" / "m2_5_zero_shot_screen.yaml"


def test_default_residue_reproduces_the_m2_5_screen_selection():
    dates = np.arange(977)
    assert np.array_equal(select_dates(dates, 10, [0]), dates[::10])
    assert select_dates(dates, 10, [0]).size == 98


def test_confirmation_residues_are_disjoint_from_the_screen():
    dates = np.arange(977)
    screen = set(select_dates(dates, 10, [0]).tolist())
    confirmation = set(select_dates(dates, 10, [2, 5]).tolist())
    assert len(confirmation) == 196
    assert screen.isdisjoint(confirmation)


def test_selected_dates_keep_their_chronological_order():
    dates = np.arange(100) * 3
    selected = select_dates(dates, 10, [5, 2])
    assert selected.tolist() == sorted(selected.tolist())


def test_empty_selection_is_refused():
    with pytest.raises(ValueError, match="Date selection is empty"):
        select_dates(np.arange(3), 10, [7])


def _config_with(tmp_path, **overrides):
    raw = yaml.safe_load(SCREEN_CONFIG.read_text(encoding="utf-8"))
    raw.update(overrides)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


def test_config_defaults_to_the_screen_residue(tmp_path):
    config = load_screen_config(_config_with(tmp_path))
    assert config.date_residues == (0,)


def test_config_accepts_registered_residues(tmp_path):
    config = load_screen_config(_config_with(tmp_path, date_residues=[2, 5]))
    assert config.date_residues == (2, 5)


@pytest.mark.parametrize("residues", [[], [2, 2], [10], [-1]])
def test_config_refuses_an_invalid_residue_set(tmp_path, residues):
    with pytest.raises(ValueError):
        load_screen_config(_config_with(tmp_path, date_residues=residues))
