import hashlib
import json
from pathlib import Path

import pytest

from evaluation.research.origins import dataset_fingerprint, load_origin_config


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
