import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.crawl import sha256_file
from evaluation.research.bootstrap import (
    COMPARISON_COLUMNS,
    POOLED_METRICS,
    compare_candidates,
)

SCHEMA_VERSION = "m2_3_paired_inference_v1"
SCOPE_COLUMNS = ["scope", *COMPARISON_COLUMNS]


@dataclass(frozen=True)
class PairedInferenceConfig:
    schema_version: str
    input_dir: Path
    report_dir: Path
    comparisons: tuple
    method: str
    mean_block_dates: int
    replicates: int
    confidence: float
    seed: int


def load_paired_config(path):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    bootstrap = raw["bootstrap"]
    config = PairedInferenceConfig(
        schema_version=str(raw["schema_version"]),
        input_dir=Path(raw["input_dir"]),
        report_dir=Path(raw["report_dir"]),
        comparisons=tuple(
            (str(item["left"]), str(item["right"])) for item in raw["comparisons"]
        ),
        method=str(bootstrap["method"]),
        mean_block_dates=int(bootstrap["mean_block_dates"]),
        replicates=int(bootstrap["replicates"]),
        confidence=float(bootstrap["confidence"]),
        seed=int(bootstrap["seed"]),
    )
    if config.schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {config.schema_version}")
    if config.method != "stationary":
        raise ValueError("M2.3 inference must use the stationary block bootstrap")
    if config.replicates < 1000:
        raise ValueError("Registered inference needs at least 1000 replicates")
    if not config.comparisons:
        raise ValueError("No comparison is registered")
    return config


def _git_value(*args):
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _candidate_path(config, candidate_id):
    return config.input_dir / f"{candidate_id}_per_date_metrics.csv.gz"


def load_candidate_dates(config, candidate_id):
    path = _candidate_path(config, candidate_id)
    frame = pd.read_csv(path)
    frame["origin_date"] = pd.to_datetime(frame["origin_date"])
    return frame


def compare_scopes(config, left, right, left_id, right_id):
    frames = [
        compare_candidates(
            left,
            right,
            left_id,
            right_id,
            mean_block=config.mean_block_dates,
            replicates=config.replicates,
            seed=config.seed,
            confidence=config.confidence,
        ).assign(scope="pooled")
    ]
    for fold_id in sorted(set(left["fold_id"])):
        frames.append(
            compare_candidates(
                left[left["fold_id"] == fold_id],
                right[right["fold_id"] == fold_id],
                left_id,
                right_id,
                mean_block=config.mean_block_dates,
                replicates=config.replicates,
                seed=config.seed,
                confidence=config.confidence,
            ).assign(scope=fold_id)
        )
    return pd.concat(frames, ignore_index=True)[SCOPE_COLUMNS]


def _render_report(config, comparisons):
    sections = []
    for (left_id, right_id), pair in comparisons.groupby(
        ["left_id", "right_id"], sort=True
    ):
        pooled = pair[pair["scope"] == "pooled"]
        lines = [
            f"### `{left_id}` versus `{right_id}`",
            "",
            f"| metric | {left_id} | {right_id} | difference | "
            f"{config.confidence:.0%} CI | verdict |",
            "|---|---:|---:|---:|---|---|",
        ]
        lines.extend(
            f"| {row['metric']} | {row['left_estimate']:.4f} | "
            f"{row['right_estimate']:.4f} | {row['difference']:+.4f} | "
            f"[{row['ci_low']:+.4f}, {row['ci_high']:+.4f}] | {row['verdict']} |"
            for row in pooled.to_dict("records")
        )
        sections.append("\n".join(lines))
    body = "\n\n".join(sections)
    dates = int(comparisons.loc[comparisons["scope"] == "pooled", "n_paired_dates"].max())

    pooled_all = comparisons[comparisons["scope"] == "pooled"]
    resolution = pooled_all.assign(
        half_width=(pooled_all["ci_high"] - pooled_all["ci_low"]) / 2.0
    )
    resolution_lines = [
        "| metric | paired 95% CI half-width | smallest resolvable difference |",
        "|---|---:|---|",
    ]
    resolution_lines.extend(
        f"| {row['metric']} | {row['half_width']:.4f} | a true difference below "
        f"{row['half_width']:.4f} cannot be separated from zero here |"
        for row in resolution.drop_duplicates("metric").to_dict("records")
    )
    resolution_table = "\n".join(resolution_lines)

    return f"""# M2.3 Paired Date-Block Inference Report

## Decision

This report replaces the diagnostic paired t-test with the canonical paired
stationary date-block bootstrap required by SPEC section 8.5. It currently
compares the two causal naive references only; no Kronos candidate has been
evaluated yet, so no model promotion decision follows from it.

## Registered Inference

- Method: stationary block bootstrap over forecast dates
- Expected block length: {config.mean_block_dates} dates
- Replicates: {config.replicates:,}
- Confidence: {config.confidence:.0%} percentile interval
- Seed: {config.seed}
- Paired dates (pooled): {dates:,}
- Metrics: {", ".join(POOLED_METRICS)}

{body}

## Design Resolution

{resolution_table}

Read these widths as the resolution of a comparison between two weakly
correlated candidates on {dates:,} paired dates. Paired difference variance falls
as the two candidates make more correlated predictions, so a Kronos-small versus
Kronos-base comparison should resolve smaller differences than this pair, while a
model versus naive comparison behaves closer to it. Fold-level intervals are
roughly twice as wide because each fold holds about a quarter of the dates.

## Reading These Intervals

- Each replicate resamples contiguous blocks of forecast dates and keeps the
  whole cross-section of that date, so overlapping horizons and market-wide
  dependence stay inside the resampled unit.
- Both candidates are evaluated on one shared resampled index, so the interval
  describes the paired difference, not two independent samples.
- Ratio metrics are recomputed from resampled numerator and denominator sums
  inside every replicate; daily ratios are never averaged.
- `verdict` states only the sign of the difference. Higher is better for DA,
  MW-DA, RankIC, and HitRate@Top10; lower is better for CRPS and
  interval_width; coverage is judged against its nominal 0.80 target.
- An interval containing zero means insufficient evidence, never equivalence.

## Guardrails

- Per-fold rows accompany the pooled row so a single regime cannot carry a
  conclusion on its own.
- No multiple-comparison correction is applied yet. Once several model
  candidates enter, SPEC section 8.6 requires a Model Confidence Set or an
  equivalent bootstrap correction before any winner is named.
- The 2026 lockbox remains closed.

## Next Step

M2.4 adds the zero-shot Kronos runner on the same origins and reuses this
inference layer to compare Kronos against these references.
"""


def run_paired_comparison(config_path, command=None):
    config_path = Path(config_path)
    config = load_paired_config(config_path)

    frames = []
    input_hashes = {}
    for left_id, right_id in config.comparisons:
        left = load_candidate_dates(config, left_id)
        right = load_candidate_dates(config, right_id)
        frames.append(compare_scopes(config, left, right, left_id, right_id))
        for candidate_id in (left_id, right_id):
            path = _candidate_path(config, candidate_id)
            input_hashes[path.name] = sha256_file(path)

    comparisons = pd.concat(frames, ignore_index=True)
    config.report_dir.mkdir(parents=True, exist_ok=True)
    comparisons_path = config.report_dir / "paired_comparisons.csv"
    comparisons.to_csv(comparisons_path, index=False, lineterminator="\n")
    report_path = config.report_dir / "paired_inference_report.md"
    report_path.write_text(_render_report(config, comparisons), encoding="utf-8")

    if command is None:
        command = (
            "python evaluation/run_paired_comparison.py --config "
            f"{config_path.as_posix()}"
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "config_path": config_path.as_posix(),
        "config_sha256": sha256_file(config_path),
        "comparisons": [
            {"left": left_id, "right": right_id}
            for left_id, right_id in config.comparisons
        ],
        "metrics": list(POOLED_METRICS),
        "bootstrap": {
            "method": config.method,
            "mean_block_dates": config.mean_block_dates,
            "replicates": config.replicates,
            "confidence": config.confidence,
            "seed": config.seed,
        },
        "model_inference": False,
        "lockbox_opened": False,
        "input_hashes": input_hashes,
        "command": command,
        "code_revision": _git_value("rev-parse", "HEAD"),
        "worktree_dirty": bool(_git_value("status", "--porcelain")),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_hashes": {
            "paired_comparisons.csv": sha256_file(comparisons_path),
            "paired_inference_report.md": sha256_file(report_path),
        },
    }
    manifest_path = config.report_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest, comparisons


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run M2.3 paired date-block inference")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    command = " ".join([sys.executable, __file__, "--config", str(args.config)])
    manifest, comparisons = run_paired_comparison(args.config, command=command)

    pooled = comparisons[comparisons["scope"] == "pooled"]
    for row in pooled.to_dict("records"):
        print(
            f"{row['left_id']} vs {row['right_id']} {row['metric']}: "
            f"{row['difference']:+.4f} "
            f"[{row['ci_low']:+.4f}, {row['ci_high']:+.4f}] {row['verdict']}"
        )
    print(f"Report: {manifest['artifact_hashes']['paired_inference_report.md']}")


if __name__ == "__main__":
    main()
