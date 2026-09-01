import argparse
import json
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
from evaluation.research.diagnostics import normalization_variants, variance_ratio
from evaluation.research.origins import OriginRegistryConfig, read_symbol_frame

SCHEMA_VERSION = "m2_4_data_diagnostics_v1"
REGISTRY_SCHEMA_VERSION = "m2_1_origin_registry_v1"


@dataclass(frozen=True)
class DiagnosticsConfig:
    schema_version: str
    dataset_id: str
    dataset_dir: Path
    dataset_manifest_path: Path
    registry_path: Path
    registry_manifest_path: Path
    output_dir: Path
    report_dir: Path
    horizons: tuple
    minimum_returns: int
    liquidity_tiers: int
    short_lookback: int
    long_lookback: int
    date_stride: int
    clip: float
    features: tuple


def load_diagnostics_config(path):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    ratio = raw["variance_ratio"]
    normalization = raw["normalization"]
    config = DiagnosticsConfig(
        schema_version=str(raw["schema_version"]),
        dataset_id=str(raw["dataset_id"]),
        dataset_dir=Path(raw["dataset_dir"]),
        dataset_manifest_path=Path(raw["dataset_manifest_path"]),
        registry_path=Path(raw["registry_path"]),
        registry_manifest_path=Path(raw["registry_manifest_path"]),
        output_dir=Path(raw["output_dir"]),
        report_dir=Path(raw["report_dir"]),
        horizons=tuple(int(value) for value in ratio["horizons"]),
        minimum_returns=int(ratio["minimum_returns"]),
        liquidity_tiers=int(ratio["liquidity_tiers"]),
        short_lookback=int(normalization["short_lookback"]),
        long_lookback=int(normalization["long_lookback"]),
        date_stride=int(normalization["date_stride"]),
        clip=float(normalization["clip"]),
        features=tuple(str(value) for value in normalization["features"]),
    )
    if config.schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {config.schema_version}")
    if min(config.horizons) < 2:
        raise ValueError("Variance-ratio horizons must be at least two sessions")
    if not 0 < config.short_lookback < config.long_lookback:
        raise ValueError("short_lookback must be shorter than long_lookback")
    if config.date_stride < 1:
        raise ValueError("date_stride must be positive")
    return config


def _git_value(*args):
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _source_config(config):
    return OriginRegistryConfig(
        schema_version=REGISTRY_SCHEMA_VERSION,
        dataset_id=config.dataset_id,
        dataset_dir=config.dataset_dir,
        dataset_manifest_path=config.dataset_manifest_path,
        universe_path=Path("."),
        registry_path=config.registry_path,
        report_dir=config.report_dir,
        lookbacks=(63, 126),
        horizon=5,
        minimum_cross_section=10,
        lockbox_start=datetime(2026, 1, 1).date(),
        folds=(),
    )


def load_inputs(config):
    registry_hash = sha256_file(config.registry_path)
    registry_manifest = json.loads(
        config.registry_manifest_path.read_text(encoding="utf-8")
    )
    if registry_manifest["registry_sha256"] != registry_hash:
        raise ValueError("Registry file does not match its manifest hash")

    registry = pd.read_csv(config.registry_path)
    registry["origin_date"] = pd.to_datetime(registry["origin_date"])

    dataset_manifest = json.loads(
        config.dataset_manifest_path.read_text(encoding="utf-8")
    )
    source_config = _source_config(config)
    frames = {}
    identifiers = registry[["symbol", "security_id"]].drop_duplicates()
    for symbol, security_id in identifiers.itertuples(index=False):
        frames[symbol] = read_symbol_frame(
            source_config, dataset_manifest, symbol, security_id
        )
    return registry, frames, registry_hash, registry_manifest, dataset_manifest


def variance_ratio_rows(config, registry, frames):
    folds = (
        registry.groupby("fold_id")["origin_date"].agg(["min", "max"]).sort_index()
    )
    records = []
    for fold_id, bounds in folds.iterrows():
        for symbol, frame in frames.items():
            inside = frame[
                (frame["timestamps"] >= bounds["min"])
                & (frame["timestamps"] <= bounds["max"] + pd.Timedelta(days=1))
            ]
            if inside.empty:
                continue
            turnover = float((inside["close"] * inside["volume"]).median())
            for segment_id, segment in inside.groupby("segment_id", sort=True):
                close = segment["close"].to_numpy(dtype=np.float64)
                if close.size < config.minimum_returns + 1:
                    continue
                returns = np.diff(np.log(close))
                for horizon in config.horizons:
                    try:
                        ratio, z_star = variance_ratio(returns, horizon)
                    except ValueError:
                        continue
                    records.append(
                        {
                            "fold_id": fold_id,
                            "symbol": symbol,
                            "segment_id": int(segment_id),
                            "sessions": int(close.size),
                            "returns": int(returns.size),
                            "median_turnover": turnover,
                            "q": horizon,
                            "variance_ratio": ratio,
                            "z_star": z_star,
                        }
                    )

    rows = pd.DataFrame(records)
    if rows.empty:
        raise ValueError("No eligible series for the variance ratio")
    labels = ["low", "mid", "high"][: config.liquidity_tiers]
    rows["liquidity_tier"] = (
        rows.groupby(["fold_id", "q"])["median_turnover"]
        .transform(
            lambda values: pd.qcut(
                values.rank(method="first"), config.liquidity_tiers, labels=labels
            )
        )
        .astype(str)
    )
    return rows.sort_values(["fold_id", "q", "symbol"], kind="mergesort").reset_index(
        drop=True
    )


def _summarize_variance_ratio(rows, scope_column):
    records = []
    for (scope, horizon), group in rows.groupby([scope_column, "q"], sort=True):
        records.append(
            {
                "scope_kind": scope_column,
                "scope": scope,
                "q": horizon,
                "series": len(group),
                "median_variance_ratio": float(group["variance_ratio"].median()),
                "q25_variance_ratio": float(group["variance_ratio"].quantile(0.25)),
                "q75_variance_ratio": float(group["variance_ratio"].quantile(0.75)),
                "share_mean_reverting": float((group["z_star"] < -1.96).mean()),
                "share_trending": float((group["z_star"] > 1.96).mean()),
            }
        )
    return pd.DataFrame(records)


def normalization_rows(config, registry, frames):
    dates = np.sort(registry["origin_date"].unique())[:: config.date_stride]
    sampled = registry[registry["origin_date"].isin(dates)]
    feature_records = []
    window_records = []
    for symbol, rows in sampled.groupby("symbol", sort=True):
        values = frames[symbol][list(config.features)].to_numpy(dtype=np.float64)
        for row in rows.itertuples(index=False):
            start = row.row_origin - config.long_lookback + 1
            window = values[start : row.row_origin + 1]
            if window.shape[0] != config.long_lookback:
                continue
            variants = normalization_variants(
                window, config.short_lookback, clip=config.clip
            )
            key = {
                "fold_id": row.fold_id,
                "origin_date": row.origin_date,
                "symbol": symbol,
            }
            for index, feature in enumerate(config.features):
                feature_records.append(
                    {
                        **key,
                        "feature": feature,
                        "scale_ratio": float(variants["scale_ratio"][index]),
                        "mean_shift": float(variants["mean_shift"][index]),
                    }
                )
            window_records.append(
                {
                    **key,
                    "clip_rate_short": variants["clip_rate"]["short"],
                    "clip_rate_long": variants["clip_rate"]["long"],
                    "clip_rate_short_scaled_by_long": variants["clip_rate"][
                        "short_scaled_by_long"
                    ],
                    "abs_z_short": variants["abs_z_mean"]["short"],
                    "abs_z_long": variants["abs_z_mean"]["long"],
                    "abs_z_short_scaled_by_long": variants["abs_z_mean"][
                        "short_scaled_by_long"
                    ],
                }
            )

    features = pd.DataFrame(feature_records)
    windows = pd.DataFrame(window_records)
    if features.empty:
        raise ValueError("No eligible origin for the normalization diagnostic")
    order = ["fold_id", "origin_date", "symbol"]
    return (
        features.sort_values([*order, "feature"]).reset_index(drop=True),
        windows.sort_values(order).reset_index(drop=True),
    )


def _summarize_normalization(features, windows):
    per_feature = (
        features.groupby("feature")
        .agg(
            origins=("scale_ratio", "size"),
            median_scale_ratio=("scale_ratio", "median"),
            q10_scale_ratio=("scale_ratio", lambda values: values.quantile(0.10)),
            q90_scale_ratio=("scale_ratio", lambda values: values.quantile(0.90)),
            median_abs_mean_shift=("mean_shift", lambda values: values.abs().median()),
            q90_abs_mean_shift=("mean_shift", lambda values: values.abs().quantile(0.90)),
        )
        .reset_index()
    )
    summary = {
        "windows": len(windows),
        "clip_rate_short": float(windows["clip_rate_short"].mean()),
        "clip_rate_long": float(windows["clip_rate_long"].mean()),
        "clip_rate_short_scaled_by_long": float(
            windows["clip_rate_short_scaled_by_long"].mean()
        ),
        "abs_z_short": float(windows["abs_z_short"].mean()),
        "abs_z_long": float(windows["abs_z_long"].mean()),
        "abs_z_short_scaled_by_long": float(
            windows["abs_z_short_scaled_by_long"].mean()
        ),
    }
    return per_feature, summary


def _render_report(config, ratio_summary, normalization_table, normalization_summary):
    fold_rows = ratio_summary[ratio_summary["scope_kind"] == "fold_id"]
    tier_rows = ratio_summary[ratio_summary["scope_kind"] == "liquidity_tier"]

    def _ratio_table(rows, label):
        lines = [
            f"| {label} | q | series | median VR | IQR | share mean-reverting | "
            "share trending |",
            "|---|---:|---:|---:|---|---:|---:|",
        ]
        lines.extend(
            f"| {row['scope']} | {row['q']} | {row['series']} | "
            f"{row['median_variance_ratio']:.4f} | "
            f"[{row['q25_variance_ratio']:.4f}, {row['q75_variance_ratio']:.4f}] | "
            f"{row['share_mean_reverting']:.3f} | {row['share_trending']:.3f} |"
            for row in rows.to_dict("records")
        )
        return "\n".join(lines)

    feature_lines = [
        "| feature | median scale ratio | 10-90% scale ratio | median abs mean shift |",
        "|---|---:|---|---:|",
    ]
    feature_lines.extend(
        f"| {row['feature']} | {row['median_scale_ratio']:.4f} | "
        f"[{row['q10_scale_ratio']:.4f}, {row['q90_scale_ratio']:.4f}] | "
        f"{row['median_abs_mean_shift']:.4f} |"
        for row in normalization_table.to_dict("records")
    )

    price_features = [
        feature
        for feature in ("open", "high", "low", "close")
        if feature in set(normalization_table["feature"])
    ]
    prices = normalization_table[normalization_table["feature"].isin(price_features)]
    others = normalization_table[~normalization_table["feature"].isin(price_features)]
    price_ratio = float(prices["median_scale_ratio"].median())
    other_ratio = float(others["median_scale_ratio"].median())
    price_shift = float(prices["median_abs_mean_shift"].median())
    confound = (
        f"""The price channels are rescaled by a median factor of
{1.0 / price_ratio:.3f} when the normalizer moves from {config.long_lookback} to
{config.short_lookback} sessions, and their window means sit
{price_shift:.3f} long-window scale units apart, while the volume channels move
only to {other_ratio:.4f}. An `L={config.short_lookback}` versus
`L={config.long_lookback}` result therefore mixes context length with a
substantially different price scaling, and the mixture is concentrated in exactly
the channels the forecast depends on. Report any lookback conclusion as
`context + normalization`, or add a third arm that holds the normalizer fixed."""
        if price_ratio < 0.9 or price_ratio > 1.1
        else """The two normalizers agree closely on every channel, so a lookback
result can be read as a context-length effect."""
    )

    return f"""# M2.4 Data Diagnostics Report

## Decision

Two training-free diagnostics run before any GPU is spent on a lookback
comparison. E0 measures how far VN150 daily returns depart from the random walk
that the `sqrt(h)` uncertainty argument assumes. E1 measures how much of an
`L=63` versus `L=126` difference would come from the normalization window rather
than from context length, because `L` sets both.

## E0 Variance Ratio

`VR(q) = Var(R_q) / (q * Var(r))` with overlapping q-period returns and the
Lo-MacKinlay heteroskedasticity-consistent statistic. `VR = 1` is the random
walk; below one is mean reversion, above one is trending. A series is counted as
mean-reverting or trending when `|z*| > 1.96`.

{_ratio_table(fold_rows, "fold")}

{_ratio_table(tier_rows, "liquidity tier")}

Liquidity tiers are in-fold descriptive terciles of median `close * volume`, not
point-in-time tiers; they classify data, never a forecast.

## E1 Normalization Confound

Each sampled origin is normalized three ways over the same rows: `short` uses
the trailing {config.short_lookback} sessions with their own moments, `long`
uses {config.long_lookback} sessions with their own moments, and
`short_scaled_by_long` keeps the {config.short_lookback} short rows but borrows
the {config.long_lookback}-session mean and scale. `short` versus
`short_scaled_by_long` isolates the normalizer, since the rows are identical.

- Sampled windows: {normalization_summary['windows']:,}
- Mean clip rate at `|z| >= {config.clip:g}`: short
  {normalization_summary['clip_rate_short']:.5f}, long
  {normalization_summary['clip_rate_long']:.5f}, short scaled by long
  {normalization_summary['clip_rate_short_scaled_by_long']:.5f}
- Mean `|z|`: short {normalization_summary['abs_z_short']:.4f}, long
  {normalization_summary['abs_z_long']:.4f}, short scaled by long
  {normalization_summary['abs_z_short_scaled_by_long']:.4f}

{chr(10).join(feature_lines)}

`scale_ratio` is the short-window scale divided by the long-window scale, and
`mean_shift` is the difference in window means expressed in long-window scale
units. Values away from one and zero mean the two lookbacks hand the tokenizer
differently scaled inputs for the same sessions.

{confound}

## Guardrails

- Both diagnostics describe data only. No model ran and no forecast was scored.
- Variance ratios are computed inside one segment at a time; no return crosses a
  segment or a fold boundary.
- The 2026 lockbox remains closed.

## Next Step

E2 remains the deciding experiment: a zero-shot screen of `{{small, base}}` by
`{{63, 126}}` on the frozen common origins. These diagnostics only tell that
screen how to phrase its conclusion.
"""


def run_data_diagnostics(config_path, command=None):
    config_path = Path(config_path)
    config = load_diagnostics_config(config_path)
    registry, frames, registry_hash, registry_manifest, dataset_manifest = load_inputs(
        config
    )

    ratio_rows = variance_ratio_rows(config, registry, frames)
    ratio_summary = pd.concat(
        [
            _summarize_variance_ratio(ratio_rows, "fold_id"),
            _summarize_variance_ratio(ratio_rows, "liquidity_tier"),
        ],
        ignore_index=True,
    )
    norm_features, norm_windows = normalization_rows(config, registry, frames)
    norm_table, norm_summary = _summarize_normalization(norm_features, norm_windows)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    ratio_rows_path = config.output_dir / "variance_ratio_series.csv.gz"
    ratio_rows.to_csv(ratio_rows_path, index=False, compression="gzip")
    norm_features.to_csv(
        config.output_dir / "normalization_features.csv.gz",
        index=False,
        compression="gzip",
    )
    norm_windows.to_csv(
        config.output_dir / "normalization_windows.csv.gz",
        index=False,
        compression="gzip",
    )

    config.report_dir.mkdir(parents=True, exist_ok=True)
    ratio_summary_path = config.report_dir / "variance_ratio_summary.csv"
    ratio_summary.to_csv(ratio_summary_path, index=False, lineterminator="\n")
    norm_summary_path = config.report_dir / "normalization_summary.csv"
    norm_table.to_csv(norm_summary_path, index=False, lineterminator="\n")
    report_path = config.report_dir / "data_diagnostics_report.md"
    report_path.write_text(
        _render_report(config, ratio_summary, norm_table, norm_summary),
        encoding="utf-8",
    )

    if command is None:
        command = (
            "python evaluation/run_data_diagnostics.py --config "
            f"{config_path.as_posix()}"
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": config.dataset_id,
        "config_path": config_path.as_posix(),
        "config_sha256": sha256_file(config_path),
        "registry_sha256": registry_hash,
        "dataset_fingerprint": registry_manifest["dataset_fingerprint"],
        "variance_ratio_horizons": list(config.horizons),
        "normalization_lookbacks": [config.short_lookback, config.long_lookback],
        "date_stride": config.date_stride,
        "series_evaluated": int(ratio_rows["symbol"].nunique()),
        "normalization_windows": norm_summary["windows"],
        "model_inference": False,
        "lockbox_opened": False,
        "price_adjustment_status": dataset_manifest["price_adjustment_status"],
        "amount_policy": dataset_manifest["amount_policy"],
        "command": command,
        "code_revision": _git_value("rev-parse", "HEAD"),
        "worktree_dirty": bool(_git_value("status", "--porcelain")),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_hashes": {
            "variance_ratio_summary.csv": sha256_file(ratio_summary_path),
            "normalization_summary.csv": sha256_file(norm_summary_path),
            "data_diagnostics_report.md": sha256_file(report_path),
        },
    }
    manifest_path = config.report_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest, ratio_summary, norm_table, norm_summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run M2.4 training-free diagnostics")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    command = " ".join([sys.executable, __file__, "--config", str(args.config)])
    manifest, ratio_summary, _, norm_summary = run_data_diagnostics(
        args.config, command=command
    )

    folds = ratio_summary[ratio_summary["scope_kind"] == "fold_id"]
    for row in folds.to_dict("records"):
        print(
            f"VR {row['scope']} q={row['q']}: median={row['median_variance_ratio']:.4f} "
            f"mean-reverting={row['share_mean_reverting']:.3f} "
            f"trending={row['share_trending']:.3f}"
        )
    print(
        f"Normalization windows: {norm_summary['windows']:,} "
        f"clip short={norm_summary['clip_rate_short']:.5f} "
        f"long={norm_summary['clip_rate_long']:.5f} "
        f"short_scaled_by_long={norm_summary['clip_rate_short_scaled_by_long']:.5f}"
    )


if __name__ == "__main__":
    main()
