import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml


FREEZE_ID = "milestone_0_baseline_freeze"
DEFAULT_ZERO_SHOT_CONFIG = Path("evaluation/configs/milestone0_baseline_zero_shot.yaml")
DEFAULT_FINETUNED_CONFIG = Path("evaluation/configs/milestone0_finetuned_v2.yaml")
DEFAULT_DATA_DIR = Path("data_cleaned")
METRIC_CONTRACT = {
    "da": "DA",
    "mw_da": "MW-DA",
    "rank_ic": "RankIC",
    "hit_rate": "HitRate",
}


def sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_metric_contract(metrics_path):
    df = pd.read_csv(metrics_path)
    if "Metric" not in df.columns:
        raise ValueError(f"Metrics CSV missing Metric column: {metrics_path}")

    selected = df[df["Metric"].isin(METRIC_CONTRACT.keys())]
    metrics = {"Validation": {}, "Test": {}}
    for _, row in selected.iterrows():
        name = METRIC_CONTRACT[row["Metric"]]
        metrics["Validation"][name] = float(row["Validation"])
        metrics["Test"][name] = float(row["Test"])
    return metrics


def load_yaml(path):
    if path is None:
        return {}
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def find_metrics_file(model_dir, preferred_name):
    model_dir = Path(model_dir)
    preferred = model_dir / preferred_name
    if preferred.exists():
        return preferred
    matches = sorted(model_dir.glob("*_metrics.csv"))
    if not matches:
        raise FileNotFoundError(f"No metrics CSV found in {model_dir}")
    return matches[0]


def relative_artifact_path(path, out_dir):
    path = Path(path)
    out_dir = Path(out_dir)
    try:
        return path.relative_to(out_dir).as_posix()
    except ValueError:
        return path.as_posix()


def collect_artifact_hashes(out_dir):
    out_dir = Path(out_dir)
    hashes = {}
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name not in {"manifest.json", "baseline_freeze_report.md"}:
            hashes[relative_artifact_path(path, out_dir)] = sha256_file(path)
    return hashes


def count_data_csvs(data_dir):
    data_dir = Path(data_dir)
    if not data_dir.exists():
        return 0
    return len(list(data_dir.glob("*.csv")))


def build_comparison(zero_metrics, fine_metrics):
    zero_test = zero_metrics["Test"]
    fine_test = fine_metrics["Test"]
    return {
        "test": {
            "zero_shot_da_hard_stop_pass": zero_test["DA"] >= 52.0,
            "finetuned_da_hard_stop_pass": fine_test["DA"] >= 52.0,
            "fine_tuned_beats_zero_shot_da": fine_test["DA"] > zero_test["DA"],
            "fine_tuned_beats_zero_shot_mw_da": fine_test["MW-DA"] > zero_test["MW-DA"],
        }
    }


def evaluation_command(config_path):
    return (
        r"C:\Users\USER\anaconda3\envs\stock\python.exe "
        f"evaluation/inference_pipeline.py --config {Path(config_path).as_posix()} --mode final"
    )


def render_metric_table(zero_metrics, fine_metrics):
    lines = [
        "| Metric | Zero-shot Validation | Fine-tuned Validation | Zero-shot Test | Fine-tuned Test |",
        "|---|---:|---:|---:|---:|",
    ]
    for metric in ["DA", "MW-DA", "RankIC", "HitRate"]:
        lines.append(
            f"| {metric} | "
            f"{zero_metrics['Validation'][metric]:.4f} | "
            f"{fine_metrics['Validation'][metric]:.4f} | "
            f"{zero_metrics['Test'][metric]:.4f} | "
            f"{fine_metrics['Test'][metric]:.4f} |"
        )
    return "\n".join(lines)


def render_report(manifest):
    zero_metrics = manifest["metrics"]["zero_shot"]
    fine_metrics = manifest["metrics"]["finetuned_v2"]
    comparison = manifest["comparison"]["test"]

    da_sentence = (
        "Fine-tuned v2 beats zero-shot on Test DA."
        if comparison["fine_tuned_beats_zero_shot_da"]
        else "Fine-tuned v2 does not beat zero-shot on Test DA."
    )
    mw_da_sentence = (
        "Fine-tuned v2 beats zero-shot on Test MW-DA."
        if comparison["fine_tuned_beats_zero_shot_mw_da"]
        else "Fine-tuned v2 does not beat zero-shot on Test MW-DA."
    )
    hard_stop = "PASS" if comparison["zero_shot_da_hard_stop_pass"] else "FAIL"
    fine_hard_stop = "PASS" if comparison["finetuned_da_hard_stop_pass"] else "FAIL"

    mode_note = ""
    if manifest["mode"] != "final":
        mode_note = (
            "\n> Note: This report is a fallback snapshot from existing sampled/dev artifacts. "
            "It is not the canonical final freeze.\n"
        )

    return f"""# Milestone 0 Baseline Freeze Report

Freeze id: `{manifest['freeze_id']}`
Generated at UTC: `{manifest['generated_at_utc']}`
{mode_note}

## Evaluation Contract

- Mode: `{manifest['mode']}`
- Data path: `{manifest['data']['path']}`
- CSV count: `{manifest['data']['csv_count']}`
- Lookback window: `{manifest['data']['lookback_window']}`
- Predict window: `{manifest['data']['predict_window']}`
- Train end date: `{manifest['data']['train_end_date']}`
- Validation end date: `{manifest['data']['val_end_date']}`
- Metrics: `DA`, `MW-DA`, `RankIC`, `HitRate`

## Commands

```powershell
{manifest['commands']['zero_shot']}
{manifest['commands']['finetuned_v2']}
C:\\Users\\USER\\anaconda3\\envs\\stock\\python.exe evaluation/freeze_baseline.py --zero-shot-dir {manifest['artifact_dirs']['zero_shot']} --finetuned-dir {manifest['artifact_dirs']['finetuned_v2']} --out-dir {manifest['artifact_dirs']['root']} --mode {manifest['mode']}
```

## Metric Snapshot

{render_metric_table(zero_metrics, fine_metrics)}

## Interpretation

- Zero-shot DA hard stop: {hard_stop} (`Test DA >= 52`)
- Fine-tuned v2 DA hard stop: {fine_hard_stop} (`Test DA >= 52`)
- {da_sentence}
- {mw_da_sentence}
- Treat fine-tuned v2 as a model improvement only if final `DA` and `MW-DA` beat zero-shot, or if a later report explains a deliberate tradeoff.
- This is a research baseline, not investment advice.

## Next Phase

Milestone 1 should build the Kronos Path Viewer: actual path, stochastic forecast paths, mean/median forecast line, confidence band, and clear uncertainty language.
"""


def freeze_baseline(
    zero_shot_dir,
    finetuned_dir,
    out_dir,
    zero_shot_config=DEFAULT_ZERO_SHOT_CONFIG,
    finetuned_config=DEFAULT_FINETUNED_CONFIG,
    data_dir=DEFAULT_DATA_DIR,
    mode="final",
):
    zero_shot_dir = Path(zero_shot_dir)
    finetuned_dir = Path(finetuned_dir)
    out_dir = Path(out_dir)
    zero_shot_config = Path(zero_shot_config)
    finetuned_config = Path(finetuned_config)
    data_dir = Path(data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    zero_metrics_path = find_metrics_file(zero_shot_dir, "baseline_metrics.csv")
    fine_metrics_path = find_metrics_file(finetuned_dir, "finetuned_metrics.csv")
    zero_metrics = load_metric_contract(zero_metrics_path)
    fine_metrics = load_metric_contract(fine_metrics_path)
    zero_config = load_yaml(zero_shot_config)
    fine_config = load_yaml(finetuned_config)
    data_config = zero_config.get("data", {})

    manifest = {
        "freeze_id": FREEZE_ID,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": mode,
        "configs": {
            "zero_shot": zero_shot_config.as_posix(),
            "finetuned_v2": finetuned_config.as_posix(),
        },
        "commands": {
            "zero_shot": evaluation_command(zero_shot_config),
            "finetuned_v2": evaluation_command(finetuned_config),
        },
        "data": {
            "path": data_dir.as_posix(),
            "csv_count": count_data_csvs(data_dir),
            "lookback_window": data_config.get("lookback_window"),
            "predict_window": data_config.get("predict_window"),
            "max_context": data_config.get("max_context"),
            "train_end_date": data_config.get("train_end_date"),
            "val_end_date": data_config.get("val_end_date"),
        },
        "models": {
            "zero_shot": {
                "tokenizer_path": zero_config.get("inference", {}).get("tokenizer_path"),
                "predictor_path": zero_config.get("inference", {}).get("predictor_path"),
            },
            "finetuned_v2": {
                "tokenizer_path": fine_config.get("inference", {}).get("tokenizer_path"),
                "predictor_path": fine_config.get("inference", {}).get("predictor_path"),
            },
        },
        "artifact_dirs": {
            "root": out_dir.as_posix(),
            "zero_shot": zero_shot_dir.as_posix(),
            "finetuned_v2": finetuned_dir.as_posix(),
        },
        "metrics": {
            "zero_shot": zero_metrics,
            "finetuned_v2": fine_metrics,
        },
        "comparison": build_comparison(zero_metrics, fine_metrics),
    }
    manifest["artifact_hashes"] = collect_artifact_hashes(out_dir)

    manifest_path = out_dir / "manifest.json"
    report_path = out_dir / "baseline_freeze_report.md"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(render_report(manifest), encoding="utf-8")
    return manifest_path, report_path


def parse_args():
    parser = argparse.ArgumentParser(description="Freeze Milestone 0 baseline artifacts into a manifest and report.")
    parser.add_argument("--zero-shot-dir", required=True)
    parser.add_argument("--finetuned-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--zero-shot-config", default=str(DEFAULT_ZERO_SHOT_CONFIG))
    parser.add_argument("--finetuned-config", default=str(DEFAULT_FINETUNED_CONFIG))
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--mode", default="final")
    return parser.parse_args()


def main():
    args = parse_args()
    manifest_path, report_path = freeze_baseline(
        zero_shot_dir=args.zero_shot_dir,
        finetuned_dir=args.finetuned_dir,
        out_dir=args.out_dir,
        zero_shot_config=args.zero_shot_config,
        finetuned_config=args.finetuned_config,
        data_dir=args.data_dir,
        mode=args.mode,
    )
    print(f"Exported manifest: {manifest_path}")
    print(f"Exported report: {report_path}")


if __name__ == "__main__":
    main()
