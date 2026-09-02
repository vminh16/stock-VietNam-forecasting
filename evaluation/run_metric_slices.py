import argparse
import gzip
import io
import json
import os
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
from evaluation.research.metrics import (
    ORIGIN_COLUMNS,
    TOP_K,
    aggregate_dates,
    summarize_metrics,
)
from evaluation.research.slices import SLICE_KEYS

SCHEMA_VERSION = "m2_6_metric_slices_v1"
SLICE_SCHEMA_VERSION = "m2_6_origin_slices_v1"


@dataclass(frozen=True)
class MetricSliceConfig:
    schema_version: str
    slices_path: Path
    slices_manifest_path: Path
    input_dirs: tuple
    output_dir: Path
    report_dir: Path
    candidates: tuple
    slice_keys: tuple
    minimum_cross_section: int


def load_metric_slice_config(path):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    config = MetricSliceConfig(
        schema_version=str(raw["schema_version"]),
        slices_path=Path(raw["slices_path"]),
        slices_manifest_path=Path(raw["slices_manifest_path"]),
        input_dirs=tuple(Path(value) for value in raw["input_dirs"]),
        output_dir=Path(raw["output_dir"]),
        report_dir=Path(raw["report_dir"]),
        candidates=tuple(str(value) for value in raw["candidates"]),
        slice_keys=tuple(str(value) for value in raw["slice_keys"]),
        minimum_cross_section=int(raw["minimum_cross_section"]),
    )
    if config.schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {config.schema_version}")
    if not config.candidates:
        raise ValueError("No candidate is registered")
    unknown = set(config.slice_keys) - set(SLICE_KEYS)
    if unknown:
        raise ValueError(f"Unregistered slice keys: {sorted(unknown)}")
    if config.minimum_cross_section < TOP_K:
        raise ValueError(
            f"minimum_cross_section below {TOP_K} would leave HitRate@Top10 undefined"
        )
    return config


def _git_value(*args):
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def load_slices(config):
    slices_hash = sha256_file(config.slices_path)
    manifest = json.loads(config.slices_manifest_path.read_text(encoding="utf-8"))
    if manifest["schema_version"] != SLICE_SCHEMA_VERSION:
        raise ValueError("Slice manifest schema version mismatch")
    if manifest["slices_sha256"] != slices_hash:
        raise ValueError("Slice file does not match its manifest hash")
    frame = pd.read_csv(config.slices_path)
    frame["origin_date"] = pd.to_datetime(frame["origin_date"])
    if frame["origin_id"].duplicated().any():
        raise ValueError("Duplicate origin_id in the slice table")
    return frame, slices_hash, manifest


def _origin_path(config, candidate_id):
    name = f"{candidate_id}_per_origin_metrics.csv.gz"
    for directory in config.input_dirs:
        path = directory / name
        if path.exists():
            return path
    raise ValueError(f"No per-origin metrics found for candidate: {candidate_id}")


def load_candidate_origins(config, candidate_id):
    path = _origin_path(config, candidate_id)
    frame = pd.read_csv(path)
    if list(frame.columns) != ORIGIN_COLUMNS:
        raise ValueError(f"{path.name} does not match the M2.2 origin contract")
    frame["origin_date"] = pd.to_datetime(frame["origin_date"])
    if frame["origin_id"].duplicated().any():
        raise ValueError(f"Duplicate origin_id in {path.name}")
    return frame, path


def attach_slices(origins, slices, slice_keys):
    """Join slice labels onto per-origin metrics without dropping an origin."""
    labels = slices[["origin_id", "security_id", "origin_date", *slice_keys]]
    merged = origins.merge(
        labels, on="origin_id", how="left", suffixes=("", "_slice"), validate="one_to_one"
    )
    for key in slice_keys:
        if merged[key].isna().any():
            raise ValueError(f"An evaluated origin has no {key} label")
    if not merged["security_id"].equals(merged["security_id_slice"]):
        raise ValueError("Slice table disagrees with the evaluated security_id")
    if not merged["origin_date"].equals(merged["origin_date_slice"]):
        raise ValueError("Slice table disagrees with the evaluated origin_date")
    return merged.drop(columns=["security_id_slice", "origin_date_slice"])


def slice_dates(block, minimum_cross_section):
    """Recompute per-date metrics inside one slice, dropping thin cross-sections."""
    counts = block.groupby(["fold_id", "origin_date"])["origin_id"].transform("size")
    kept = block[counts >= minimum_cross_section]
    dropped = int(
        block.loc[counts < minimum_cross_section]
        .groupby(["fold_id", "origin_date"])
        .ngroups
    )
    if kept.empty:
        raise ValueError("Every date in this slice is below the minimum cross-section")
    return aggregate_dates(kept[ORIGIN_COLUMNS].reset_index(drop=True)), dropped


def _write_metrics(path, frame):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    output = frame.copy()
    output["origin_date"] = pd.to_datetime(output["origin_date"]).dt.strftime("%Y-%m-%d")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                output.to_csv(text, index=False, lineterminator="\n")
    os.replace(temporary, path)
    return path


def slice_candidate_id(candidate_id, slice_key, slice_value):
    return f"{candidate_id}__{slice_key}_{slice_value}"


def _render_report(config, summary, slices_hash, dropped_total):
    lines = [
        "| candidate | slice | DA | MW-DA | RankIC | HitRate@Top10 | CRPS | "
        "coverage | dates | origins |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| `{row['candidate_id']}` | `{row['slice_key']}={row['slice_value']}` | "
        f"{row['DA']:.4f} | {row['MW-DA']:.4f} | {row['RankIC']:.4f} | "
        f"{row['HitRate@Top10']:.4f} | {row['CRPS']:.6f} | {row['coverage']:.4f} | "
        f"{row['valid_dates']:,} | {row['origin_rows']:,} |"
        for row in summary[summary["scope"] == "pooled"].to_dict("records")
    )
    return f"""# M2.6 Metric Slice Report

## Decision

This unit recomputes the locked metrics inside pre-registered slices of the
frozen origins. It runs no model: every number comes from per-origin metric
files a previous unit already wrote. It names no winner; paired date-block
intervals over these slice files carry any comparison.

## Registered Setup

- Slice table SHA256: `{slices_hash}`
- Candidates: {", ".join(f"`{value}`" for value in config.candidates)}
- Slice keys: {", ".join(f"`{value}`" for value in config.slice_keys)}
- Minimum cross-section per date inside a slice: {config.minimum_cross_section}
- Dates dropped for a thin cross-section, summed over slices: {dropped_total}

## Pooled Metrics By Slice

{chr(10).join(lines)}

## Reading These Slices

- `RankIC` inside a slice is the cross-sectional correlation among that slice's
  symbols only. A model can rank the liquid tier well and the illiquid tier
  badly while its whole-market `RankIC` looks flat, so the slice rows answer a
  different question from the pooled report and neither replaces the other.
- `HitRate@Top10` inside a slice selects the top ten symbols of that slice, not
  the top ten of the market.
- A date whose slice holds fewer than {config.minimum_cross_section} origins is
  dropped from that slice only, so slices can carry different date counts. A
  paired comparison between two candidates on the same slice stays valid because
  both candidates share the same origins and therefore the same dropped dates.
- Slice labels were fixed by `evaluation/run_origin_slices.py` before any metric
  here was computed, and the symbol groups read no price or result at all.

## Guardrails

- Per-date files are written under the same
  `{{candidate}}_per_date_metrics.csv.gz` convention, so
  `evaluation/run_paired_comparison.py` consumes them unchanged.
- Slicing multiplies the number of comparisons. SPEC section 8.7 registers the
  slice keys and section 8.8 requires a multiplicity correction before any slice
  result is read as evidence; an unregistered slice search is data snooping.
- The 2026 lockbox remains closed.
"""


def run_metric_slices(config_path, command=None):
    config_path = Path(config_path)
    config = load_metric_slice_config(config_path)
    slices, slices_hash, slices_manifest = load_slices(config)

    summary_rows = []
    artifact_hashes = {}
    input_hashes = {}
    dropped_total = 0
    for candidate_id in config.candidates:
        origins, origin_path = load_candidate_origins(config, candidate_id)
        input_hashes[origin_path.name] = sha256_file(origin_path)
        labelled = attach_slices(origins, slices, config.slice_keys)
        for slice_key in config.slice_keys:
            for slice_value, block in labelled.groupby(slice_key, sort=True):
                dates, dropped = slice_dates(block, config.minimum_cross_section)
                dropped_total += dropped
                sliced_id = slice_candidate_id(candidate_id, slice_key, slice_value)
                written = _write_metrics(
                    config.output_dir / f"{sliced_id}_per_date_metrics.csv.gz", dates
                )
                artifact_hashes[written.name] = sha256_file(written)
                common = {
                    "candidate_id": candidate_id,
                    "slice_key": slice_key,
                    "slice_value": slice_value,
                    "sliced_candidate_id": sliced_id,
                    "dropped_dates": dropped,
                }
                for fold_id, fold in dates.groupby("fold_id", sort=True):
                    summary_rows.append(
                        {**common, "scope": fold_id, **summarize_metrics(fold)}
                    )
                summary_rows.append(
                    {**common, "scope": "pooled", **summarize_metrics(dates)}
                )

    summary = pd.DataFrame(summary_rows)
    config.report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = config.report_dir / "slice_metric_summary.csv"
    summary.to_csv(summary_path, index=False, lineterminator="\n")
    report_path = config.report_dir / "metric_slice_report.md"
    report_path.write_text(
        _render_report(config, summary, slices_hash, dropped_total), encoding="utf-8"
    )
    artifact_hashes[summary_path.name] = sha256_file(summary_path)
    artifact_hashes[report_path.name] = sha256_file(report_path)

    if command is None:
        command = (
            "python evaluation/run_metric_slices.py --config "
            f"{config_path.as_posix()}"
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "config_path": config_path.as_posix(),
        "config_sha256": sha256_file(config_path),
        "slices_path": config.slices_path.as_posix(),
        "slices_sha256": slices_hash,
        "dataset_fingerprint": slices_manifest["dataset_fingerprint"],
        "registry_sha256": slices_manifest["registry_sha256"],
        "candidates": list(config.candidates),
        "slice_keys": list(config.slice_keys),
        "minimum_cross_section": config.minimum_cross_section,
        "dropped_dates_total": dropped_total,
        "output_dir": config.output_dir.as_posix(),
        "input_dirs": [directory.as_posix() for directory in config.input_dirs],
        "input_hashes": input_hashes,
        "model_inference": False,
        "training": False,
        "lockbox_opened": False,
        "command": command,
        "code_revision": _git_value("rev-parse", "HEAD"),
        "worktree_dirty": bool(_git_value("status", "--porcelain")),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_hashes": artifact_hashes,
    }
    manifest_path = config.report_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Recompute M2 metrics inside slices")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    command = " ".join([sys.executable, __file__, "--config", str(args.config)])
    manifest, summary = run_metric_slices(args.config, command=command)

    for row in summary[summary["scope"] == "pooled"].to_dict("records"):
        print(
            f"{row['sliced_candidate_id']}: DA={row['DA']:.4f} "
            f"MW-DA={row['MW-DA']:.4f} RankIC={row['RankIC']:.4f} "
            f"CRPS={row['CRPS']:.6f} coverage={row['coverage']:.4f} "
            f"dates={row['valid_dates']:,}"
        )
    print(f"Dropped dates: {manifest['dropped_dates_total']}")


if __name__ == "__main__":
    main()
