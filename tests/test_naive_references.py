import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from data_pipeline.crawl import sha256_file
from evaluation.build_origin_registry import build_registry_artifacts
from evaluation.research.origins import FoldSpec, OriginRegistryConfig
from evaluation.run_naive_references import (
    evaluate_naive_references,
    load_naive_config,
)


SYMBOL_COUNT = 12


@pytest.fixture
def naive_fixture(tmp_path):
    dataset_dir = tmp_path / "curated" / "fixture"
    symbols_dir = dataset_dir / "symbols"
    symbols_dir.mkdir(parents=True)

    sessions = pd.bdate_range("2021-01-04", "2022-12-30")
    generator = np.random.default_rng(4242)
    universe_rows = []
    artifact_hashes = {}
    for index in range(SYMBOL_COUNT):
        symbol = f"S{index:02d}"
        security_id = f"HOSE_{symbol}"
        steps = generator.normal(loc=0.0004, scale=0.018, size=len(sessions))
        close = 20.0 * np.exp(np.cumsum(steps))
        frame = pd.DataFrame(
            {
                "security_id": security_id,
                "symbol": symbol,
                "timestamps": sessions + pd.Timedelta(hours=9),
                "session_id": range(len(sessions)),
                "segment_id": 0,
                "open": close * 0.998,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": 100000.0,
                "amount": close * 100000.0,
                "amount_source": "derived_ohlc4",
            }
        )
        symbol_path = symbols_dir / f"{symbol}.csv"
        frame.to_csv(symbol_path, index=False, date_format="%Y-%m-%d %H:%M:%S")
        artifact_hashes[f"symbols/{symbol}.csv"] = sha256_file(symbol_path)
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
                "dataset_dir": str(registry_config.dataset_dir),
                "dataset_manifest_path": str(registry_config.dataset_manifest_path),
                "universe_path": str(registry_config.universe_path),
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

    naive_config_path = tmp_path / "naive.yaml"
    naive_config_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "m2_2_naive_references_v1",
                "dataset_id": "fixture",
                "dataset_dir": str(dataset_dir),
                "dataset_manifest_path": str(manifest_path),
                "registry_path": str(registry_config.registry_path),
                "registry_manifest_path": str(
                    registry_config.report_dir / "manifest.json"
                ),
                "output_dir": str(tmp_path / "naive_output"),
                "report_dir": str(tmp_path / "naive_report"),
                "horizon": 5,
                "sample_count": 8,
                "sampling_seed": 20260812,
                "interval_quantiles": [0.10, 0.90],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return {
        "config_path": naive_config_path,
        "registry_path": registry_config.registry_path,
        "symbols_dir": symbols_dir,
    }


def _expected_actual_returns(naive_fixture):
    registry = pd.read_csv(naive_fixture["registry_path"])
    returns = []
    for symbol, rows in registry.groupby("symbol", sort=True):
        close = pd.read_csv(naive_fixture["symbols_dir"] / f"{symbol}.csv")[
            "close"
        ].to_numpy(dtype=np.float64)
        origin = rows["row_origin"].to_numpy(dtype=np.int64)
        target_end = rows["row_target_end"].to_numpy(dtype=np.int64)
        returns.append(close[target_end] / close[origin] - 1.0)
    return np.concatenate(returns)


def test_naive_run_reports_both_causal_references(naive_fixture):
    manifest, summary = evaluate_naive_references(naive_fixture["config_path"])

    assert manifest["candidates"] == ["persistence", "recent_return_bootstrap"]
    assert manifest["model_inference"] is False
    assert set(summary["candidate_id"]) == {"persistence", "recent_return_bootstrap"}
    assert set(summary["scope"]) == {"eval_2022", "pooled"}
    pooled = summary[summary["scope"] == "pooled"].set_index("candidate_id")
    assert (pooled["origin_rows"] == manifest["origin_rows"]).all()
    assert pooled.loc["persistence", "sample_count"] == 8


def test_persistence_is_a_permanent_down_call(naive_fixture):
    _, summary = evaluate_naive_references(naive_fixture["config_path"])
    pooled = summary[summary["scope"] == "pooled"].set_index("candidate_id")

    actual = _expected_actual_returns(naive_fixture)
    expected_da = float((actual <= 0).mean()) * 100.0

    assert pooled.loc["persistence", "DA"] == pytest.approx(expected_da)
    assert pooled.loc["persistence", "RankIC"] == pytest.approx(0.0)
    assert pooled.loc["persistence", "interval_width"] == pytest.approx(0.0)


def test_bootstrap_reference_carries_dispersion_without_ranking_signal(naive_fixture):
    _, summary = evaluate_naive_references(naive_fixture["config_path"])
    pooled = summary[summary["scope"] == "pooled"].set_index("candidate_id")

    assert pooled.loc["recent_return_bootstrap", "interval_width"] > 0.0
    assert 0.0 < pooled.loc["recent_return_bootstrap", "coverage"] <= 1.0
    assert abs(pooled.loc["recent_return_bootstrap", "RankIC"]) < 0.2
    assert (
        pooled.loc["recent_return_bootstrap", "CRPS"]
        < pooled.loc["persistence", "CRPS"] * 3.0
    )


def test_naive_run_is_reproducible(naive_fixture):
    first, _ = evaluate_naive_references(naive_fixture["config_path"])
    first_hashes = dict(first["artifact_hashes"])
    second, _ = evaluate_naive_references(naive_fixture["config_path"])

    assert second["artifact_hashes"] == first_hashes


def test_run_rejects_a_registry_that_does_not_match_its_manifest(naive_fixture):
    config = load_naive_config(naive_fixture["config_path"])
    registry = pd.read_csv(config.registry_path)
    registry.iloc[:-1].to_csv(config.registry_path, index=False, compression="gzip")

    with pytest.raises(ValueError, match="manifest hash"):
        evaluate_naive_references(naive_fixture["config_path"])


def test_cli_runs_directly_from_repo_root(naive_fixture):
    repo_root = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [
            sys.executable,
            "evaluation/run_naive_references.py",
            "--config",
            str(naive_fixture["config_path"]),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "persistence: DA=" in completed.stdout
