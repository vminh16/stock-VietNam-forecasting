import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from data_pipeline.crawl import sha256_file
from evaluation.research.origins import (
    build_common_origins,
    dataset_fingerprint,
    load_origin_config,
    write_registry,
)


def _git_value(*args):
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _build_summary(origins):
    rows = []
    for fold_id, fold in origins.groupby("fold_id", sort=True):
        rows.append(
            {
                "scope": "fold",
                "fold_id": fold_id,
                "origin_date": "",
                "origin_count": len(fold),
                "symbol_count": fold["security_id"].nunique(),
                "eligible_dates": fold["origin_date"].nunique(),
            }
        )
    for (fold_id, origin_date), day in origins.groupby(
        ["fold_id", "origin_date"], sort=True
    ):
        rows.append(
            {
                "scope": "date",
                "fold_id": fold_id,
                "origin_date": pd.Timestamp(origin_date).strftime("%Y-%m-%d"),
                "origin_count": len(day),
                "symbol_count": day["security_id"].nunique(),
                "eligible_dates": 1,
            }
        )
    return pd.DataFrame(rows)


def _render_report(config, origins, summary, registry_hash):
    fold_rows = summary[summary["scope"] == "fold"]
    table_lines = [
        "| fold_id | origin_count | symbol_count | eligible_dates |",
        "|---|---:|---:|---:|",
    ]
    table_lines.extend(
        f"| {row.fold_id} | {row.origin_count} | {row.symbol_count} | "
        f"{row.eligible_dates} |"
        for row in fold_rows.itertuples(index=False)
    )
    table = "\n".join(table_lines)
    return f"""# M2.1 Common-Origin Registry Report

## Decision

M2.1 created evaluation metadata only. No model inference, metric calculation,
or training was performed. Every registry row is valid for both `L=63` and
`L=126` with `H=5`.

## Registry

- Dataset: `{config.dataset_id}`
- Origin rows: {len(origins):,}
- Eligible dates: {origins['origin_date'].nunique():,}
- Symbols: {origins['security_id'].nunique():,}
- Registry SHA256: `{registry_hash}`
- Lockbox start: `{config.lockbox_start.isoformat()}`
- Minimum symbols per date: {config.minimum_cross_section}

{table}

## Guardrails

- Origins require 126 contiguous history rows and five contiguous targets in
  one security and segment; the same rows also define the 63-session view.
- Dates below ten eligible symbols are absent.
- Source data may contain 2026 rows, but no origin or target from 2026 is
  registered.
- The fixed current VN150 population remains survivorship-biased.
- Provider price-adjustment semantics remain unverified.
- `amount` remains the derived OHLC4 compatibility proxy, not provider turnover.

## Next Step

M2.2 may derive deterministic smoke and screen views from this registry and add
two causal naive forecast references. Kronos inference remains out of scope.
"""


def build_registry_artifacts(config_path, command=None):
    config_path = Path(config_path)
    config = load_origin_config(config_path)
    origins = build_common_origins(config)
    registry_path = write_registry(origins, config.registry_path)
    registry_hash = sha256_file(registry_path)

    config.report_dir.mkdir(parents=True, exist_ok=True)
    summary = _build_summary(origins)
    summary_path = config.report_dir / "registry_summary.csv"
    summary.to_csv(summary_path, index=False, lineterminator="\n")
    report_path = config.report_dir / "registry_report.md"
    report_path.write_text(
        _render_report(config, origins, summary, registry_hash), encoding="utf-8"
    )

    source_manifest_path = config.dataset_dir / "dataset_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if command is None:
        command = (
            "python evaluation/build_origin_registry.py --config "
            f"{config_path.as_posix()}"
        )
    manifest = {
        "schema_version": config.schema_version,
        "dataset_id": config.dataset_id,
        "dataset_fingerprint": dataset_fingerprint(source_manifest),
        "config_path": config_path.as_posix(),
        "config_sha256": sha256_file(config_path),
        "registry_path": registry_path.as_posix(),
        "registry_sha256": registry_hash,
        "lookbacks": list(config.lookbacks),
        "horizon": config.horizon,
        "minimum_cross_section": config.minimum_cross_section,
        "lockbox_start": config.lockbox_start.isoformat(),
        "lockbox_opened": False,
        "folds": [
            {
                "fold_id": fold.fold_id,
                "start": fold.start.isoformat(),
                "end": fold.end.isoformat(),
            }
            for fold in config.folds
        ],
        "origin_rows": len(origins),
        "eligible_dates": origins["origin_date"].nunique(),
        "symbols": origins["security_id"].nunique(),
        "source_dataset_manifest": source_manifest_path.as_posix(),
        "source_dataset_manifest_sha256": sha256_file(source_manifest_path),
        "price_adjustment_status": source_manifest["price_adjustment_status"],
        "amount_policy": source_manifest["amount_policy"],
        "command": command,
        "code_revision": _git_value("rev-parse", "HEAD"),
        "worktree_dirty": bool(_git_value("status", "--porcelain")),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_hashes": {
            "registry": registry_hash,
            "registry_summary.csv": sha256_file(summary_path),
            "registry_report.md": sha256_file(report_path),
        },
    }
    manifest_path = config.report_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the M2.1 origin registry")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    command = " ".join([sys.executable, __file__, "--config", str(args.config)])
    manifest = build_registry_artifacts(args.config, command=command)
    print(f"Registry: {manifest['registry_path']}")
    print(f"SHA256: {manifest['registry_sha256']}")
    print(f"Rows: {manifest['origin_rows']:,}")
    print(f"Dates: {manifest['eligible_dates']:,}")
    print(f"Symbols: {manifest['symbols']:,}")
    for fold in manifest["folds"]:
        print(f"Fold: {fold['fold_id']} {fold['start']}..{fold['end']}")


if __name__ == "__main__":
    main()
