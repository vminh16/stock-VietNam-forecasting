import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.freeze_baseline import (
    freeze_baseline,
    load_metric_contract,
    sha256_file,
)


def write_metrics(path, rows):
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def test_load_metric_contract_extracts_only_core_metrics(tmp_path):
    metrics_path = tmp_path / "baseline_metrics.csv"
    write_metrics(
        metrics_path,
        [
            {"Metric": "da", "Validation": 49.375, "Test": 52.76},
            {"Metric": "mw_da", "Validation": 46.57, "Test": 49.38},
            {"Metric": "rank_ic", "Validation": 0.024, "Test": 0.017},
            {"Metric": "hit_rate", "Validation": 57.5, "Test": 53.4},
            {"Metric": "ann_return_long", "Validation": 20.8, "Test": 13.3},
        ],
    )

    metrics = load_metric_contract(metrics_path)

    assert metrics == {
        "Validation": {
            "DA": 49.375,
            "MW-DA": 46.57,
            "RankIC": 0.024,
            "HitRate": 57.5,
        },
        "Test": {
            "DA": 52.76,
            "MW-DA": 49.38,
            "RankIC": 0.017,
            "HitRate": 53.4,
        },
    }


def test_freeze_baseline_writes_manifest_and_report(tmp_path):
    out_dir = tmp_path / "freeze"
    zero_dir = out_dir / "zero_shot"
    fine_dir = out_dir / "finetuned_v2"
    data_dir = tmp_path / "data_cleaned"
    zero_dir.mkdir(parents=True)
    fine_dir.mkdir(parents=True)
    data_dir.mkdir()

    for symbol in ["AAA", "BBB"]:
        (data_dir / f"{symbol}.csv").write_text("timestamps,open,close,high,low,volume,amount\n", encoding="utf-8")

    write_metrics(
        zero_dir / "baseline_metrics.csv",
        [
            {"Metric": "da", "Validation": 49.0, "Test": 53.0},
            {"Metric": "mw_da", "Validation": 47.0, "Test": 49.0},
            {"Metric": "rank_ic", "Validation": 0.02, "Test": 0.01},
            {"Metric": "hit_rate", "Validation": 58.0, "Test": 54.0},
        ],
    )
    write_metrics(
        fine_dir / "finetuned_metrics.csv",
        [
            {"Metric": "da", "Validation": 52.0, "Test": 51.0},
            {"Metric": "mw_da", "Validation": 51.0, "Test": 50.0},
            {"Metric": "rank_ic", "Validation": 0.05, "Test": 0.03},
            {"Metric": "hit_rate", "Validation": 59.0, "Test": 51.0},
        ],
    )

    (zero_dir / "per_date_metrics.csv").write_text("date,da,rank_ic,long_symbols\n", encoding="utf-8")
    (fine_dir / "per_date_metrics.csv").write_text("date,da,rank_ic,long_symbols\n", encoding="utf-8")
    (zero_dir / "backtest_performance.png").write_bytes(b"zero-plot")
    (fine_dir / "finetuned_backtest_performance.png").write_bytes(b"fine-plot")

    zero_config = tmp_path / "zero.yaml"
    fine_config = tmp_path / "fine.yaml"
    zero_config.write_text(
        """
data:
  data_path: data_cleaned
  lookback_window: 126
  predict_window: 5
  max_context: 512
  train_end_date: "2023-01-01"
  val_end_date: "2024-01-01"
inference:
  tokenizer_path: pretrained/Kronos-Tokenizer-base
  predictor_path: pretrained/Kronos-base
  output_dir: reports/milestone_0_baseline_freeze/zero_shot
""".strip(),
        encoding="utf-8",
    )
    fine_config.write_text(
        """
data:
  data_path: data_cleaned
  lookback_window: 126
  predict_window: 5
  max_context: 512
  train_end_date: "2023-01-01"
  val_end_date: "2024-01-01"
inference:
  tokenizer_path: finetune_csv/finetuned/tokenizer_v2/tokenizer/best_model
  predictor_path: finetune_csv/finetuned/basemodel_v2/basemodel/best_model
  output_dir: reports/milestone_0_baseline_freeze/finetuned_v2
""".strip(),
        encoding="utf-8",
    )

    manifest_path, report_path = freeze_baseline(
        zero_shot_dir=zero_dir,
        finetuned_dir=fine_dir,
        out_dir=out_dir,
        zero_shot_config=zero_config,
        finetuned_config=fine_config,
        data_dir=data_dir,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert manifest["freeze_id"] == "milestone_0_baseline_freeze"
    assert manifest["data"]["csv_count"] == 2
    assert manifest["metrics"]["zero_shot"]["Test"]["DA"] == 53.0
    assert manifest["metrics"]["finetuned_v2"]["Test"]["MW-DA"] == 50.0
    assert manifest["comparison"]["test"]["fine_tuned_beats_zero_shot_da"] is False
    assert manifest["comparison"]["test"]["fine_tuned_beats_zero_shot_mw_da"] is True
    assert manifest["artifact_hashes"]["zero_shot/baseline_metrics.csv"] == sha256_file(zero_dir / "baseline_metrics.csv")
    assert "Fine-tuned v2 does not beat zero-shot on Test DA" in report
    assert "Fine-tuned v2 beats zero-shot on Test MW-DA" in report
    assert "DA hard stop: PASS" in report
