import argparse
import json
from pathlib import Path

import pandas as pd


def _window_count(lengths, lookback, horizon):
    return sum(max(0, int(length) - lookback - horizon) for length in lengths)


def audit_dataset(dataset_dir, out_dir, lookbacks=(63, 126), horizon=5):
    dataset_dir = Path(dataset_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    exclusions = pd.read_csv(dataset_dir / "exclusions.csv")

    rows = []
    amount_source_counts = {}
    for symbol, stats in sorted(manifest["symbols"].items()):
        frame = pd.read_csv(dataset_dir / "symbols" / f"{symbol}.csv")
        frame["timestamps"] = pd.to_datetime(frame["timestamps"], errors="coerce")
        segment_lengths = frame.groupby("segment_id").size().tolist() if len(frame) else []
        for source, count in frame["amount_source"].value_counts().items():
            amount_source_counts[source] = amount_source_counts.get(source, 0) + int(count)
        symbol_exclusions = exclusions[exclusions["symbol"] == symbol]
        row = {
            "symbol": symbol,
            "exchange": frame["security_id"].iloc[0].split("_", 1)[0] if len(frame) else "",
            "raw_rows": stats["raw_rows"],
            "valid_rows": len(frame),
            "excluded_records": len(symbol_exclusions),
            "first_valid": frame["timestamps"].min() if len(frame) else "",
            "last_valid": frame["timestamps"].max() if len(frame) else "",
            "segments": len(segment_lengths),
            "max_segment_rows": max(segment_lengths, default=0),
            "minimum_history_252": len(frame) >= 252,
        }
        for lookback in lookbacks:
            row[f"windows_l{lookback}_h{horizon}"] = _window_count(
                segment_lengths, lookback, horizon
            )
        rows.append(row)

    quality = pd.DataFrame(rows)
    quality_path = out_dir / "data_quality.csv"
    quality.to_csv(quality_path, index=False, lineterminator="\n")
    (out_dir / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    reason_counts = exclusions["reason"].value_counts().sort_index().to_dict()
    calendar_lines = []
    for path in sorted((dataset_dir / "calendars").glob("*.csv")):
        calendar = pd.read_csv(path)
        dates = pd.to_datetime(calendar["session_date"])
        calendar_lines.append(
            f"- {path.stem}: {len(calendar)} sessions, "
            f"{dates.min().date()} to {dates.max().date()}"
        )
    exchange_summary = quality.groupby("exchange").agg(
        symbols=("symbol", "count"),
        raw_rows=("raw_rows", "sum"),
        valid_rows=("valid_rows", "sum"),
        segments=("segments", "sum"),
    )
    short_history_symbols = ", ".join(
        quality.loc[~quality["minimum_history_252"], "symbol"].tolist()
    ) or "none"
    window_lines = [
        f"- `L={lookback}, H={horizon}`: "
        f"{int(quality[f'windows_l{lookback}_h{horizon}'].sum())} windows"
        for lookback in lookbacks
    ]
    report = f"""# VN150 Strict Data Quality Report

Dataset: `{manifest['dataset_id']}`

## Coverage

- Symbols: {len(quality)}
- Raw rows: {int(quality['raw_rows'].sum())}
- Valid rows: {int(quality['valid_rows'].sum())}
- Contiguous segments: {int(quality['segments'].sum())}
- Symbols below 252 valid sessions: {int((~quality['minimum_history_252']).sum())}
- Short-history symbols: {short_history_symbols}
- First valid bar: {quality['first_valid'].min()}
- Last valid bar: {quality['last_valid'].max()}

## Amount Provenance

```json
{json.dumps(amount_source_counts, indent=2, ensure_ascii=True)}
```

## Calendar Coverage

{chr(10).join(calendar_lines)}

## Exchange Summary

```text
{exchange_summary.to_string()}
```

## Window Availability

{chr(10).join(window_lines)}

These are dependent observations from overlapping windows, not an effective
sample size.

## Exclusions

```json
{json.dumps(reason_counts, indent=2, ensure_ascii=True)}
```
"""
    report_path = out_dir / "data_quality_report.md"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Audit a strict VN150 dataset")
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    report_path = audit_dataset(args.dataset_dir, args.out_dir)
    print(f"Data quality report: {report_path}")


if __name__ == "__main__":
    main()
