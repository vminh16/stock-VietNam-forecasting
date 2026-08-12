import hashlib
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from data_pipeline.crawl import sha256_file
from evaluation.research.origins import (
    FoldSpec,
    OriginRegistryConfig,
    build_common_origins,
    dataset_fingerprint,
    load_origin_config,
    validate_common_origins,
)


@pytest.fixture
def registry_fixture(tmp_path):
    dataset_dir = tmp_path / "curated" / "fixture"
    symbols_dir = dataset_dir / "symbols"
    symbols_dir.mkdir(parents=True)

    history_dates = pd.bdate_range("2021-06-01", "2022-12-30")
    lockbox_dates = pd.bdate_range("2026-01-02", periods=140)
    universe_rows = []
    artifact_hashes = {}
    for index in range(10):
        symbol = f"S{index:02d}"
        security_id = f"HOSE_{symbol}"
        dates = history_dates[1:] if index == 9 else history_dates
        frame = pd.DataFrame(
            {
                "security_id": security_id,
                "symbol": symbol,
                "timestamps": dates + pd.Timedelta(hours=9),
                "session_id": range(len(dates)),
                "segment_id": 0,
            }
        )
        lockbox = pd.DataFrame(
            {
                "security_id": security_id,
                "symbol": symbol,
                "timestamps": lockbox_dates + pd.Timedelta(hours=9),
                "session_id": range(len(dates), len(dates) + len(lockbox_dates)),
                "segment_id": 1,
            }
        )
        frame = pd.concat([frame, lockbox], ignore_index=True)
        symbol_path = symbols_dir / f"{symbol}.csv"
        frame.to_csv(symbol_path, index=False, date_format="%Y-%m-%d %H:%M:%S")
        artifact_hashes[f"symbols/{symbol}.csv"] = sha256_file(symbol_path)
        universe_rows.append([security_id, symbol, "HOSE", "2026-08-09"])

    manifest = {
        "dataset_id": "fixture",
        "policy_version": "strict_v2",
        "price_adjustment_status": "unverified_provider_history",
        "amount_policy": "derived_ohlc4_compatibility_proxy",
        "artifact_hashes": artifact_hashes,
    }
    (dataset_dir / "dataset_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    universe_path = tmp_path / "universe.csv"
    universe = pd.DataFrame(
        universe_rows,
        columns=["security_id", "symbol", "exchange", "included_as_of"],
    )
    universe.to_csv(universe_path, index=False)
    reversed_universe_path = tmp_path / "universe_reversed.csv"
    universe.iloc[::-1].to_csv(reversed_universe_path, index=False)

    config = OriginRegistryConfig(
        schema_version="m2_1_origin_registry_v1",
        dataset_id="fixture",
        dataset_dir=dataset_dir,
        universe_path=universe_path,
        registry_path=tmp_path / "common_origins.csv.gz",
        report_dir=tmp_path / "report",
        lookbacks=(63, 126),
        horizon=5,
        minimum_cross_section=10,
        lockbox_start=date(2026, 1, 1),
        folds=(FoldSpec("eval_2022", date(2022, 1, 1), date(2022, 12, 31)),),
    )
    return {
        "config": config,
        "reordered_config": replace(config, universe_path=reversed_universe_path),
        "fold_ends": {"eval_2022": pd.Timestamp("2022-12-31")},
    }


def test_m2_1_config_locks_common_origin_contract():
    config = load_origin_config(Path("evaluation/configs/m2_1_origins.yaml"))

    assert config.dataset_id == "vn150_strict_v2"
    assert config.lookbacks == (63, 126)
    assert config.horizon == 5
    assert config.minimum_cross_section == 10
    assert config.lockbox_start.isoformat() == "2026-01-01"
    assert [(fold.start.isoformat(), fold.end.isoformat()) for fold in config.folds] == [
        ("2022-01-01", "2022-12-31"),
        ("2023-01-01", "2023-12-31"),
        ("2024-01-01", "2024-12-31"),
        ("2025-01-01", "2025-12-31"),
    ]


def test_config_rejects_a_fold_that_touches_lockbox(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
schema_version: m2_1_origin_registry_v1
dataset_id: vn150_strict_v2
dataset_dir: data/curated/vn150_strict_v2
universe_path: data_pipeline/universe_150.csv
registry_path: data/evaluation/m2_1/common_origins.csv.gz
report_dir: reports/milestone_2_research_eval/origin_registry
lookbacks: [63, 126]
horizon: 5
minimum_cross_section: 10
lockbox_start: 2026-01-01
folds:
  - {fold_id: eval_2025, start: 2025-01-01, end: 2026-01-02}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="lockbox"):
        load_origin_config(path)


def test_dataset_fingerprint_ignores_generated_timestamp():
    base = {
        "dataset_id": "vn150_strict_v2",
        "policy_version": "strict_v2",
        "artifact_hashes": {"symbols/AAA.csv": "abc"},
    }

    first = dataset_fingerprint({**base, "generated_at_utc": "first"})
    second = dataset_fingerprint({**base, "generated_at_utc": "second"})
    expected = hashlib.sha256(
        json.dumps(base, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    assert first == second == expected


def test_registry_requires_both_lookbacks_and_five_future_rows(registry_fixture):
    origins = build_common_origins(registry_fixture["config"])

    assert (origins["row_origin"] - origins["row_start_l63"] == 62).all()
    assert (origins["row_origin"] - origins["row_start_l126"] == 125).all()
    assert (origins["row_target_start"] - origins["row_origin"] == 1).all()
    assert (origins["row_target_end"] - origins["row_origin"] == 5).all()


def test_registry_never_crosses_segment_fold_or_lockbox(registry_fixture):
    config = registry_fixture["config"]
    origins = build_common_origins(config)

    assert origins["origin_date"].max() < pd.Timestamp("2026-01-01")
    assert origins["target_end_date"].max() < pd.Timestamp("2026-01-01")
    assert (
        origins["target_end_date"]
        <= origins["fold_id"].map(registry_fixture["fold_ends"])
    ).all()
    validate_common_origins(origins, config)


def test_dates_below_minimum_cross_section_are_removed(registry_fixture):
    config = registry_fixture["config"]
    origins = build_common_origins(config)
    counts = origins.groupby(["fold_id", "origin_date"])["security_id"].nunique()

    assert counts.ge(config.minimum_cross_section).all()
    assert counts.min() == 10


def test_origin_ids_and_rows_are_stable_when_input_order_changes(registry_fixture):
    first = build_common_origins(registry_fixture["config"])
    second = build_common_origins(registry_fixture["reordered_config"])
    columns = ["origin_id", "security_id", "origin_date", "row_origin"]

    pd.testing.assert_frame_equal(first[columns], second[columns])
