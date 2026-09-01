import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.crawl import sha256_file
from evaluation.research.kronos_runner import (
    ArmSpec,
    build_batch,
    load_predictor,
    run_batch,
)
from evaluation.research.metrics import (
    FORECAST_COLUMNS,
    aggregate_dates,
    summarize_metrics,
    summarize_origins,
)
from evaluation.research.origins import OriginRegistryConfig, read_symbol_frame

SCHEMA_VERSION = "m2_5_zero_shot_screen_v1"
REGISTRY_SCHEMA_VERSION = "m2_1_origin_registry_v1"
LOW_VRAM_BYTES = 4.4 * 1024**3
LOW_VRAM_EFFECTIVE_BATCH = 64


@dataclass(frozen=True)
class ScreenConfig:
    schema_version: str
    dataset_id: str
    dataset_dir: Path
    dataset_manifest_path: Path
    registry_path: Path
    registry_manifest_path: Path
    tokenizer_path: Path
    output_dir: Path
    report_dir: Path
    horizon: int
    date_stride: int
    sample_count: int
    seed: int
    temperature: float
    top_k: int
    top_p: float
    max_context: int
    clip: float
    batch_size: int
    arms: tuple


def load_screen_config(path):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    sampling = raw["sampling"]
    runtime = raw["runtime"]
    arms = tuple(
        ArmSpec(
            arm_id=str(item["arm_id"]),
            model_path=Path(item["model_path"]),
            lookback=int(item["lookback"]),
            normalizer_lookback=int(item["normalizer_lookback"]),
        )
        for item in raw["arms"]
    )
    config = ScreenConfig(
        schema_version=str(raw["schema_version"]),
        dataset_id=str(raw["dataset_id"]),
        dataset_dir=Path(raw["dataset_dir"]),
        dataset_manifest_path=Path(raw["dataset_manifest_path"]),
        registry_path=Path(raw["registry_path"]),
        registry_manifest_path=Path(raw["registry_manifest_path"]),
        tokenizer_path=Path(raw["tokenizer_path"]),
        output_dir=Path(raw["output_dir"]),
        report_dir=Path(raw["report_dir"]),
        horizon=int(raw["horizon"]),
        date_stride=int(raw["date_stride"]),
        sample_count=int(sampling["sample_count"]),
        seed=int(sampling["seed"]),
        temperature=float(sampling["temperature"]),
        top_k=int(sampling["top_k"]),
        top_p=float(sampling["top_p"]),
        max_context=int(runtime["max_context"]),
        clip=float(runtime["clip"]),
        batch_size=int(runtime["batch_size"]),
        arms=arms,
    )
    if config.schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {config.schema_version}")
    if config.horizon != 5:
        raise ValueError("M2.5 horizon must be 5")
    if config.sample_count < 2:
        raise ValueError("sample_count must allow ensemble statistics")
    if config.date_stride < 1 or config.batch_size < 1:
        raise ValueError("date_stride and batch_size must be positive")
    if len({arm.arm_id for arm in config.arms}) != len(config.arms):
        raise ValueError("Arm identifiers must be unique")
    for arm in config.arms:
        arm.validate()
        if arm.lookback > config.max_context:
            raise ValueError(f"{arm.arm_id}: lookback exceeds max_context")
    return config


def _git_value(*args):
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _origin_seed(seed, arm_id, origin_date):
    payload = f"{seed}|{arm_id}|{pd.Timestamp(origin_date):%Y-%m-%d}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def _model_hash(arm):
    return sha256_file(Path(arm.model_path) / "model.safetensors")


def selection_hash(registry):
    """Hash the exact evaluated origin set so a subsample never reuses another."""
    joined = "|".join(sorted(registry["origin_id"].astype(str)))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def arm_cache_key(config, arm, registry_hash, selection):
    payload = json.dumps(
        {
            "schema_version": config.schema_version,
            "registry_sha256": registry_hash,
            "selection_sha256": selection,
            "date_stride": config.date_stride,
            "horizon": config.horizon,
            "sample_count": config.sample_count,
            "seed": config.seed,
            "temperature": config.temperature,
            "top_k": config.top_k,
            "top_p": config.top_p,
            "max_context": config.max_context,
            "clip": config.clip,
            "arm_id": arm.arm_id,
            "lookback": arm.lookback,
            "normalizer_lookback": arm.normalizer_lookback,
            "model_sha256": _model_hash(arm),
            "tokenizer_sha256": sha256_file(
                config.tokenizer_path / "model.safetensors"
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_inputs(config, max_dates=None):
    registry_hash = sha256_file(config.registry_path)
    registry_manifest = json.loads(
        config.registry_manifest_path.read_text(encoding="utf-8")
    )
    if registry_manifest["registry_sha256"] != registry_hash:
        raise ValueError("Registry file does not match its manifest hash")

    registry = pd.read_csv(config.registry_path)
    registry["origin_date"] = pd.to_datetime(registry["origin_date"])
    dates = np.sort(registry["origin_date"].unique())[:: config.date_stride]
    if max_dates is not None:
        dates = dates[:max_dates]
    registry = registry[registry["origin_date"].isin(dates)].reset_index(drop=True)

    dataset_manifest = json.loads(
        config.dataset_manifest_path.read_text(encoding="utf-8")
    )
    source_config = OriginRegistryConfig(
        schema_version=REGISTRY_SCHEMA_VERSION,
        dataset_id=config.dataset_id,
        dataset_dir=config.dataset_dir,
        dataset_manifest_path=config.dataset_manifest_path,
        universe_path=Path("."),
        registry_path=config.registry_path,
        report_dir=config.report_dir,
        lookbacks=(63, 126),
        horizon=config.horizon,
        minimum_cross_section=10,
        lockbox_start=datetime(2026, 1, 1).date(),
        folds=(),
    )
    frames = {}
    for symbol, security_id in (
        registry[["symbol", "security_id"]].drop_duplicates().itertuples(index=False)
    ):
        frames[symbol] = read_symbol_frame(
            source_config, dataset_manifest, symbol, security_id
        )
    return registry, frames, registry_hash, registry_manifest, dataset_manifest


def _forecast_frame(rows, paths, actual, horizon, sample_count):
    block = horizon * sample_count
    steps = np.tile(np.repeat(np.arange(1, horizon + 1), sample_count), len(rows))
    samples = np.tile(np.arange(sample_count), len(rows) * horizon)
    return pd.DataFrame(
        {
            "fold_id": np.repeat(rows["fold_id"].to_numpy(), block),
            "origin_id": np.repeat(rows["origin_id"].to_numpy(), block),
            "security_id": np.repeat(rows["security_id"].to_numpy(), block),
            "origin_date": np.repeat(rows["origin_date"].to_numpy(), block),
            "sample_id": samples,
            "horizon_step": steps,
            "predicted_return": paths.transpose(0, 2, 1).reshape(-1),
            "actual_return": np.repeat(actual, sample_count, axis=1).reshape(-1),
        },
        columns=FORECAST_COLUMNS,
    )


def evaluate_arm(config, arm, registry, frames, device, progress=None):
    predictor = load_predictor(
        config.tokenizer_path,
        arm.model_path,
        device=device,
        max_context=config.max_context,
        clip=config.clip,
    )
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    started = time.perf_counter()
    origin_frames = []
    processed = 0
    for (_, origin_date), day in registry.groupby(
        ["fold_id", "origin_date"], sort=True
    ):
        day = day.reset_index(drop=True)
        day_paths = []
        for start in range(0, len(day), config.batch_size):
            chunk = day.iloc[start : start + config.batch_size]
            batch = build_batch(frames, chunk, arm, clip=config.clip)
            day_paths.append(
                (
                    chunk,
                    run_batch(
                        predictor,
                        batch,
                        horizon=config.horizon,
                        sample_count=config.sample_count,
                        seed=_origin_seed(config.seed, arm.arm_id, origin_date) + start,
                        temperature=config.temperature,
                        top_k=config.top_k,
                        top_p=config.top_p,
                        device=device,
                    ),
                    batch["actual_return"],
                )
            )
            processed += len(chunk)

        forecasts = pd.concat(
            [
                _forecast_frame(
                    chunk, paths, actual, config.horizon, config.sample_count
                )
                for chunk, paths, actual in day_paths
            ],
            ignore_index=True,
        )
        origin_frames.append(summarize_origins(forecasts))
        if progress is not None:
            progress(arm.arm_id, processed, time.perf_counter() - started)

    elapsed = time.perf_counter() - started
    peak_vram = (
        float(torch.cuda.max_memory_allocated()) / 1024**3
        if torch.cuda.is_available()
        else 0.0
    )
    del predictor
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    dates = aggregate_dates(pd.concat(origin_frames, ignore_index=True))
    runtime = {
        "arm_id": arm.arm_id,
        "lookback": arm.lookback,
        "normalizer_lookback": arm.normalizer_lookback,
        "origins": processed,
        "elapsed_seconds": elapsed,
        "origins_per_second": processed / elapsed if elapsed > 0 else float("nan"),
        "peak_vram_gb": peak_vram,
    }
    return dates, runtime


def _write_dates(path, dates):
    path.parent.mkdir(parents=True, exist_ok=True)
    output = dates.copy()
    output["origin_date"] = pd.to_datetime(output["origin_date"]).dt.strftime("%Y-%m-%d")
    output.to_csv(path, index=False, compression="gzip")
    return path


def _resume_arm(config, arm, cache_key):
    """Return a completed arm's dates and runtime when its cache key still matches."""
    path = config.output_dir / f"{arm.arm_id}_per_date_metrics.csv.gz"
    sidecar = config.output_dir / f"{arm.arm_id}_cache.json"
    if not path.exists() or not sidecar.exists():
        return None
    record = json.loads(sidecar.read_text(encoding="utf-8"))
    if record.get("cache_key") != cache_key:
        return None
    dates = pd.read_csv(path)
    dates["origin_date"] = pd.to_datetime(dates["origin_date"])
    return dates, record["runtime"]


def _record_arm(config, arm, cache_key, runtime):
    sidecar = config.output_dir / f"{arm.arm_id}_cache.json"
    sidecar.write_text(
        json.dumps({"cache_key": cache_key, "runtime": runtime}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _render_report(config, summary, runtimes, registry, registry_hash, smoke):
    pooled = summary[summary["scope"] == "pooled"]
    lines = [
        "| arm | L | normalizer | DA | MW-DA | RankIC | HitRate@Top10 | CRPS | "
        "coverage | width |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    arms = {arm.arm_id: arm for arm in config.arms}
    lines.extend(
        f"| `{row['arm_id']}` | {arms[row['arm_id']].lookback} | "
        f"{arms[row['arm_id']].normalizer_lookback} | {row['DA']:.4f} | "
        f"{row['MW-DA']:.4f} | {row['RankIC']:.4f} | {row['HitRate@Top10']:.4f} | "
        f"{row['CRPS']:.6f} | {row['coverage']:.4f} | {row['interval_width']:.6f} |"
        for row in pooled.to_dict("records")
    )
    runtime_lines = [
        "| arm | origins | seconds | origins/s | peak VRAM GB |",
        "|---|---:|---:|---:|---:|",
    ]
    runtime_lines.extend(
        f"| `{row['arm_id']}` | {row['origins']:,} | {row['elapsed_seconds']:.1f} | "
        f"{row['origins_per_second']:.2f} | {row['peak_vram_gb']:.2f} |"
        for row in runtimes.to_dict("records")
    )
    heading = "Smoke Run" if smoke else "Screen"

    return f"""# M2.5 Zero-Shot Kronos {heading} Report

## Decision

{"This is an engineering smoke run. It validates the pipeline end to end and measures throughput; it must not be read as model evidence." if smoke else "This is a screening run on a strided subsample of the frozen common origins. It ranks candidates for a later confirmation run; it is not a promotion decision."}
No model was trained. The 2026 lockbox remains closed.

## Registered Setup

- Registry SHA256: `{registry_hash}`
- Origins per arm: {len(registry):,}
- Evaluation dates: {registry['origin_date'].nunique():,}
- Symbols: {registry['security_id'].nunique():,}
- Date stride: {config.date_stride}
- Sample paths per origin: {config.sample_count}
- Sampling: `T={config.temperature}`, `top_p={config.top_p}`, `top_k={config.top_k}`,
  seed {config.seed}
- Batch size: {config.batch_size} origins, effective
  {config.batch_size * config.sample_count} sampled sequences

Sampling temperature follows the Kronos authors' published price-series setting
rather than the `T=0.7` used by the frozen M0 baseline, so these numbers compare
arms against each other and not against the M0 report.

## Metrics

{chr(10).join(lines)}

## Runtime

{chr(10).join(runtime_lines)}

## How To Read The Arms

- `small_l63` versus `small_l126` mixes context length with the normalization
  scale, because `L` sets both.
- `small_l63_norm126` holds the {config.arms[0].lookback}-session rows but borrows
  the 126-session mean and scale, so `small_l63` versus `small_l63_norm126`
  isolates the normalizer and `small_l63_norm126` versus `small_l126` isolates
  context length.
- `base_*` arms answer whether the 102.3M backbone earns its cost over the 24.7M
  one on this population.
- Point estimates alone decide nothing. Paired date-block intervals come from
  `evaluation/run_paired_comparison.py` over the same per-date metric files.

## Guardrails

- Every arm runs on identical origins, identical targets, and a per-date seed
  shared by construction across arms.
- Normalization is lookback-only; no future observation enters an input window.
- Kronos code is unmodified; sampling reuses the frozen `generate_raw` path.
"""


def run_screen(config_path, command=None, max_dates=None, smoke=False):
    config_path = Path(config_path)
    config = load_screen_config(config_path)
    registry, frames, registry_hash, registry_manifest, dataset_manifest = load_inputs(
        config, max_dates=max_dates
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    effective = config.batch_size * config.sample_count
    if device == "cuda":
        total = torch.cuda.get_device_properties(0).total_memory
        if total <= LOW_VRAM_BYTES and effective >= LOW_VRAM_EFFECTIVE_BATCH:
            print(
                f"WARNING: effective batch {effective} on a "
                f"{total / 1024**3:.1f} GB GPU may page through system RAM"
            )

    def progress(arm_id, processed, elapsed):
        rate = processed / elapsed if elapsed > 0 else 0.0
        print(
            f"  {arm_id}: {processed:,} origins in {elapsed:.0f}s ({rate:.2f}/s)",
            flush=True,
        )

    selection = selection_hash(registry)
    summary_rows = []
    runtime_rows = []
    artifact_hashes = {}
    for arm in config.arms:
        cache_key = arm_cache_key(config, arm, registry_hash, selection)
        resumed = _resume_arm(config, arm, cache_key)
        if resumed is not None:
            print(f"Arm {arm.arm_id}: reusing cached result", flush=True)
            dates, runtime = resumed
        else:
            print(f"Arm {arm.arm_id} on {device}", flush=True)
            dates, runtime = evaluate_arm(
                config, arm, registry, frames, device, progress=progress
            )
            _write_dates(
                config.output_dir / f"{arm.arm_id}_per_date_metrics.csv.gz", dates
            )
            _record_arm(config, arm, cache_key, runtime)

        path = config.output_dir / f"{arm.arm_id}_per_date_metrics.csv.gz"
        artifact_hashes[path.name] = sha256_file(path)
        runtime = {**runtime, "cache_key": cache_key}
        runtime_rows.append(runtime)
        for fold_id, fold in dates.groupby("fold_id", sort=True):
            summary_rows.append(
                {"arm_id": arm.arm_id, "scope": fold_id, **summarize_metrics(fold)}
            )
        summary_rows.append(
            {"arm_id": arm.arm_id, "scope": "pooled", **summarize_metrics(dates)}
        )

    summary = pd.DataFrame(summary_rows)
    runtimes = pd.DataFrame(runtime_rows)
    config.report_dir.mkdir(parents=True, exist_ok=True)
    prefix = "smoke_" if smoke else ""
    summary_path = config.report_dir / f"{prefix}metric_summary.csv"
    summary.to_csv(summary_path, index=False, lineterminator="\n")
    runtime_path = config.report_dir / f"{prefix}runtime_summary.csv"
    runtimes.to_csv(runtime_path, index=False, lineterminator="\n")
    report_path = config.report_dir / f"{prefix}zero_shot_screen_report.md"
    report_path.write_text(
        _render_report(config, summary, runtimes, registry, registry_hash, smoke),
        encoding="utf-8",
    )
    artifact_hashes[summary_path.name] = sha256_file(summary_path)
    artifact_hashes[runtime_path.name] = sha256_file(runtime_path)
    artifact_hashes[report_path.name] = sha256_file(report_path)

    if command is None:
        command = (
            "python evaluation/run_zero_shot_screen.py --config "
            f"{config_path.as_posix()}"
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "smoke": smoke,
        "dataset_id": config.dataset_id,
        "config_path": config_path.as_posix(),
        "config_sha256": sha256_file(config_path),
        "registry_sha256": registry_hash,
        "selection_sha256": selection,
        "dataset_fingerprint": registry_manifest["dataset_fingerprint"],
        "device": device,
        "horizon": config.horizon,
        "date_stride": config.date_stride,
        "sample_count": config.sample_count,
        "sampling_seed": config.seed,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "top_k": config.top_k,
        "batch_size": config.batch_size,
        "origins_per_arm": len(registry),
        "evaluation_dates": int(registry["origin_date"].nunique()),
        "symbols": int(registry["security_id"].nunique()),
        "arms": [
            {
                "arm_id": arm.arm_id,
                "model_path": arm.model_path.as_posix(),
                "model_sha256": _model_hash(arm),
                "lookback": arm.lookback,
                "normalizer_lookback": arm.normalizer_lookback,
                "cache_key": arm_cache_key(config, arm, registry_hash, selection),
            }
            for arm in config.arms
        ],
        "tokenizer_path": config.tokenizer_path.as_posix(),
        "tokenizer_sha256": sha256_file(config.tokenizer_path / "model.safetensors"),
        "training": False,
        "lockbox_opened": False,
        "price_adjustment_status": dataset_manifest["price_adjustment_status"],
        "amount_policy": dataset_manifest["amount_policy"],
        "command": command,
        "code_revision": _git_value("rev-parse", "HEAD"),
        "worktree_dirty": bool(_git_value("status", "--porcelain")),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_hashes": artifact_hashes,
    }
    manifest_path = config.report_dir / f"{prefix}manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest, summary, runtimes


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the M2.5 zero-shot Kronos screen")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--max-dates", type=int, default=None)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    command = " ".join(
        [sys.executable, __file__, "--config", str(args.config)]
        + (["--max-dates", str(args.max_dates)] if args.max_dates else [])
        + (["--smoke"] if args.smoke else [])
    )
    manifest, summary, runtimes = run_screen(
        args.config, command=command, max_dates=args.max_dates, smoke=args.smoke
    )

    print(f"Origins per arm: {manifest['origins_per_arm']:,}")
    for row in summary[summary["scope"] == "pooled"].to_dict("records"):
        print(
            f"{row['arm_id']}: DA={row['DA']:.4f} MW-DA={row['MW-DA']:.4f} "
            f"RankIC={row['RankIC']:.4f} CRPS={row['CRPS']:.6f} "
            f"coverage={row['coverage']:.4f}"
        )
    for row in runtimes.to_dict("records"):
        print(
            f"{row['arm_id']}: {row['origins_per_second']:.2f} origins/s, "
            f"peak VRAM {row['peak_vram_gb']:.2f} GB"
        )


if __name__ == "__main__":
    main()
