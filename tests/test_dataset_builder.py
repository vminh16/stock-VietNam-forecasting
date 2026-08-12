import json
from pathlib import Path

import pandas as pd

from data_pipeline.build_dataset import build_dataset
from data_pipeline.audit import audit_dataset
from data_pipeline.crawl import sha256_file


def write_fixture(root):
    snapshot = root / "raw" / "snapshot"
    (snapshot / "symbols").mkdir(parents=True)
    (snapshot / "calendars").mkdir()
    universe_path = root / "universe.csv"
    pd.DataFrame(
        [["HOSE_AAA", "AAA", "HOSE", "2026-08-09"]],
        columns=["security_id", "symbol", "exchange", "included_as_of"],
    ).to_csv(universe_path, index=False)

    calendar = pd.DataFrame(
        {"time": ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]}
    )
    calendar.to_csv(snapshot / "calendars" / "HOSE.csv", index=False)
    calendar.to_csv(snapshot / "calendars" / "HNX.csv", index=False)
    calendar.to_csv(snapshot / "calendars" / "UPCOM.csv", index=False)

    pd.DataFrame(
        {
            "time": [
                "2024-01-02", "2024-01-02", "2024-01-04", "2024-01-05",
                "2024-01-05", "2024-01-08",
            ],
            "open": [10, 10, 12, 13, 99, 14],
            "high": [11, 11, 13, 14, 100, 15],
            "low": [9, 9, 11, 12, 98, 13],
            "close": [10.5, 10.5, 12.5, 13.5, 99.5, 14.5],
            "volume": [100, 100, 200, 300, 300, 400],
        }
    ).to_csv(snapshot / "symbols" / "AAA.csv", index=False)

    artifacts = {}
    for path in sorted(snapshot.rglob("*.csv")):
        artifacts[path.relative_to(snapshot).as_posix()] = {
            "rows": len(pd.read_csv(path)),
            "sha256": sha256_file(path),
        }
    (snapshot / "crawl_manifest.json").write_text(
        json.dumps({"status": "complete", "artifacts": artifacts}), encoding="utf-8"
    )
    return snapshot, universe_path


def test_builder_splits_missing_and_conflicting_sessions(tmp_path):
    raw_dir, universe_path = write_fixture(tmp_path)
    manifest_path = build_dataset(
        raw_dir, universe_path, "dataset", tmp_path / "curated", expected_size=1
    )

    curated = pd.read_csv(manifest_path.parent / "symbols" / "AAA.csv")
    assert list(curated["timestamps"].str[:10]) == ["2024-01-02", "2024-01-04", "2024-01-08"]
    assert curated["segment_id"].nunique() == 3
    assert curated.loc[2, "session_id"] - curated.loc[1, "session_id"] == 2
    assert curated["amount_source"].eq("derived_ohlc4").all()
    assert curated.loc[0, "amount"] == 100 * (10 + 11 + 9 + 10.5) / 4

    exclusions = pd.read_csv(manifest_path.parent / "exclusions.csv")
    assert set(exclusions["reason"]) == {
        "duplicate_identical",
        "duplicate_conflict",
        "missing_session",
    }
    assert "2024-01-01" not in exclusions["timestamps"].astype(str).tolist()


def test_weekend_does_not_split_segment(tmp_path):
    raw_dir, universe_path = write_fixture(tmp_path)
    symbol_path = raw_dir / "symbols" / "AAA.csv"
    symbol = pd.read_csv(symbol_path)
    symbol = symbol[symbol["time"].isin(["2024-01-05", "2024-01-08"])]
    symbol = symbol.drop_duplicates("time", keep="first")
    symbol.to_csv(symbol_path, index=False)
    raw_manifest = json.loads((raw_dir / "crawl_manifest.json").read_text())
    key = "symbols/AAA.csv"
    raw_manifest["artifacts"][key] = {
        "rows": len(symbol), "sha256": sha256_file(symbol_path)
    }
    (raw_dir / "crawl_manifest.json").write_text(json.dumps(raw_manifest))

    manifest_path = build_dataset(
        raw_dir, universe_path, "weekend", tmp_path / "curated", expected_size=1
    )
    curated = pd.read_csv(manifest_path.parent / "symbols" / "AAA.csv")
    assert curated["segment_id"].nunique() == 1


def test_invalid_and_zero_trade_rows_are_excluded(tmp_path):
    raw_dir, universe_path = write_fixture(tmp_path)
    symbol_path = raw_dir / "symbols" / "AAA.csv"
    symbol = pd.DataFrame(
        {
            "time": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "open": [10, 10, 10], "high": [11, 9, 11], "low": [9, 8, 9],
            "close": [10, 10, 10], "volume": [100, 100, 0],
        }
    )
    symbol.to_csv(symbol_path, index=False)
    raw_manifest = json.loads((raw_dir / "crawl_manifest.json").read_text())
    raw_manifest["artifacts"]["symbols/AAA.csv"] = {
        "rows": 3, "sha256": sha256_file(symbol_path)
    }
    (raw_dir / "crawl_manifest.json").write_text(json.dumps(raw_manifest))

    manifest_path = build_dataset(
        raw_dir, universe_path, "invalid", tmp_path / "curated", expected_size=1
    )
    curated = pd.read_csv(manifest_path.parent / "symbols" / "AAA.csv")
    exclusions = pd.read_csv(manifest_path.parent / "exclusions.csv")
    assert len(curated) == 1
    assert set(exclusions["reason"]) >= {"invalid_ohlc", "zero_trade"}


def test_large_overnight_jump_is_audited_without_rewriting_history(tmp_path):
    raw_dir, universe_path = write_fixture(tmp_path)
    symbol_path = raw_dir / "symbols" / "AAA.csv"
    symbol = pd.DataFrame(
        {
            "time": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "open": [10.0, 10.1, 12.5],
            "high": [10.5, 10.6, 13.0],
            "low": [9.8, 9.9, 12.3],
            "close": [10.0, 10.2, 12.8],
            "volume": [100, 110, 120],
        }
    )
    symbol.to_csv(symbol_path, index=False)
    raw_manifest = json.loads((raw_dir / "crawl_manifest.json").read_text())
    raw_manifest["artifacts"]["symbols/AAA.csv"] = {
        "rows": len(symbol), "sha256": sha256_file(symbol_path)
    }
    (raw_dir / "crawl_manifest.json").write_text(json.dumps(raw_manifest))

    manifest_path = build_dataset(
        raw_dir, universe_path, "jump", tmp_path / "curated", expected_size=1
    )

    curated = pd.read_csv(manifest_path.parent / "symbols" / "AAA.csv")
    candidates = pd.read_csv(manifest_path.parent / "continuity_candidates.csv")
    manifest = json.loads(manifest_path.read_text())

    assert curated["segment_id"].tolist() == [0, 0, 0]
    assert candidates.loc[0, "reason"] == "large_overnight_jump"
    assert candidates.loc[0, "threshold"] == 0.17
    assert manifest["policy_version"] == "strict_v2"
    assert manifest["continuity_policy"] == "audit_large_jumps_no_price_rewrite"
    assert manifest["price_adjustment_status"] == "unverified_provider_history"
    assert manifest["amount_policy"] == "derived_ohlc4_compatibility_proxy"


def test_repeated_builds_produce_identical_curated_hashes(tmp_path):
    raw_dir, universe_path = write_fixture(tmp_path)
    first = build_dataset(
        raw_dir, universe_path, "one", tmp_path / "curated", expected_size=1
    )
    second = build_dataset(
        raw_dir, universe_path, "two", tmp_path / "curated", expected_size=1
    )
    first_manifest = json.loads(first.read_text())
    second_manifest = json.loads(second.read_text())
    assert first_manifest["artifact_hashes"] == second_manifest["artifact_hashes"]


def test_audit_reports_window_contract(tmp_path):
    raw_dir, universe_path = write_fixture(tmp_path)
    manifest_path = build_dataset(
        raw_dir, universe_path, "audit", tmp_path / "curated", expected_size=1
    )
    report_path = audit_dataset(
        manifest_path.parent,
        tmp_path / "reports",
        lookbacks=(1, 2),
        horizon=1,
    )

    quality = pd.read_csv(report_path.parent / "data_quality.csv")
    assert list(quality["symbol"]) == ["AAA"]
    assert {"windows_l1_h1", "windows_l2_h1", "max_segment_rows"} <= set(quality.columns)
    report = report_path.read_text(encoding="utf-8")
    assert "dependent observations" in report
    assert "derived_ohlc4" in report
    published_manifest = json.loads(
        (report_path.parent / "dataset_manifest.json").read_text(encoding="utf-8")
    )
    assert published_manifest["raw_snapshot_manifest"]["status"] == "complete"
