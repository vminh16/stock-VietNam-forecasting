import json
from datetime import date

import numpy as np
import pandas as pd
import pytest
import yaml

from data_pipeline.crawl import sha256_file
from evaluation.build_origin_registry import build_registry_artifacts
from evaluation.research.origins import FoldSpec, OriginRegistryConfig
from evaluation.run_data_diagnostics import (
    load_diagnostics_config,
    run_data_diagnostics,
)


@pytest.fixture
def diagnostics_fixture(tmp_path):
    dataset_dir = tmp_path / "curated" / "fixture"
    symbols_dir = dataset_dir / "symbols"
    symbols_dir.mkdir(parents=True)

    sessions = pd.bdate_range("2021-01-04", "2022-12-30")
    generator = np.random.default_rng(99)
    universe_rows = []
    artifact_hashes = {}
    for index in range(12):
        symbol = f"S{index:02d}"
        security_id = f"HOSE_{symbol}"
        steps = generator.normal(0.0005, 0.02, len(sessions))
        close = 25.0 * np.exp(np.cumsum(steps))
        frame = pd.DataFrame(
            {
                "security_id": security_id,
                "symbol": symbol,
                "timestamps": sessions + pd.Timedelta(hours=9),
                "session_id": range(len(sessions)),
                "segment_id": 0,
                "open": close * 0.997,
                "high": close * 1.012,
                "low": close * 0.988,
                "close": close,
                "volume": generator.lognormal(11.0, 0.4, len(sessions)),
                "amount": close * generator.lognormal(11.0, 0.4, len(sessions)),
                "amount_source": "derived_ohlc4",
            }
        )
        path = symbols_dir / f"{symbol}.csv"
        frame.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")
        artifact_hashes[f"symbols/{symbol}.csv"] = sha256_file(path)
        universe_rows.append([security_id, symbol, "HOSE", "2026-08-09"])

    dataset_manifest = {
        "dataset_id": "fixture",
        "policy_version": "strict_v2",
        "price_adjustment_status": "unverified_provider_history",
        "amount_policy": "derived_ohlc4_compatibility_proxy",
        "artifact_hashes": artifact_hashes,
    }
    manifest_path = dataset_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(dataset_manifest), encoding="utf-8")

    universe_path = tmp_path / "universe.csv"
    pd.DataFrame(
        universe_rows, columns=["security_id", "symbol", "exchange", "included_as_of"]
    ).to_csv(universe_path, index=False)

    registry_config = OriginRegistryConfig(
        schema_version="m2_1_origin_registry_v1",
        dataset_id="fixture",
        dataset_dir=dataset_dir,
        dataset_manifest_path=manifest_path,
        universe_path=universe_path,
        registry_path=tmp_path / "common_origins.csv.gz",
        report_dir=tmp_path / "registry_report",
        lookbacks=(63, 126),
        horizon=5,
        minimum_cross_section=10,
        lockbox_start=date(2026, 1, 1),
        folds=(FoldSpec("eval_2022", date(2022, 1, 1), date(2022, 12, 31)),),
    )
    registry_config_path = tmp_path / "origins.yaml"
    registry_config_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": registry_config.schema_version,
                "dataset_id": registry_config.dataset_id,
                "dataset_dir": str(dataset_dir),
                "dataset_manifest_path": str(manifest_path),
                "universe_path": str(universe_path),
                "registry_path": str(registry_config.registry_path),
                "report_dir": str(registry_config.report_dir),
                "lookbacks": [63, 126],
                "horizon": 5,
                "minimum_cross_section": 10,
                "lockbox_start": "2026-01-01",
                "folds": [
                    {"fold_id": "eval_2022", "start": "2022-01-01", "end": "2022-12-31"}
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    build_registry_artifacts(registry_config_path, command="pytest fixture")

    config_path = tmp_path / "diagnostics.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "m2_4_data_diagnostics_v1",
                "dataset_id": "fixture",
                "dataset_dir": str(dataset_dir),
                "dataset_manifest_path": str(manifest_path),
                "registry_path": str(registry_config.registry_path),
                "registry_manifest_path": str(
                    registry_config.report_dir / "manifest.json"
                ),
                "output_dir": str(tmp_path / "diag_output"),
                "report_dir": str(tmp_path / "diag_report"),
                "variance_ratio": {
                    "horizons": [2, 5],
                    "minimum_returns": 60,
                    "liquidity_tiers": 3,
                },
                "normalization": {
                    "short_lookback": 63,
                    "long_lookback": 126,
                    "date_stride": 20,
                    "clip": 5.0,
                    "features": ["open", "high", "low", "close", "volume", "amount"],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return {"config_path": config_path, "report_dir": tmp_path / "diag_report"}


def test_diagnostics_report_random_walk_data_near_one(diagnostics_fixture):
    manifest, ratio_summary, _, _ = run_data_diagnostics(
        diagnostics_fixture["config_path"]
    )

    assert manifest["model_inference"] is False
    folds = ratio_summary[ratio_summary["scope_kind"] == "fold_id"]
    assert set(folds["q"]) == {2, 5}
    assert folds["median_variance_ratio"].between(0.7, 1.3).all()


def test_diagnostics_expose_the_normalization_scale_gap(diagnostics_fixture):
    _, _, norm_table, norm_summary = run_data_diagnostics(
        diagnostics_fixture["config_path"]
    )

    assert norm_summary["windows"] > 0
    prices = norm_table[norm_table["feature"].isin(["open", "high", "low", "close"])]
    volumes = norm_table[norm_table["feature"].isin(["volume", "amount"])]
    assert (prices["median_scale_ratio"] < volumes["median_scale_ratio"].min()).all()
    assert (norm_table["origins"] == norm_summary["windows"]).all()


def test_diagnostics_are_reproducible(diagnostics_fixture):
    first, _, _, _ = run_data_diagnostics(diagnostics_fixture["config_path"])
    second, _, _, _ = run_data_diagnostics(diagnostics_fixture["config_path"])

    assert first["artifact_hashes"] == second["artifact_hashes"]


def test_config_rejects_a_lookback_pair_in_the_wrong_order(diagnostics_fixture, tmp_path):
    raw = yaml.safe_load(diagnostics_fixture["config_path"].read_text(encoding="utf-8"))
    raw["normalization"]["short_lookback"] = 126
    raw["normalization"]["long_lookback"] = 63
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="short_lookback must be shorter"):
        load_diagnostics_config(path)
