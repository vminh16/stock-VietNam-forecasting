import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from evaluation.research.metrics import DATE_COLUMNS
from evaluation.run_paired_comparison import (
    load_paired_config,
    run_paired_comparison,
)


def _per_date_frame(rank_ic_values, fold_ids):
    records = []
    sessions = pd.bdate_range("2022-01-03", periods=len(rank_ic_values))
    for session, value, fold_id in zip(sessions, rank_ic_values, fold_ids):
        records.append(
            {
                "fold_id": fold_id,
                "origin_date": session.strftime("%Y-%m-%d"),
                "horizon": 5,
                "sample_count": 20,
                "origin_count": 120,
                "symbol_count": 120,
                "correct_count": 60,
                "correct_abs_return": 1.0,
                "total_abs_return": 2.0,
                "rank_ic": value,
                "hit_rate_top10": 0.5,
                "crps_sum": 3.0,
                "coverage_sum": 90.0,
                "width_sum": 12.0,
            }
        )
    return pd.DataFrame(records, columns=DATE_COLUMNS)


@pytest.fixture
def paired_fixture(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    folds = ["eval_2022"] * 30 + ["eval_2023"] * 30
    generator = np.random.default_rng(5)
    noise = generator.normal(0.0, 0.05, 60)

    _per_date_frame(0.03 + noise, folds).to_csv(
        input_dir / "candidate_a_per_date_metrics.csv.gz",
        index=False,
        compression="gzip",
    )
    _per_date_frame(noise, folds).to_csv(
        input_dir / "candidate_b_per_date_metrics.csv.gz",
        index=False,
        compression="gzip",
    )

    config_path = tmp_path / "paired.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "m2_3_paired_inference_v1",
                "input_dir": str(input_dir),
                "report_dir": str(tmp_path / "report"),
                "comparisons": [{"left": "candidate_a", "right": "candidate_b"}],
                "bootstrap": {
                    "method": "stationary",
                    "mean_block_dates": 5,
                    "replicates": 1000,
                    "confidence": 0.95,
                    "seed": 20260901,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return {"config_path": config_path, "input_dir": input_dir}


def test_comparison_reports_pooled_and_per_fold_scopes(paired_fixture):
    manifest, comparisons = run_paired_comparison(paired_fixture["config_path"])

    assert manifest["model_inference"] is False
    assert set(comparisons["scope"]) == {"pooled", "eval_2022", "eval_2023"}
    pooled = comparisons[
        (comparisons["scope"] == "pooled") & (comparisons["metric"] == "RankIC")
    ].iloc[0]
    assert pooled["difference"] == pytest.approx(0.03, abs=1e-9)
    assert pooled["ci_low"] > 0.0
    assert pooled["verdict"] == "candidate_a higher"
    assert pooled["n_paired_dates"] == 60


def test_identical_metrics_report_insufficient_evidence(paired_fixture):
    _, comparisons = run_paired_comparison(paired_fixture["config_path"])

    shared = comparisons[
        (comparisons["scope"] == "pooled") & (comparisons["metric"] == "DA")
    ].iloc[0]

    assert shared["difference"] == pytest.approx(0.0)
    assert shared["verdict"] == "insufficient evidence"


def test_run_is_reproducible_and_records_input_hashes(paired_fixture):
    first, _ = run_paired_comparison(paired_fixture["config_path"])
    second, _ = run_paired_comparison(paired_fixture["config_path"])

    assert first["artifact_hashes"] == second["artifact_hashes"]
    assert set(first["input_hashes"]) == {
        "candidate_a_per_date_metrics.csv.gz",
        "candidate_b_per_date_metrics.csv.gz",
    }


def test_config_rejects_an_unregistered_bootstrap_method(paired_fixture, tmp_path):
    raw = yaml.safe_load(paired_fixture["config_path"].read_text(encoding="utf-8"))
    raw["bootstrap"]["method"] = "iid"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="stationary block bootstrap"):
        load_paired_config(path)


def test_comparison_rejects_candidates_with_different_dates(paired_fixture):
    config = load_paired_config(paired_fixture["config_path"])
    path = paired_fixture["input_dir"] / "candidate_b_per_date_metrics.csv.gz"
    frame = pd.read_csv(path)
    frame.iloc[:-1].to_csv(path, index=False, compression="gzip")

    with pytest.raises(ValueError, match="date sets differ"):
        run_paired_comparison(paired_fixture["config_path"])


def test_cli_runs_directly_from_repo_root(paired_fixture):
    repo_root = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [
            sys.executable,
            "evaluation/run_paired_comparison.py",
            "--config",
            str(paired_fixture["config_path"]),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "RankIC:" in completed.stdout
    manifest = json.loads(
        (Path(yaml.safe_load(paired_fixture["config_path"].read_text())["report_dir"]) / "manifest.json").read_text()
    )
    assert manifest["bootstrap"]["replicates"] == 1000
