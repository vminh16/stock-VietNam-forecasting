import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.research.slices import (
    SLICE_KEYS,
    assign_symbol_groups,
    liquidity_tiers,
    trailing_liquidity,
)


def _frame(values, dates=("2022-01-03",)):
    records = []
    for origin_date in dates:
        for security_id, value in values.items():
            records.append(
                {
                    "fold_id": "fold_2022",
                    "origin_date": pd.Timestamp(origin_date),
                    "security_id": security_id,
                    "liquidity_value": float(value),
                }
            )
    return pd.DataFrame(records)


def test_symbol_groups_are_deterministic_and_salt_dependent():
    ids = [f"HOSE_S{index:03d}" for index in range(40)]
    first = assign_symbol_groups(ids, group_count=4, salt="m2")
    assert first == assign_symbol_groups(ids, group_count=4, salt="m2")
    assert first != assign_symbol_groups(ids, group_count=4, salt="m3")


def test_symbol_groups_do_not_depend_on_input_order_or_repetition():
    ids = [f"HOSE_S{index:03d}" for index in range(30)]
    shuffled = list(reversed(ids)) + ids
    assert assign_symbol_groups(ids, 3, "m2") == assign_symbol_groups(shuffled, 3, "m2")


def test_symbol_groups_cover_every_symbol_exactly_once():
    ids = [f"HOSE_S{index:03d}" for index in range(50)]
    groups = assign_symbol_groups(ids, group_count=5, salt="m2")
    assert set(groups) == set(ids)
    assert set(groups.values()) <= {f"group_{index}" for index in range(5)}


def test_symbol_groups_reject_a_degenerate_split():
    with pytest.raises(ValueError):
        assign_symbol_groups(["HOSE_A", "HOSE_B"], group_count=1, salt="m2")


def test_trailing_liquidity_reads_only_history_up_to_the_origin():
    values = np.arange(20, dtype=np.float64)
    assert trailing_liquidity(values, row_origin=9, lookback=5) == 7.0
    # A future spike must not move the value.
    spiked = values.copy()
    spiked[10:] = 1e9
    assert trailing_liquidity(spiked, row_origin=9, lookback=5) == 7.0


def test_trailing_liquidity_refuses_an_incomplete_window():
    values = np.arange(5, dtype=np.float64)
    with pytest.raises(ValueError):
        trailing_liquidity(values, row_origin=2, lookback=5)


def test_trailing_liquidity_refuses_non_finite_history():
    values = np.array([1.0, np.nan, 3.0, 4.0], dtype=np.float64)
    with pytest.raises(ValueError):
        trailing_liquidity(values, row_origin=3, lookback=4)


def test_liquidity_tiers_are_balanced_and_ordered_by_liquidity():
    frame = _frame({f"HOSE_S{index:02d}": index for index in range(9)})
    tiers = liquidity_tiers(frame, tier_count=3)
    labelled = frame.assign(liquidity_tier=tiers)
    counts = labelled["liquidity_tier"].value_counts()
    assert set(counts.index) == {"tier_0", "tier_1", "tier_2"}
    assert counts.to_list() == [3, 3, 3]
    top = labelled.loc[labelled["liquidity_tier"] == "tier_0", "liquidity_value"]
    bottom = labelled.loc[labelled["liquidity_tier"] == "tier_2", "liquidity_value"]
    assert top.min() > bottom.max()


def test_liquidity_tiers_are_assigned_inside_each_date():
    frame = _frame(
        {"HOSE_A": 1.0, "HOSE_B": 2.0, "HOSE_C": 3.0, "HOSE_D": 4.0},
        dates=("2022-01-03", "2022-01-04"),
    )
    # Reverse the second date so a global ranking and a per-date ranking differ.
    second = frame["origin_date"] == pd.Timestamp("2022-01-04")
    frame.loc[second, "liquidity_value"] = [40.0, 30.0, 20.0, 10.0]
    labelled = frame.assign(liquidity_tier=liquidity_tiers(frame, tier_count=2))
    for _, day in labelled.groupby("origin_date"):
        assert day["liquidity_tier"].value_counts().to_dict() == {"tier_0": 2, "tier_1": 2}
    assert (
        labelled.loc[second & (labelled["security_id"] == "HOSE_A"), "liquidity_tier"]
        .iloc[0]
        == "tier_0"
    )


def test_liquidity_tiers_break_ties_by_security_id():
    frame = _frame({"HOSE_B": 5.0, "HOSE_A": 5.0, "HOSE_C": 5.0, "HOSE_D": 5.0})
    labelled = frame.assign(liquidity_tier=liquidity_tiers(frame, tier_count=2))
    assignment = dict(zip(labelled["security_id"], labelled["liquidity_tier"]))
    assert assignment == {
        "HOSE_A": "tier_0",
        "HOSE_B": "tier_0",
        "HOSE_C": "tier_1",
        "HOSE_D": "tier_1",
    }


def test_liquidity_tiers_refuse_a_date_thinner_than_the_tier_count():
    frame = _frame({"HOSE_A": 1.0, "HOSE_B": 2.0})
    with pytest.raises(ValueError):
        liquidity_tiers(frame, tier_count=3)


def test_slice_keys_are_the_two_registered_slice_columns():
    assert SLICE_KEYS == ("symbol_group", "liquidity_tier")
