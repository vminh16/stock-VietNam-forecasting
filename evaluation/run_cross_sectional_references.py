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

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.crawl import sha256_file
from evaluation.research.cross_sectional import (
    CROSS_SECTIONAL_IDS,
    MOMENTUM_FORMATION,
    MOMENTUM_SKIP,
    REQUIRED_HISTORY,
    REVERSAL_LOOKBACK,
    SCHEMA_VERSION,
    forecast_cross_sectional,
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

REGISTRY_SCHEMA_VERSION = "m2_1_origin_registry_v1"


@dataclass(frozen=True)
class CrossSectionalConfig:
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


def load_cross_sectional_config(path):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    config = CrossSectionalConfig(
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
    )
    if config.schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {config.schema_version}")
    if config.horizon != 5:
        raise ValueError("M2.8 horizon must be 5")
    if config.sample_count < 2:
        raise ValueError("sample_count must allow ensemble statistics")
    return config


def _git_value(*args):
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def load_registry(config):
    registry_hash = sha256_file(config.registry_path)
    manifest = json.loads(config.registry_manifest_path.read_text(encoding="utf-8"))
    if manifest["schema_version"] != REGISTRY_SCHEMA_VERSION:
        raise ValueError("Registry manifest schema version mismatch")
    if manifest["registry_sha256"] != registry_hash:
        raise ValueError("Registry file does not match its manifest hash")
    registry = pd.read_csv(config.registry_path)
    if list(registry.columns) != REGISTRY_COLUMNS:
        raise ValueError("Registry columns do not match the M2.1 contract")
    registry["origin_date"] = pd.to_datetime(registry["origin_date"])
    return registry, registry_hash, manifest


def load_close_series(config, registry):
    dataset_manifest = json.loads(
        config.dataset_manifest_path.read_text(encoding="utf-8")
    )
    if dataset_manifest["dataset_id"] != config.dataset_id:
        raise ValueError("Dataset ID does not match the cross-sectional config")
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
    for symbol, security_id in (
        registry[["symbol", "security_id"]].drop_duplicates().itertuples(index=False)
    ):
        frame = read_symbol_frame(source_config, dataset_manifest, symbol, security_id)
        close = frame["close"].to_numpy(dtype=np.float64)
        if not np.isfinite(close).all() or (close <= 0).any():
            raise ValueError(f"Curated close series is not positive: {symbol}")
        closes[symbol] = close
    return closes, dataset_manifest


def _date_forecasts(rows, closes, config, candidate_id):
    predicted = np.empty((len(rows), config.sample_count, config.horizon))
    actual = np.empty((len(rows), config.horizon))
    for position, row in enumerate(rows.itertuples(index=False)):
        close = closes[row.symbol]
        history = close[row.row_start_l126 : row.row_origin + 1]
        future = close[row.row_target_start : row.row_target_end + 1]
        if history.size != REQUIRED_HISTORY or future.size != config.horizon:
            raise ValueError(f"Registry offsets are out of range: {row.origin_id}")
        paths = forecast_cross_sectional(
            history, horizon=config.horizon, sample_count=config.sample_count
        )
        predicted[position] = paths[candidate_id]
        actual[position] = future / close[row.row_origin] - 1.0

    block = config.horizon * config.sample_count
    return pd.DataFrame(
        {
            "fold_id": np.repeat(rows["fold_id"].to_numpy(), block),
            "origin_id": np.repeat(rows["origin_id"].to_numpy(), block),
            "security_id": np.repeat(rows["security_id"].to_numpy(), block),
            "origin_date": np.repeat(rows["origin_date"].to_numpy(), block),
            "sample_id": np.tile(
                np.arange(config.sample_count), len(rows) * config.horizon
            ),
            "horizon_step": np.tile(
                np.repeat(np.arange(1, config.horizon + 1), config.sample_count),
                len(rows),
            ),
            "predicted_return": predicted.transpose(0, 2, 1).reshape(-1),
            "actual_return": np.repeat(actual, config.sample_count, axis=1).reshape(-1),
        },
        columns=FORECAST_COLUMNS,
    )


def evaluate_candidate(config, registry, closes, candidate_id):
    origins = pd.concat(
        [
            summarize_origins(
                _date_forecasts(rows, closes, config, candidate_id),
                quantiles=INTERVAL_QUANTILES,
            )
            for _, rows in registry.groupby(["fold_id", "origin_date"], sort=True)
        ],
        ignore_index=True,
    )
    return origins, aggregate_dates(origins)


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


def _render_report(config, summary, registry, registry_hash):
    pooled = summary[summary["scope"] == "pooled"]
    lines = [
        "| candidate | DA | MW-DA | RankIC | HitRate@Top10 |",
        "|---|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| `{row['candidate_id']}` | {row['DA']:.4f} | {row['MW-DA']:.4f} | "
        f"{row['RankIC']:.4f} | {row['HitRate@Top10']:.4f} |"
        for row in pooled.to_dict("records")
    )
    folds = summary[summary["scope"] != "pooled"].sort_values(
        ["candidate_id", "scope"], kind="mergesort"
    )
    fold_lines = [
        "| candidate | fold | RankIC | HitRate@Top10 |",
        "|---|---|---:|---:|",
    ]
    fold_lines.extend(
        f"| `{row['candidate_id']}` | {row['scope']} | {row['RankIC']:.4f} | "
        f"{row['HitRate@Top10']:.4f} |"
        for row in folds.to_dict("records")
    )
    return f"""# M2.8 Cross-Sectional Reference Report

## Decision

M2.2 established that Kronos beats references carrying no ranking information.
This unit adds references that do carry ranking information, so a model can be
asked the harder question: does it beat a cheap, well-known effect computed from
the same closes? No model ran here and no promotion follows from this report.

## Registered Setup

- Registry SHA256: `{registry_hash}`
- Origin rows per candidate: {len(registry):,}
- Evaluation dates: {registry['origin_date'].nunique():,}
- Symbols: {registry['security_id'].nunique():,}
- Horizon: {config.horizon}
- Sample paths per origin: {config.sample_count}, identical by construction
- Seeds: none. Both references are deterministic.

`short_term_reversal` predicts the negative of the trailing
{REVERSAL_LOOKBACK}-session return, the horizon this project forecasts.
`momentum_126_21` predicts continuation of the {MOMENTUM_FORMATION}-session
formation return that skips the most recent {MOMENTUM_SKIP} sessions, rescaled
to the forecast horizon by simple proportion. Both fit inside the registered
`L=126` history, so they add no data requirement.

## Ranking Metrics

{chr(10).join(lines)}

## Per-Fold Ranking Metrics

{chr(10).join(fold_lines)}

## Reading These Numbers

- These are **point forecasts replicated across samples**. CRPS, interval
  coverage, and interval width are meaningless for them and are omitted from the
  tables above on purpose. A probabilistic comparison against these references
  would need a dispersion model that is not registered.
- The horizon rescaling is unit conversion, not a fitted coefficient. RankIC is
  invariant to it, so the ranking comparison is unaffected by that choice; DA and
  MW-DA depend only on sign, which the rescaling preserves.
- A reference whose pooled RankIC is far from zero means a cheap formula already
  ranks this market. Any model claim must then clear that formula, not just the
  M2.2 noise references.
- Both references read only closes up to the forecast origin.

## Guardrails

- Identical origins, targets, and horizon as every other M2 candidate, so paired
  date-block inference applies without restriction.
- The fixed VN150 population remains survivorship-conditional.
- Provider price-adjustment semantics remain unverified, and a corporate action
  that the provider did not adjust will contaminate both a reversal and a
  momentum signal more than it contaminates a naive reference.
- The 2026 lockbox remains closed.
"""


def evaluate_cross_sectional_references(config_path, command=None):
    config_path = Path(config_path)
    config = load_cross_sectional_config(config_path)
    registry, registry_hash, registry_manifest = load_registry(config)
    closes, dataset_manifest = load_close_series(config, registry)

    summary_rows = []
    artifact_hashes = {}
    for candidate_id in CROSS_SECTIONAL_IDS:
        origins, dates = evaluate_candidate(config, registry, closes, candidate_id)
        for path, frame in (
            (config.output_dir / f"{candidate_id}_per_date_metrics.csv.gz", dates),
            (config.output_dir / f"{candidate_id}_per_origin_metrics.csv.gz", origins),
        ):
            written = _write_metrics(path, frame)
            artifact_hashes[written.name] = sha256_file(written)
        for fold_id, fold in dates.groupby("fold_id", sort=True):
            summary_rows.append(
                {"candidate_id": candidate_id, "scope": fold_id, **summarize_metrics(fold)}
            )
        summary_rows.append(
            {"candidate_id": candidate_id, "scope": "pooled", **summarize_metrics(dates)}
        )

    summary = pd.DataFrame(summary_rows)
    config.report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = config.report_dir / "metric_summary.csv"
    summary.to_csv(summary_path, index=False, lineterminator="\n")
    report_path = config.report_dir / "cross_sectional_reference_report.md"
    report_path.write_text(
        _render_report(config, summary, registry, registry_hash), encoding="utf-8"
    )
    artifact_hashes[summary_path.name] = sha256_file(summary_path)
    artifact_hashes[report_path.name] = sha256_file(report_path)

    if command is None:
        command = (
            "python evaluation/run_cross_sectional_references.py --config "
            f"{config_path.as_posix()}"
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": config.dataset_id,
        "candidates": list(CROSS_SECTIONAL_IDS),
        "config_path": config_path.as_posix(),
        "config_sha256": sha256_file(config_path),
        "registry_path": config.registry_path.as_posix(),
        "registry_sha256": registry_hash,
        "dataset_fingerprint": registry_manifest["dataset_fingerprint"],
        "horizon": config.horizon,
        "sample_count": config.sample_count,
        "deterministic": True,
        "reversal_lookback": REVERSAL_LOOKBACK,
        "momentum_formation": MOMENTUM_FORMATION,
        "momentum_skip": MOMENTUM_SKIP,
        "origin_rows": len(registry),
        "evaluation_dates": int(registry["origin_date"].nunique()),
        "symbols": int(registry["security_id"].nunique()),
        "model_inference": False,
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
    manifest_path = config.report_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest, summary


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Evaluate the M2.8 cross-sectional references"
    )
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    command = " ".join([sys.executable, __file__, "--config", str(args.config)])
    manifest, summary = evaluate_cross_sectional_references(args.config, command=command)

    print(f"Origins per candidate: {manifest['origin_rows']:,}")
    print(f"Dates: {manifest['evaluation_dates']:,}")
    for row in summary[summary["scope"] == "pooled"].to_dict("records"):
        print(
            f"{row['candidate_id']}: DA={row['DA']:.4f} MW-DA={row['MW-DA']:.4f} "
            f"RankIC={row['RankIC']:.4f} HitRate={row['HitRate@Top10']:.4f}"
        )


if __name__ == "__main__":
    main()
