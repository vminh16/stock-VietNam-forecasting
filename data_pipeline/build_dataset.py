import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .contracts import (
    AMOUNT_POLICY,
    CANONICAL_TIMESTAMP_HOUR,
    CURATED_COLUMNS,
    FEATURE_COLUMNS,
    PRICE_ADJUSTMENT_STATUS,
    PRICE_COLUMNS,
    PRICE_UNIT,
    RAW_COLUMNS,
    continuity_candidate_threshold,
)
from .crawl import sha256_file
from .universe import load_universe

CONTINUITY_CANDIDATE_COLUMNS = [
    "security_id", "symbol", "timestamps", "reason", "overnight_return", "threshold",
]


def _load_calendar(path):
    frame = pd.read_csv(path)
    timestamp_column = "time" if "time" in frame.columns else "timestamps"
    if timestamp_column not in frame.columns:
        raise ValueError(f"Calendar has no timestamp column: {path}")
    dates = pd.to_datetime(frame[timestamp_column], errors="coerce").dt.normalize()
    if dates.isna().any():
        raise ValueError(f"Calendar contains invalid timestamps: {path}")
    dates = pd.Series(sorted(dates.drop_duplicates()))
    return pd.DataFrame({"session_date": dates, "session_id": range(len(dates))})


def _prepare_symbol(raw, security_id, symbol, exchange, calendar):
    timestamp_column = "time" if "time" in raw.columns else "timestamps"
    required = set(RAW_COLUMNS + [timestamp_column])
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"{symbol} is missing columns: {sorted(missing)}")

    raw = raw.copy()
    raw["_raw_order"] = range(len(raw))
    raw["session_date"] = pd.to_datetime(raw[timestamp_column], errors="coerce").dt.normalize()
    for column in RAW_COLUMNS + (["amount"] if "amount" in raw.columns else []):
        raw[column] = pd.to_numeric(raw[column], errors="coerce")

    exclusions = []
    invalid_timestamp = raw["session_date"].isna()
    exclusions.extend(
        (security_id, symbol, "", "invalid_timestamp")
        for _ in range(int(invalid_timestamp.sum()))
    )
    raw = raw[~invalid_timestamp].copy()

    comparison_columns = [
        column for column in raw.columns
        if column not in {timestamp_column, "_raw_order", "session_date"}
    ]
    distinct_per_date = raw.groupby("session_date")[comparison_columns].nunique(dropna=False)
    conflict_dates = set(distinct_per_date.index[distinct_per_date.max(axis=1) > 1])
    conflict_mask = raw["session_date"].isin(conflict_dates)
    exclusions.extend(
        (security_id, symbol, date, "duplicate_conflict")
        for date in raw.loc[conflict_mask, "session_date"]
    )
    raw = raw[~conflict_mask].copy()

    identical_duplicate = raw.duplicated("session_date", keep="first")
    exclusions.extend(
        (security_id, symbol, date, "duplicate_identical")
        for date in raw.loc[identical_duplicate, "session_date"]
    )
    candidates = raw[~identical_duplicate].copy()

    calendar_dates = set(calendar["session_date"])
    before_or_after_coverage = (
        candidates["session_date"].lt(calendar["session_date"].min())
        | candidates["session_date"].gt(calendar["session_date"].max())
    )
    exclusions.extend(
        (security_id, symbol, date, "outside_calendar_coverage")
        for date in candidates.loc[before_or_after_coverage, "session_date"]
    )
    outside_calendar = ~candidates["session_date"].isin(calendar_dates)
    inside_non_session = outside_calendar & ~before_or_after_coverage
    exclusions.extend(
        (security_id, symbol, date, "not_exchange_session")
        for date in candidates.loc[inside_non_session, "session_date"]
    )
    candidates = candidates[~outside_calendar]
    if candidates.empty:
        return pd.DataFrame(columns=CURATED_COLUMNS), exclusions, []

    expected = calendar[calendar["session_date"] >= candidates["session_date"].min()].copy()
    merged = expected.merge(candidates, on="session_date", how="left", sort=True)
    present = merged["_raw_order"].notna()
    numeric = merged[RAW_COLUMNS].to_numpy(dtype=float)
    finite = pd.Series(np.isfinite(numeric).all(axis=1), index=merged.index)
    positive_prices = merged[PRICE_COLUMNS].gt(0).all(axis=1)
    coherent = (
        merged["high"].ge(merged[["open", "close", "low"]].max(axis=1))
        & merged["low"].le(merged[["open", "close", "high"]].min(axis=1))
    )
    positive_volume = merged["volume"].gt(0)
    valid = present & finite & positive_prices & coherent & positive_volume
    if "amount" in merged.columns:
        valid &= merged["amount"].isna() | merged["amount"].gt(0)

    reasons = pd.Series("", index=merged.index, dtype=object)
    reasons.loc[~present] = "missing_session"
    reasons.loc[present & ~finite] = "non_finite"
    reasons.loc[present & finite & (~positive_prices | ~coherent)] = "invalid_ohlc"
    zero_trade = present & finite & positive_prices & coherent & ~positive_volume
    if "amount" in merged.columns:
        zero_trade |= present & merged["amount"].notna() & merged["amount"].le(0)
    reasons.loc[zero_trade] = "zero_trade"
    conflict_expected = merged["session_date"].isin(conflict_dates) & ~present
    reasons.loc[conflict_expected] = ""
    exclusions.extend(
        (security_id, symbol, row.session_date, row.reason)
        for row in pd.DataFrame(
            {"session_date": merged["session_date"], "reason": reasons}
        ).itertuples(index=False)
        if row.reason
    )

    threshold = continuity_candidate_threshold(exchange)
    previous_valid = valid.shift(1, fill_value=False)
    overnight_return = merged["open"].div(merged["close"].shift(1)).sub(1.0)
    large_jump = valid & previous_valid & overnight_return.abs().gt(threshold)
    continuity_candidates = [
        (
            security_id,
            symbol,
            row.session_date,
            "large_overnight_jump",
            float(row.overnight_return),
            threshold,
        )
        for row in pd.DataFrame(
            {
                "session_date": merged["session_date"],
                "overnight_return": overnight_return,
                "large_jump": large_jump,
            }
        ).itertuples(index=False)
        if row.large_jump
    ]

    segment_start = valid & ~previous_valid
    curated = merged[valid].copy()
    curated["security_id"] = security_id
    curated["symbol"] = symbol
    curated["timestamps"] = (
        curated["session_date"] + pd.Timedelta(hours=CANONICAL_TIMESTAMP_HOUR)
    )
    curated["segment_id"] = segment_start[valid].cumsum().to_numpy() - 1
    if "amount" in curated.columns:
        has_provider_amount = curated["amount"].notna()
    else:
        curated["amount"] = np.nan
        has_provider_amount = pd.Series(False, index=curated.index)
    derived_amount = curated["volume"] * curated[PRICE_COLUMNS].mean(axis=1)
    curated["amount"] = curated["amount"].where(has_provider_amount, derived_amount)
    curated["amount_source"] = np.where(
        has_provider_amount, "provider", "derived_ohlc4"
    )
    return curated[CURATED_COLUMNS].reset_index(drop=True), exclusions, continuity_candidates


def build_dataset(raw_dir, universe_path, dataset_id, out_dir, expected_size=150):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", dataset_id):
        raise ValueError("dataset_id contains unsupported characters")

    raw_dir = Path(raw_dir)
    universe_path = Path(universe_path)
    universe = load_universe(universe_path, expected_size=expected_size)
    raw_manifest_path = raw_dir / "crawl_manifest.json"
    raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    if raw_manifest.get("status") != "complete":
        raise ValueError("Raw snapshot manifest is not complete")

    for relative_path, artifact in raw_manifest["artifacts"].items():
        path = raw_dir / relative_path
        if not path.exists() or sha256_file(path) != artifact["sha256"]:
            raise ValueError(f"Raw artifact hash mismatch: {relative_path}")

    dataset_dir = Path(out_dir) / dataset_id
    symbols_dir = dataset_dir / "symbols"
    calendars_dir = dataset_dir / "calendars"
    if dataset_dir.exists():
        raise FileExistsError(f"Dataset already exists: {dataset_dir}")
    symbols_dir.mkdir(parents=True)
    calendars_dir.mkdir()

    calendars = {}
    for exchange in ("HOSE", "HNX", "UPCOM"):
        calendar = _load_calendar(raw_dir / "calendars" / f"{exchange}.csv")
        calendars[exchange] = calendar
        calendar.to_csv(
            calendars_dir / f"{exchange}.csv", index=False,
            date_format="%Y-%m-%d", lineterminator="\n",
        )

    all_exclusions = []
    all_continuity_candidates = []
    symbol_stats = {}
    for item in universe.itertuples(index=False):
        raw = pd.read_csv(raw_dir / "symbols" / f"{item.symbol}.csv")
        curated, exclusions, continuity_candidates = _prepare_symbol(
            raw, item.security_id, item.symbol, item.exchange, calendars[item.exchange]
        )
        curated.to_csv(
            symbols_dir / f"{item.symbol}.csv", index=False,
            date_format="%Y-%m-%d %H:%M:%S", lineterminator="\n",
        )
        all_exclusions.extend(exclusions)
        all_continuity_candidates.extend(continuity_candidates)
        symbol_stats[item.symbol] = {
            "raw_rows": len(raw),
            "valid_rows": len(curated),
            "segments": int(curated["segment_id"].nunique()) if len(curated) else 0,
            "continuity_candidates": len(continuity_candidates),
        }

    exclusions = pd.DataFrame(
        all_exclusions,
        columns=["security_id", "symbol", "timestamps", "reason"],
    ).sort_values(["symbol", "timestamps", "reason"])
    exclusions.to_csv(
        dataset_dir / "exclusions.csv", index=False,
        date_format="%Y-%m-%d", lineterminator="\n",
    )

    continuity_candidates = pd.DataFrame(
        all_continuity_candidates, columns=CONTINUITY_CANDIDATE_COLUMNS
    ).sort_values(["symbol", "timestamps"])
    continuity_candidates.to_csv(
        dataset_dir / "continuity_candidates.csv",
        index=False,
        date_format="%Y-%m-%d",
        lineterminator="\n",
    )

    artifact_hashes = {}
    for path in sorted(dataset_dir.rglob("*.csv")):
        artifact_hashes[path.relative_to(dataset_dir).as_posix()] = sha256_file(path)

    manifest = {
        "dataset_id": dataset_id,
        "status": "complete",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy_version": "strict_v2",
        "missing_policy": "split_no_imputation",
        "continuity_policy": "audit_large_jumps_no_price_rewrite",
        "continuity_thresholds": {
            exchange: continuity_candidate_threshold(exchange)
            for exchange in ("HOSE", "HNX", "UPCOM")
        },
        "price_unit": PRICE_UNIT,
        "price_adjustment_status": PRICE_ADJUSTMENT_STATUS,
        "timestamp_policy": f"session_date_plus_{CANONICAL_TIMESTAMP_HOUR:02d}:00",
        "feature_order": FEATURE_COLUMNS,
        "amount_policy": AMOUNT_POLICY,
        "raw_manifest_sha256": sha256_file(raw_manifest_path),
        "raw_snapshot_manifest": raw_manifest,
        "universe_sha256": sha256_file(universe_path),
        "symbols": symbol_stats,
        "artifact_hashes": artifact_hashes,
    }
    manifest_path = dataset_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main():
    parser = argparse.ArgumentParser(description="Build a strict segmented VN150 dataset")
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--universe", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    manifest_path = build_dataset(
        args.raw_dir, args.universe, args.dataset_id, args.out_dir
    )
    print(f"Curated dataset: {manifest_path}")


if __name__ == "__main__":
    main()
