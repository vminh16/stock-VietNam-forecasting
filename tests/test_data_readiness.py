import json

import pandas as pd

from data_pipeline.build_dataset import build_dataset
from data_pipeline.readiness import audit_data_readiness
from test_dataset_builder import write_fixture


def test_readiness_report_is_conditional_when_price_adjustment_is_unverified(tmp_path):
    raw_dir, universe_path = write_fixture(tmp_path)
    manifest_path = build_dataset(
        raw_dir, universe_path, "readiness", tmp_path / "curated", expected_size=1
    )

    report_path = audit_data_readiness(
        manifest_path.parent,
        tmp_path / "report",
        lookbacks=(2, 3),
        horizon=1,
    )

    summary = json.loads((report_path.parent / "readiness_summary.json").read_text())
    symbols = pd.read_csv(report_path.parent / "symbol_readiness.csv")

    assert summary["status"] == "CONDITIONAL"
    assert summary["blocking_findings"] == []
    assert "unverified_provider_history" in summary["conditional_findings"]
    assert "derived_ohlc4_compatibility_proxy" in summary["conditional_findings"]
    assert symbols.loc[0, "amount_proxy_max_relative_error"] < 1e-12
    assert (report_path.parent / "continuity_candidates.csv").exists()
    assert report_path.read_text(encoding="utf-8").startswith("# VN150 Data Readiness")


def test_readiness_detects_duplicate_symbol_session_as_blocker(tmp_path):
    raw_dir, universe_path = write_fixture(tmp_path)
    manifest_path = build_dataset(
        raw_dir, universe_path, "readiness", tmp_path / "curated", expected_size=1
    )
    symbol_path = manifest_path.parent / "symbols" / "AAA.csv"
    frame = pd.read_csv(symbol_path)
    pd.concat([frame, frame.iloc[[0]]], ignore_index=True).to_csv(symbol_path, index=False)

    report_path = audit_data_readiness(
        manifest_path.parent,
        tmp_path / "report",
        lookbacks=(2,),
        horizon=1,
    )
    summary = json.loads((report_path.parent / "readiness_summary.json").read_text())

    assert summary["status"] == "BLOCKED"
    assert "duplicate_symbol_session" in summary["blocking_findings"]
