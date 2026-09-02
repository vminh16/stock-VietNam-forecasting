import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.research.metrics import ORIGIN_COLUMNS
from evaluation.run_metric_slices import (
    attach_slices,
    slice_candidate_id,
    slice_dates,
)

SLICE_KEY = "liquidity_tier"


def _origins(records):
    rows = []
    for origin_date, security_id, predicted, actual in records:
        rows.append(
            {
                "fold_id": "fold_2022",
                "origin_id": f"{origin_date}:{security_id}",
                "security_id": security_id,
                "origin_date": pd.Timestamp(origin_date),
                "horizon": 5,
                "sample_count": 10,
                "predicted_return": float(predicted),
                "actual_return": float(actual),
                "crps": 0.02,
                "interval_covered": 1.0,
                "interval_width": 0.1,
            }
        )
    return pd.DataFrame(rows, columns=ORIGIN_COLUMNS)


def _slices(origins, assignment):
    return pd.DataFrame(
        {
            "origin_id": origins["origin_id"],
            "security_id": origins["security_id"],
            "origin_date": origins["origin_date"],
            SLICE_KEY: origins["security_id"].map(assignment),
        }
    )


def _two_tier_day(origin_date="2022-01-03", size=10):
    """Tier 0 ranks perfectly, tier 1 ranks backwards, so pooled RankIC cancels."""
    records = []
    assignment = {}
    for index in range(size):
        top = f"HOSE_T0_{index:02d}"
        bottom = f"HOSE_T1_{index:02d}"
        records.append((origin_date, top, 0.01 * (index + 1), 0.01 * (index + 1)))
        records.append((origin_date, bottom, 0.01 * (index + 1), -0.01 * (index + 1)))
        assignment[top] = "tier_0"
        assignment[bottom] = "tier_1"
    origins = _origins(records)
    return origins, _slices(origins, assignment)


def test_attach_slices_refuses_an_unlabelled_origin():
    origins, slices = _two_tier_day()
    with pytest.raises(ValueError, match="no liquidity_tier label"):
        attach_slices(origins, slices.iloc[1:], [SLICE_KEY])


def test_attach_slices_refuses_a_disagreeing_slice_table():
    origins, slices = _two_tier_day()
    slices = slices.copy()
    slices.loc[0, "security_id"] = "HOSE_WRONG"
    with pytest.raises(ValueError, match="security_id"):
        attach_slices(origins, slices, [SLICE_KEY])


def test_slice_metrics_separate_signal_that_pooled_metrics_cancel():
    origins, slices = _two_tier_day()
    labelled = attach_slices(origins, slices, [SLICE_KEY])

    pooled, _ = slice_dates(labelled, minimum_cross_section=10)
    assert abs(float(pooled["rank_ic"].iloc[0])) < 0.2

    scores = {}
    for value, block in labelled.groupby(SLICE_KEY):
        dates, _ = slice_dates(block, minimum_cross_section=10)
        scores[value] = float(dates["rank_ic"].iloc[0])
    assert scores["tier_0"] == pytest.approx(1.0)
    assert scores["tier_1"] == pytest.approx(-1.0)


def test_slice_dates_drops_only_the_thin_dates_and_counts_them():
    full, _ = _two_tier_day("2022-01-03")
    thin = _origins(
        [("2022-01-04", f"HOSE_T0_{index:02d}", 0.01, 0.01) for index in range(4)]
    )
    block = pd.concat([full, thin], ignore_index=True)
    dates, dropped = slice_dates(block, minimum_cross_section=10)
    assert dropped == 1
    assert dates["origin_date"].to_list() == [pd.Timestamp("2022-01-03")]


def test_slice_dates_refuse_a_slice_with_no_usable_date():
    thin = _origins(
        [("2022-01-04", f"HOSE_T0_{index:02d}", 0.01, 0.01) for index in range(4)]
    )
    with pytest.raises(ValueError, match="below the minimum cross-section"):
        slice_dates(thin, minimum_cross_section=10)


def test_slice_metrics_use_only_the_slice_rows():
    origins, slices = _two_tier_day()
    labelled = attach_slices(origins, slices, [SLICE_KEY])
    top = labelled[labelled[SLICE_KEY] == "tier_0"]
    dates, _ = slice_dates(top, minimum_cross_section=10)
    assert int(dates["origin_count"].iloc[0]) == 10
    assert int(dates["correct_count"].iloc[0]) == 10
    assert float(dates["hit_rate_top10"].iloc[0]) == pytest.approx(1.0)


def test_sliced_candidate_id_matches_the_paired_comparison_convention():
    sliced = slice_candidate_id("base_l126", "liquidity_tier", "tier_0")
    assert sliced == "base_l126__liquidity_tier_tier_0"
    assert f"{sliced}_per_date_metrics.csv.gz".endswith("_per_date_metrics.csv.gz")


def test_slice_dates_keep_the_locked_origin_contract():
    origins, slices = _two_tier_day()
    labelled = attach_slices(origins, slices, [SLICE_KEY])
    assert set(ORIGIN_COLUMNS).issubset(labelled.columns)
    dates, _ = slice_dates(labelled, minimum_cross_section=10)
    assert np.isfinite(dates["crps_sum"].to_numpy()).all()
