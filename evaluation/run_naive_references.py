import argparse
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.crawl import sha256_file
from evaluation.research.baselines import (
    BASELINE_IDS,
    RECENT_RETURN_LOOKBACK,
    forecast_baselines,
)
from evaluation.research.metrics import (
    FORECAST_COLUMNS,
    INTERVAL_QUANTILES,
    aggregate_dates,
    summarize_metrics,
    summarize_origins,
)
from evaluation.research.origins import (
    OriginRegistryConfig,
    REGISTRY_COLUMNS,
    read_symbol_frame,
)

SCHEMA_VERSION = "m2_2_naive_references_v1"
REGISTRY_SCHEMA_VERSION = "m2_1_origin_registry_v1"


@dataclass(frozen=True)
class NaiveReferenceConfig:
    schema_version: str
    dataset_id: str
    dataset_dir: Path
    dataset_manifest_path: Path
    registry_path: Path
    registry_manifest_path: Path
    output_dir: Path
    report_dir: Path
    horizon: int
    sample_count: int
    sampling_seed: int
    interval_quantiles: tuple


def load_naive_config(path):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    config = NaiveReferenceConfig(
        schema_version=str(raw["schema_version"]),
        dataset_id=str(raw["dataset_id"]),
        dataset_dir=Path(raw["dataset_dir"]),
        dataset_manifest_path=Path(raw["dataset_manifest_path"]),
        registry_path=Path(raw["registry_path"]),
        registry_manifest_path=Path(raw["registry_manifest_path"]),
        output_dir=Path(raw["output_dir"]),
        report_dir=Path(raw["report_dir"]),
        horizon=int(raw["horizon"]),
        sample_count=int(raw["sample_count"]),
        sampling_seed=int(raw["sampling_seed"]),
        interval_quantiles=tuple(float(value) for value in raw["interval_quantiles"]),
    )
    if config.schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {config.schema_version}")
    if config.horizon != 5:
        raise ValueError("M2.2 horizon must be 5")
    if config.sample_count < 2:
        raise ValueError("sample_count must allow ensemble statistics")
    if config.interval_quantiles != INTERVAL_QUANTILES:
        raise ValueError("M2.2 interval quantiles must be (0.10, 0.90)")
    return config


def _git_value(*args):
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _origin_seed(sampling_seed, origin_id):
    payload = f"{sampling_seed}|{origin_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def load_registry(config):
    registry_hash = sha256_file(config.registry_path)
    registry_manifest = json.loads(
        config.registry_manifest_path.read_text(encoding="utf-8")
    )
    if registry_manifest["schema_version"] != REGISTRY_SCHEMA_VERSION:
        raise ValueError("Registry manifest schema version mismatch")
    if registry_manifest["registry_sha256"] != registry_hash:
        raise ValueError("Registry file does not match its manifest hash")
    if registry_manifest["horizon"] != config.horizon:
        raise ValueError("Registry horizon does not match the naive config")

    registry = pd.read_csv(config.registry_path)
    if list(registry.columns) != REGISTRY_COLUMNS:
        raise ValueError("Registry columns do not match the M2.1 contract")
    if not (registry["schema_version"] == REGISTRY_SCHEMA_VERSION).all():
        raise ValueError("Registry schema version mismatch")
    for column in ("origin_date", "target_start_date", "target_end_date"):
        registry[column] = pd.to_datetime(registry[column])
    return registry, registry_hash, registry_manifest


def load_close_series(config, registry):
    dataset_manifest = json.loads(
        config.dataset_manifest_path.read_text(encoding="utf-8")
    )
    if dataset_manifest["dataset_id"] != config.dataset_id:
        raise ValueError("Dataset ID does not match the naive config")

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

    closes = {}
    identifiers = registry[["symbol", "security_id"]].drop_duplicates()
    for symbol, security_id in identifiers.itertuples(index=False):
        frame = read_symbol_frame(source_config, dataset_manifest, symbol, security_id)
        close = frame["close"].to_numpy(dtype=np.float64)
        if not np.isfinite(close).all() or (close <= 0).any():
            raise ValueError(f"Curated close series is not positive: {symbol}")
        dates = frame["timestamps"].dt.normalize().to_numpy()
        rows = registry.loc[registry["symbol"] == symbol]
        offsets = rows["row_origin"].to_numpy(dtype=np.int64)
        if not np.array_equal(
            dates[offsets], rows["origin_date"].to_numpy(dtype="datetime64[ns]")
        ):
            raise ValueError(f"Registry origin rows drifted from curated data: {symbol}")
        closes[symbol] = close
    return closes, dataset_manifest


def _date_forecasts(rows, closes, config, candidate_id):
    predicted = np.empty((len(rows), config.sample_count, config.horizon))
    actual = np.empty((len(rows), config.horizon))
    for position, row in enumerate(rows.itertuples(index=False)):
        close = closes[row.symbol]
        history = close[row.row_origin - RECENT_RETURN_LOOKBACK + 1 : row.row_origin + 1]
        future = close[row.row_target_start : row.row_target_end + 1]
        if history.size != RECENT_RETURN_LOOKBACK or future.size != config.horizon:
            raise ValueError(f"Registry offsets are out of range: {row.origin_id}")
        paths = forecast_baselines(
            history,
            horizon=config.horizon,
            sample_count=config.sample_count,
            seed=_origin_seed(config.sampling_seed, row.origin_id),
        )
        predicted[position] = paths[candidate_id]
        actual[position] = future / close[row.row_origin] - 1.0

    steps = np.tile(
        np.repeat(np.arange(1, config.horizon + 1), config.sample_count), len(rows)
    )
    samples = np.tile(np.arange(config.sample_count), len(rows) * config.horizon)
    block = config.horizon * config.sample_count
    return pd.DataFrame(
        {
            "fold_id": np.repeat(rows["fold_id"].to_numpy(), block),
            "origin_id": np.repeat(rows["origin_id"].to_numpy(), block),
            "security_id": np.repeat(rows["security_id"].to_numpy(), block),
            "origin_date": np.repeat(rows["origin_date"].to_numpy(), block),
            "sample_id": samples,
            "horizon_step": steps,
            "predicted_return": predicted.transpose(0, 2, 1).reshape(-1),
            "actual_return": np.repeat(actual, config.sample_count, axis=1).reshape(-1),
        },
        columns=FORECAST_COLUMNS,
    )


def evaluate_candidate(config, registry, closes, candidate_id):
    origins = [
        summarize_origins(
            _date_forecasts(rows, closes, config, candidate_id),
            quantiles=config.interval_quantiles,
        )
        for _, rows in registry.groupby(["fold_id", "origin_date"], sort=True)
    ]
    return aggregate_dates(pd.concat(origins, ignore_index=True))


def _summary_rows(candidate_id, dates):
    rows = []
    for fold_id, fold in dates.groupby("fold_id", sort=True):
        rows.append({"candidate_id": candidate_id, "scope": fold_id, **summarize_metrics(fold)})
    rows.append({"candidate_id": candidate_id, "scope": "pooled", **summarize_metrics(dates)})
    return rows


def _write_per_date_metrics(path, dates):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    output = dates.copy()
    output["origin_date"] = pd.to_datetime(output["origin_date"]).dt.strftime("%Y-%m-%d")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                output.to_csv(text, index=False, lineterminator="\n")
    os.replace(temporary, path)
    return path


def _metric_table(rows, scope_label):
    header = (
        f"| candidate | {scope_label} | DA | MW-DA | RankIC | HitRate@Top10 | CRPS | "
        "coverage | width |"
    )
    lines = [header, "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    lines.extend(
        f"| `{row['candidate_id']}` | {row['scope']} | {row['DA']:.4f} | "
        f"{row['MW-DA']:.4f} | {row['RankIC']:.4f} | {row['HitRate@Top10']:.4f} | "
        f"{row['CRPS']:.6f} | {row['coverage']:.4f} | {row['interval_width']:.6f} |"
        for row in rows.to_dict("records")
    )
    return "\n".join(lines)


def _render_report(config, summary, registry, registry_hash):
    pooled = summary[summary["scope"] == "pooled"]
    folds = summary[summary["scope"] != "pooled"].sort_values(
        ["candidate_id", "scope"], kind="mergesort"
    )
    table = _metric_table(pooled, "scope")
    fold_table = _metric_table(folds, "fold")
    persistence_folds = folds[folds["candidate_id"] == "persistence"]
    best_fold = persistence_folds.loc[persistence_folds["DA"].idxmax()]
    return f"""# M2.2 Naive Reference Report

## Decision

M2.2 evaluated two causal naive references on the frozen M2.1 common origins. No
Kronos inference, training, or model selection was performed. These numbers are
the floor that any future model must beat on identical origins.

## Evidence

- Dataset: `{config.dataset_id}`
- Registry SHA256: `{registry_hash}`
- Origin rows per candidate: {len(registry):,}
- Evaluation dates: {registry['origin_date'].nunique():,}
- Symbols: {registry['security_id'].nunique():,}
- Sample paths per origin: {config.sample_count}
- Sampling seed: {config.sampling_seed}
- Interval quantiles: {list(config.interval_quantiles)}

{table}

## Per-Fold Evidence

{fold_table}

## Reading These Numbers

- `persistence` predicts zero cumulative return, so `direction(0) = -1` makes it a
  permanent down call; its DA equals the share of non-positive realized returns.
- That trivial down call reaches DA {best_fold['DA']:.4f} in `{best_fold['scope']}`,
  which is a direct warning about the `DA >= 52%` product utility floor: a falling
  market can lift DA above the floor without any forecasting skill. DA alone
  therefore cannot promote a model, and MW-DA plus RankIC carry the decision.
- `recent_return_bootstrap` resamples contiguous five-session blocks from the
  trailing {RECENT_RETURN_LOOKBACK} observed sessions, so it carries realistic
  dispersion without any cross-sectional signal.
- RankIC near zero is the expected result for both references. A model that fails
  to beat these values has produced no ranking information.
- CRPS, coverage, and width come from the sampled paths, not from a point
  forecast; `persistence` has zero width by construction.

## Guardrails

- Paired comparison is preserved: both candidates use identical origins, targets,
  sample counts, and per-origin seeds.
- No future observation reaches a forecast; both references read only closes up
  to the forecast origin.
- Confidence intervals are absent by design; paired date-block bootstrap arrives
  with M2.3.
- The fixed current VN150 population remains survivorship-biased.
- Provider price-adjustment semantics remain unverified.

## Next Step

M2.3 adds the zero-shot Kronos runner on these same origins, then paired
stationary date-block inference against these references.
"""


def evaluate_naive_references(config_path, command=None):
    config_path = Path(config_path)
    config = load_naive_config(config_path)
    registry, registry_hash, registry_manifest = load_registry(config)
    closes, dataset_manifest = load_close_series(config, registry)

    summary_rows = []
    artifact_hashes = {}
    for candidate_id in BASELINE_IDS:
        dates = evaluate_candidate(config, registry, closes, candidate_id)
        per_date_path = _write_per_date_metrics(
            config.output_dir / f"{candidate_id}_per_date_metrics.csv.gz", dates
        )
        artifact_hashes[per_date_path.name] = sha256_file(per_date_path)
        summary_rows.extend(_summary_rows(candidate_id, dates))

    summary = pd.DataFrame(summary_rows)
    config.report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = config.report_dir / "metric_summary.csv"
    summary.to_csv(summary_path, index=False, lineterminator="\n")
    report_path = config.report_dir / "naive_reference_report.md"
    report_path.write_text(
        _render_report(config, summary, registry, registry_hash), encoding="utf-8"
    )
    artifact_hashes["metric_summary.csv"] = sha256_file(summary_path)
    artifact_hashes["naive_reference_report.md"] = sha256_file(report_path)

    if command is None:
        command = (
            "python evaluation/run_naive_references.py --config "
            f"{config_path.as_posix()}"
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": config.dataset_id,
        "candidates": list(BASELINE_IDS),
        "config_path": config_path.as_posix(),
        "config_sha256": sha256_file(config_path),
        "registry_path": config.registry_path.as_posix(),
        "registry_sha256": registry_hash,
        "registry_manifest_sha256": sha256_file(config.registry_manifest_path),
        "dataset_fingerprint": registry_manifest["dataset_fingerprint"],
        "horizon": config.horizon,
        "sample_count": config.sample_count,
        "sampling_seed": config.sampling_seed,
        "interval_quantiles": list(config.interval_quantiles),
        "origin_rows": len(registry),
        "evaluation_dates": int(registry["origin_date"].nunique()),
        "symbols": int(registry["security_id"].nunique()),
        "lockbox_start": registry_manifest["lockbox_start"],
        "lockbox_opened": False,
        "model_inference": False,
        "price_adjustment_status": dataset_manifest["price_adjustment_status"],
        "amount_policy": dataset_manifest["amount_policy"],
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
    parser = argparse.ArgumentParser(description="Evaluate the M2.2 naive references")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    command = " ".join([sys.executable, __file__, "--config", str(args.config)])
    manifest, summary = evaluate_naive_references(args.config, command=command)

    print(f"Origins per candidate: {manifest['origin_rows']:,}")
    print(f"Dates: {manifest['evaluation_dates']:,}")
    print(f"Symbols: {manifest['symbols']:,}")
    pooled = summary[summary["scope"] == "pooled"]
    for row in pooled.to_dict("records"):
        print(
            f"{row['candidate_id']}: DA={row['DA']:.4f} MW-DA={row['MW-DA']:.4f} "
            f"RankIC={row['RankIC']:.4f} HitRate={row['HitRate@Top10']:.4f} "
            f"CRPS={row['CRPS']:.6f} coverage={row['coverage']:.4f}"
        )


if __name__ == "__main__":
    main()
