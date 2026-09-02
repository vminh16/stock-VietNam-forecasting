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
from evaluation.research.origins import (
    OriginRegistryConfig,
    REGISTRY_COLUMNS,
    read_symbol_frame,
)
from evaluation.research.slices import (
    SCHEMA_VERSION,
    SLICE_COLUMNS,
    assign_symbol_groups,
    liquidity_tiers,
    trailing_liquidity,
)

REGISTRY_SCHEMA_VERSION = "m2_1_origin_registry_v1"
VERIFY_SAMPLE = 64


@dataclass(frozen=True)
class SliceConfig:
    schema_version: str
    dataset_id: str
    dataset_dir: Path
    dataset_manifest_path: Path
    registry_path: Path
    registry_manifest_path: Path
    output_path: Path
    report_dir: Path
    liquidity_lookback: int
    tier_count: int
    group_count: int
    group_salt: str


def load_slice_config(path):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    config = SliceConfig(
        schema_version=str(raw["schema_version"]),
        dataset_id=str(raw["dataset_id"]),
        dataset_dir=Path(raw["dataset_dir"]),
        dataset_manifest_path=Path(raw["dataset_manifest_path"]),
        registry_path=Path(raw["registry_path"]),
        registry_manifest_path=Path(raw["registry_manifest_path"]),
        output_path=Path(raw["output_path"]),
        report_dir=Path(raw["report_dir"]),
        liquidity_lookback=int(raw["liquidity_lookback"]),
        tier_count=int(raw["tier_count"]),
        group_count=int(raw["group_count"]),
        group_salt=str(raw["group_salt"]),
    )
    if config.schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {config.schema_version}")
    if config.liquidity_lookback > 126:
        raise ValueError("Liquidity lookback must fit inside the registered history")
    if config.tier_count < 2 or config.group_count < 2:
        raise ValueError("tier_count and group_count must be at least 2")
    if not config.group_salt:
        raise ValueError("group_salt must be recorded so the split is reproducible")
    return config


def _git_value(*args):
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def load_registry(config):
    registry_hash = sha256_file(config.registry_path)
    registry_manifest = json.loads(
        config.registry_manifest_path.read_text(encoding="utf-8")
    )
    if registry_manifest["schema_version"] != REGISTRY_SCHEMA_VERSION:
        raise ValueError("Registry manifest schema version mismatch")
    if registry_manifest["registry_sha256"] != registry_hash:
        raise ValueError("Registry file does not match its manifest hash")

    registry = pd.read_csv(config.registry_path)
    if list(registry.columns) != REGISTRY_COLUMNS:
        raise ValueError("Registry columns do not match the M2.1 contract")
    registry["origin_date"] = pd.to_datetime(registry["origin_date"])
    return registry, registry_hash, registry_manifest


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


def liquidity_values(config, registry, dataset_manifest):
    """Attach the point-in-time liquidity of every registered origin."""
    source_config = _source_config(config)
    values = pd.Series(index=registry.index, dtype=np.float64)
    identifiers = registry[["symbol", "security_id"]].drop_duplicates()
    for symbol, security_id in identifiers.itertuples(index=False):
        frame = read_symbol_frame(source_config, dataset_manifest, symbol, security_id)
        amount = frame["amount"].to_numpy(dtype=np.float64)
        if not np.isfinite(amount).all() or (amount < 0).any():
            raise ValueError(f"Curated amount series is not usable: {symbol}")
        rolling = (
            frame.groupby("segment_id")["amount"]
            .transform(lambda column: column.rolling(config.liquidity_lookback).median())
            .to_numpy(dtype=np.float64)
        )
        rows = registry.index[registry["symbol"] == symbol]
        offsets = registry.loc[rows, "row_origin"].to_numpy(dtype=np.int64)
        selected = rolling[offsets]
        if not np.isfinite(selected).all():
            raise ValueError(f"Liquidity window is incomplete at an origin: {symbol}")
        values.loc[rows] = selected

        # Tie the vectorized path to the unit-tested scalar definition.
        for offset, expected in zip(offsets[:VERIFY_SAMPLE], selected[:VERIFY_SAMPLE]):
            direct = trailing_liquidity(amount, int(offset), config.liquidity_lookback)
            if not np.isclose(direct, expected, rtol=0.0, atol=1e-9):
                raise ValueError(f"Rolling liquidity disagrees with the definition: {symbol}")
    if values.isna().any():
        raise ValueError("An origin received no liquidity value")
    return values


def build_slices(config, registry, dataset_manifest):
    frame = registry[
        ["fold_id", "origin_id", "security_id", "symbol", "origin_date"]
    ].copy()
    frame["liquidity_value"] = liquidity_values(config, registry, dataset_manifest)
    frame["liquidity_tier"] = liquidity_tiers(frame, config.tier_count)
    groups = assign_symbol_groups(
        frame["security_id"], config.group_count, config.group_salt
    )
    frame["symbol_group"] = frame["security_id"].map(groups)
    if frame["symbol_group"].isna().any():
        raise ValueError("A symbol received no group")
    frame.insert(0, "schema_version", SCHEMA_VERSION)
    return frame[SLICE_COLUMNS].sort_values(
        ["fold_id", "origin_date", "security_id"], kind="mergesort"
    ).reset_index(drop=True)


def write_slices(frame, path):
    path = Path(path)
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


def _group_table(frame):
    rows = []
    for group, block in frame.groupby("symbol_group", sort=True):
        shares = block["liquidity_tier"].value_counts(normalize=True)
        rows.append(
            {
                "symbol_group": group,
                "symbols": int(block["security_id"].nunique()),
                "origins": len(block),
                "top_tier_share": float(shares.get("tier_0", 0.0)),
            }
        )
    return pd.DataFrame(rows)


def _tier_table(frame):
    rows = []
    for tier, block in frame.groupby("liquidity_tier", sort=True):
        rows.append(
            {
                "liquidity_tier": tier,
                "origins": len(block),
                "symbols": int(block["security_id"].nunique()),
                "median_amount": float(block["liquidity_value"].median()),
                "min_symbols_per_date": int(
                    block.groupby(["fold_id", "origin_date"])["security_id"]
                    .nunique()
                    .min()
                ),
            }
        )
    return pd.DataFrame(rows)


def _render_report(config, frame, registry_hash, groups, tiers):
    group_lines = [
        "| symbol_group | symbols | origins | share of origins in tier_0 |",
        "|---|---:|---:|---:|",
    ]
    group_lines.extend(
        f"| `{row['symbol_group']}` | {row['symbols']} | {row['origins']:,} | "
        f"{row['top_tier_share']:.3f} |"
        for row in groups.to_dict("records")
    )
    tier_lines = [
        "| liquidity_tier | origins | symbols seen | median amount | "
        "min symbols on a date |",
        "|---|---:|---:|---:|---:|",
    ]
    tier_lines.extend(
        f"| `{row['liquidity_tier']}` | {row['origins']:,} | {row['symbols']} | "
        f"{row['median_amount']:,.0f} | {row['min_symbols_per_date']} |"
        for row in tiers.to_dict("records")
    )
    thin = tiers[tiers["min_symbols_per_date"] < 10]
    warning = (
        "Every tier keeps at least ten symbols on every date, so HitRate@Top10 is "
        "defined inside each tier."
        if thin.empty
        else "At least one tier falls below ten symbols on some date; "
        "HitRate@Top10 is undefined there and those dates are dropped from that "
        "slice only."
    )
    return f"""# M2.6 Origin Slice Assignment Report

## Decision

This unit assigns two slice labels to every frozen M2.1 origin. It runs no model
and reads no evaluation result, so both partitions are usable as pre-registered
slices. No metric is computed here.

## Registered Setup

- Registry SHA256: `{registry_hash}`
- Origins labelled: {len(frame):,}
- Evaluation dates: {frame['origin_date'].nunique():,}
- Symbols: {frame['security_id'].nunique():,}
- Liquidity lookback: {config.liquidity_lookback} sessions, median traded amount
- Liquidity tiers: {config.tier_count}, assigned inside each evaluation date
- Symbol groups: {config.group_count}, salted hash `{config.group_salt}`

## Symbol Groups

{chr(10).join(group_lines)}

The group label is a salted hash of `security_id` alone. It reads no price, no
return, and no model output, so an unseen-symbol holdout picked from this table
cannot have been chosen after seeing which symbols a candidate ranks well. The
tier-0 share column is a diagnostic only: a group whose share is far from
{1.0 / config.tier_count:.3f} is liquidity-skewed by chance, and a holdout built
from it will not represent the whole population.

## Liquidity Tiers

{chr(10).join(tier_lines)}

{warning}

Tiers are assigned inside each date, so a symbol moves between tiers as its
liquidity changes and each tier holds a stable share of the cross-section. A
fixed absolute threshold would instead drift with market growth and would make a
2022 tier incomparable to a 2025 tier.

## Limitations

- `amount` is the `volume * OHLC4` compatibility proxy recorded by M1, not
  provider-reported turnover, so tiers rank a proxy for traded value.
- The fixed VN150 population remains survivorship-conditional; tiers rank inside
  it and say nothing about symbols the universe excludes.
- Group balance is left to the hash. The report shows the realized skew rather
  than correcting it, because stratifying on liquidity would make the partition
  depend on the data it is meant to hold out.

## Next Step

`evaluation/run_metric_slices.py` recomputes per-date metrics inside each slice
from the per-origin metric files, and the existing paired date-block bootstrap
consumes those files unchanged.
"""


def build_origin_slices(config_path, command=None):
    config_path = Path(config_path)
    config = load_slice_config(config_path)
    registry, registry_hash, registry_manifest = load_registry(config)
    dataset_manifest = json.loads(
        config.dataset_manifest_path.read_text(encoding="utf-8")
    )
    if dataset_manifest["dataset_id"] != config.dataset_id:
        raise ValueError("Dataset ID does not match the slice config")

    frame = build_slices(config, registry, dataset_manifest)
    output_path = write_slices(frame, config.output_path)
    groups = _group_table(frame)
    tiers = _tier_table(frame)

    config.report_dir.mkdir(parents=True, exist_ok=True)
    group_path = config.report_dir / "symbol_groups.csv"
    groups.to_csv(group_path, index=False, lineterminator="\n")
    tier_path = config.report_dir / "liquidity_tiers.csv"
    tiers.to_csv(tier_path, index=False, lineterminator="\n")
    report_path = config.report_dir / "origin_slice_report.md"
    report_path.write_text(
        _render_report(config, frame, registry_hash, groups, tiers), encoding="utf-8"
    )

    if command is None:
        command = (
            "python evaluation/run_origin_slices.py --config "
            f"{config_path.as_posix()}"
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": config.dataset_id,
        "config_path": config_path.as_posix(),
        "config_sha256": sha256_file(config_path),
        "registry_path": config.registry_path.as_posix(),
        "registry_sha256": registry_hash,
        "dataset_fingerprint": registry_manifest["dataset_fingerprint"],
        "slices_path": output_path.as_posix(),
        "slices_sha256": sha256_file(output_path),
        "liquidity_lookback": config.liquidity_lookback,
        "liquidity_source_column": "amount",
        "tier_count": config.tier_count,
        "group_count": config.group_count,
        "group_salt": config.group_salt,
        "origins": len(frame),
        "evaluation_dates": int(frame["origin_date"].nunique()),
        "symbols": int(frame["security_id"].nunique()),
        "symbol_group_sizes": {
            str(row["symbol_group"]): int(row["symbols"])
            for row in groups.to_dict("records")
        },
        "model_inference": False,
        "training": False,
        "lockbox_opened": False,
        "price_adjustment_status": dataset_manifest["price_adjustment_status"],
        "amount_policy": dataset_manifest["amount_policy"],
        "command": command,
        "code_revision": _git_value("rev-parse", "HEAD"),
        "worktree_dirty": bool(_git_value("status", "--porcelain")),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_hashes": {
            "symbol_groups.csv": sha256_file(group_path),
            "liquidity_tiers.csv": sha256_file(tier_path),
            "origin_slice_report.md": sha256_file(report_path),
        },
    }
    manifest_path = config.report_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest, frame


def main(argv=None):
    parser = argparse.ArgumentParser(description="Assign M2.6 origin slice labels")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    command = " ".join([sys.executable, __file__, "--config", str(args.config)])
    manifest, frame = build_origin_slices(args.config, command=command)

    print(f"Origins labelled: {manifest['origins']:,}")
    print(f"Symbols: {manifest['symbols']:,}")
    print(f"Slices SHA256: {manifest['slices_sha256']}")
    for group, size in sorted(manifest["symbol_group_sizes"].items()):
        print(f"{group}: {size} symbols")


if __name__ == "__main__":
    main()
