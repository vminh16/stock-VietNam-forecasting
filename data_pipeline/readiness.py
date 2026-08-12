import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .contracts import (
    AMOUNT_POLICY,
    CANONICAL_TIMESTAMP_HOUR,
    CURATED_COLUMNS,
    FEATURE_COLUMNS,
    PRICE_COLUMNS,
)
from .transforms import normalize_lookback_window


def _window_count(lengths, lookback, horizon, training):
    extra = 0 if training else 1
    return sum(max(0, int(length) - lookback - horizon + extra) for length in lengths)


def _normalization_profile(frame, lookback, clip):
    windows = clipped = values = constant_features = 0
    for _, segment in frame.groupby("segment_id", sort=True):
        matrix = segment[FEATURE_COLUMNS].to_numpy(dtype=np.float64)
        for start in range(0, len(matrix) - lookback + 1, lookback):
            sample = matrix[start:start + lookback]
            normalized, mean, scale = normalize_lookback_window(
                sample, lookback, clip
            )
            unbounded = (sample - mean) / (scale + 1e-5)
            windows += 1
            clipped += int((np.abs(unbounded) > clip).sum())
            values += int(normalized.size)
            constant_features += int((sample.std(axis=0) < 1e-6).sum())
    return {
        "lookback": lookback,
        "sampled_nonoverlap_windows": windows,
        "clipped_values": clipped,
        "normalization_values": values,
        "clip_rate": clipped / values if values else 0.0,
        "constant_feature_windows": constant_features,
    }


def audit_data_readiness(dataset_dir, out_dir, lookbacks=(63, 126), horizon=5,
                         clip=5.0):
    dataset_dir = Path(dataset_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))

    blocking = set()
    symbol_rows = []
    normalization_rows = []
    for path in sorted((dataset_dir / "symbols").glob("*.csv")):
        frame = pd.read_csv(path)
        missing = set(CURATED_COLUMNS) - set(frame.columns)
        if missing:
            blocking.add("missing_required_columns")
            symbol_rows.append({"symbol": path.stem, "missing_columns": ",".join(sorted(missing))})
            continue

        frame["timestamps"] = pd.to_datetime(frame["timestamps"], errors="coerce")
        numeric = frame[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
        duplicate_count = int(frame.duplicated(["security_id", "session_id"]).sum())
        nonfinite_count = int((~np.isfinite(numeric.to_numpy())).any(axis=1).sum())
        invalid_ohlc = int((
            numeric["high"].lt(numeric[PRICE_COLUMNS].max(axis=1))
            | numeric["low"].gt(numeric[PRICE_COLUMNS].min(axis=1))
        ).sum())
        timestamp_mismatch = int((
            frame["timestamps"].isna()
            | frame["timestamps"].dt.hour.ne(CANONICAL_TIMESTAMP_HOUR)
            | frame["timestamps"].dt.minute.ne(0)
        ).sum())
        segment_gaps = 0
        lengths = []
        for _, segment in frame.groupby("segment_id", sort=True):
            lengths.append(len(segment))
            segment_gaps += int(~segment["session_id"].diff().dropna().eq(1).all())

        if duplicate_count:
            blocking.add("duplicate_symbol_session")
        if nonfinite_count:
            blocking.add("nonfinite_features")
        if invalid_ohlc:
            blocking.add("invalid_ohlc")
        if timestamp_mismatch:
            blocking.add("noncanonical_timestamp")
        if segment_gaps:
            blocking.add("session_gap_inside_segment")

        amount_proxy = numeric["volume"] * numeric[PRICE_COLUMNS].mean(axis=1)
        denominator = amount_proxy.abs().clip(lower=1e-12)
        amount_error = numeric["amount"].sub(amount_proxy).abs().div(denominator)
        row = {
            "symbol": path.stem,
            "rows": len(frame),
            "segments": len(lengths),
            "duplicate_symbol_session": duplicate_count,
            "nonfinite_features": nonfinite_count,
            "invalid_ohlc": invalid_ohlc,
            "noncanonical_timestamp": timestamp_mismatch,
            "session_gap_inside_segment": segment_gaps,
            "amount_proxy_max_relative_error": float(amount_error.max()) if len(frame) else 0.0,
        }
        for lookback in lookbacks:
            row[f"training_windows_l{lookback}_h{horizon}"] = _window_count(
                lengths, lookback, horizon, training=True
            )
            row[f"evaluation_origins_l{lookback}_h{horizon}"] = _window_count(
                lengths, lookback, horizon, training=False
            )
            profile = _normalization_profile(frame, lookback, clip)
            profile["symbol"] = path.stem
            normalization_rows.append(profile)
        symbol_rows.append(row)

    symbols = pd.DataFrame(symbol_rows).sort_values("symbol").reset_index(drop=True)
    normalization = pd.DataFrame(normalization_rows).sort_values(
        ["lookback", "symbol"]
    ).reset_index(drop=True)
    symbols.to_csv(out_dir / "symbol_readiness.csv", index=False, lineterminator="\n")
    normalization.to_csv(
        out_dir / "normalization_diagnostics.csv", index=False, lineterminator="\n"
    )

    conditional = []
    adjustment_status = manifest.get("price_adjustment_status", "unrecorded")
    amount_policy = manifest.get("amount_policy", "unrecorded")
    if adjustment_status != "verified_adjusted":
        conditional.append(adjustment_status)
    if amount_policy == AMOUNT_POLICY:
        conditional.append(amount_policy)

    status = "BLOCKED" if blocking else "CONDITIONAL" if conditional else "PASS"
    continuity_path = dataset_dir / "continuity_candidates.csv"
    if continuity_path.exists():
        continuity_candidates = pd.read_csv(continuity_path)
    else:
        continuity_candidates = pd.DataFrame(
            columns=[
                "security_id", "symbol", "timestamps", "reason",
                "overnight_return", "threshold",
            ]
        )
    continuity_candidates.to_csv(
        out_dir / "continuity_candidates.csv", index=False, lineterminator="\n"
    )
    continuity_count = len(continuity_candidates)
    clip_summary = (
        normalization.groupby("lookback").agg(
            sampled_nonoverlap_windows=("sampled_nonoverlap_windows", "sum"),
            clipped_values=("clipped_values", "sum"),
            normalization_values=("normalization_values", "sum"),
            constant_feature_windows=("constant_feature_windows", "sum"),
        ).reset_index()
        if len(normalization)
        else pd.DataFrame()
    )
    if len(clip_summary):
        clip_summary["clip_rate"] = (
            clip_summary["clipped_values"] / clip_summary["normalization_values"]
        )

    summary = {
        "dataset_id": manifest.get("dataset_id"),
        "policy_version": manifest.get("policy_version"),
        "status": status,
        "blocking_findings": sorted(blocking),
        "conditional_findings": conditional,
        "symbols": int(len(symbols)),
        "rows": int(symbols.get("rows", pd.Series(dtype=int)).fillna(0).sum()),
        "segments": int(symbols.get("segments", pd.Series(dtype=int)).fillna(0).sum()),
        "continuity_candidates": continuity_count,
        "price_adjustment_status": adjustment_status,
        "amount_policy": amount_policy,
        "normalization": clip_summary.to_dict(orient="records"),
    }
    (out_dir / "readiness_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    window_lines = []
    for lookback in lookbacks:
        training_column = f"training_windows_l{lookback}_h{horizon}"
        origin_column = f"evaluation_origins_l{lookback}_h{horizon}"
        window_lines.append(
            f"- `L={lookback}, H={horizon}`: "
            f"{int(symbols.get(training_column, pd.Series(dtype=int)).fillna(0).sum())} training windows; "
            f"{int(symbols.get(origin_column, pd.Series(dtype=int)).fillna(0).sum())} evaluation origins."
        )
    normalization_table = clip_summary.to_string(index=False) if len(clip_summary) else "No windows"
    report = f"""# VN150 Data Readiness

## Decision

**{status}.** The dataset has no structural blocker only when the blocking list
below is empty. A conditional result permits evaluation-harness work, but not an
unqualified claim that provider prices are corporate-action adjusted.

## Dataset

- Dataset: `{summary['dataset_id']}` (`{summary['policy_version']}`)
- Symbols: {summary['symbols']}
- Valid rows: {summary['rows']}
- Contiguous segments: {summary['segments']}
- Large overnight jumps retained for review: {continuity_count}
- Price adjustment status: `{adjustment_status}`
- Amount policy: `{amount_policy}`

## Structural Findings

- Blocking findings: {', '.join(sorted(blocking)) or 'none'}
- Conditional findings: {', '.join(conditional) or 'none'}

## Window Contract

{chr(10).join(window_lines)}

Training uses `L+H+1` rows for next-token loss. Evaluation uses `L+H` rows.
Neither count is an effective sample size.

## Normalization Diagnostics

```text
{normalization_table}
```

Normalization is local Z-score using lookback rows only, with scale `1.0` for
near-constant features and clipping at `[-{clip}, {clip}]`.

## Interpretation

- KBS `history()` exposes OHLCV in thousand-VND price units but does not attach
  a machine-readable adjusted-price guarantee in the retained payload.
- The pipeline preserves provider OHLC and records jumps above 17% for review.
  It does not split or rewrite observations without a point-in-time reference
  price or corporate-action factor.
- `amount` is a deterministic Kronos-compatibility proxy, not reported turnover.
- The fixed current VN150 population remains survivorship-biased by construction.

## Source Notes

- Vnstock 4.0.x KBS history implementation and price-unit behavior:
  https://github.com/thinh-vu/vnstock
- Vnstock release notes for KBS thousand-VND normalization:
  https://vnstocks.com/docs/tai-lieu/lich-su-phien-ban
- Official Kronos repository and six-feature K-line contract:
  https://github.com/shiyu-coder/Kronos
"""
    report_path = out_dir / "data_readiness_report.md"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Audit model readiness of a strict dataset")
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    print(f"Data readiness report: {audit_data_readiness(args.dataset_dir, args.out_dir)}")


if __name__ == "__main__":
    main()
