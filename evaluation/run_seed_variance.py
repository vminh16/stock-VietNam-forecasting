"""Measure how much a Kronos metric moves when only the RNG stream changes.

SPEC section 8.11. The replicates are produced by the ordinary screen runner
from `m2_9_seed_variance.yaml`; this script only reads their per-date metrics,
so it needs no GPU and no model weights.

The primary readout is the standard deviation of pooled RankIC across the
replicates, compared against the threshold section 8.11 fixed in advance.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.research.metrics import summarize_metrics

SCHEMA_VERSION = "m2_9_seed_variance_v1"

# SPEC 8.11 decision rule, fixed before any replicate was computed. The M2.8
# primary contrast spans a half-width of 0.0295 on these same 196 dates.
M2_8_HALF_WIDTH = 0.0295
NORMAL_QUANTILE = 1.96
SIGMA_DATE = M2_8_HALF_WIDTH / NORMAL_QUANTILE
TOLERATED_RATIO = 0.25
PRIMARY_METRIC = "RankIC"
REPORTED_METRICS = (
    "DA",
    "MW-DA",
    "RankIC",
    "HitRate@Top10",
    "CRPS",
    "coverage",
    "interval_width",
)


def load_replicates(config_path):
    raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    output_dir = ROOT / raw["output_dir"]
    report_dir = ROOT / raw["report_dir"]
    arm_ids = [str(arm["arm_id"]) for arm in raw["arms"]]
    if len(arm_ids) < 3:
        raise ValueError("A standard deviation over fewer than 3 replicates is not usable")

    summaries = {}
    for arm_id in arm_ids:
        path = output_dir / f"{arm_id}_per_date_metrics.csv.gz"
        if not path.exists():
            raise FileNotFoundError(f"Replicate not computed: {path}")
        dates = pd.read_csv(path)
        summaries[arm_id] = summarize_metrics(dates)
    return arm_ids, summaries, report_dir


def spread(summaries, arm_ids, metric):
    values = pd.Series([summaries[arm_id][metric] for arm_id in arm_ids])
    return {
        "metric": metric,
        "values": [float(value) for value in values],
        "mean": float(values.mean()),
        "sd": float(values.std(ddof=1)),
        "min": float(values.min()),
        "max": float(values.max()),
        "range": float(values.max() - values.min()),
    }


def read_decision(sd_seed):
    """Apply SPEC 8.11 rules 4 and 5 exactly as registered."""
    threshold = TOLERATED_RATIO * SIGMA_DATE
    material = sd_seed > threshold
    inflation = (SIGMA_DATE**2 + sd_seed**2) ** 0.5 / SIGMA_DATE
    return {
        "sd_seed": float(sd_seed),
        "sigma_date": float(SIGMA_DATE),
        "threshold": float(threshold),
        "interval_inflation_factor": float(inflation),
        "material": bool(material),
        "rule": "8.11.5" if material else "8.11.4",
    }


def run(config_path, command=None):
    arm_ids, summaries, report_dir = load_replicates(config_path)
    spreads = {metric: spread(summaries, arm_ids, metric) for metric in REPORTED_METRICS}
    decision = read_decision(spreads[PRIMARY_METRIC]["sd"])

    dates_seen = {summaries[arm_id]["valid_dates"] for arm_id in arm_ids}
    origins_seen = {summaries[arm_id]["origin_rows"] for arm_id in arm_ids}
    if len(dates_seen) != 1 or len(origins_seen) != 1:
        raise ValueError("Replicates do not share one evaluation set")

    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "config": str(Path(config_path).as_posix()),
        "replicates": arm_ids,
        "valid_dates": dates_seen.pop(),
        "origin_rows": origins_seen.pop(),
        "primary_metric": PRIMARY_METRIC,
        "decision": decision,
        "spreads": spreads,
        "per_replicate": summaries,
    }

    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "seed_variance.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    _write_markdown(report_dir / "seed_variance.md", report)
    return report


def _write_markdown(path, report):
    rows = "\n".join(
        f"| `{name}` | " + " | ".join(f"{value:.4f}" for value in item["values"])
        + f" | {item['sd']:.6f} |"
        for name, item in report["spreads"].items()
    )
    decision = report["decision"]
    verdict = (
        "material, SPEC 8.11 rule 5 applies"
        if decision["material"]
        else "immaterial, SPEC 8.11 rule 4 applies"
    )
    path.write_text(
        f"""# M2.9 Sampling-Noise Budget

Read against SPEC section 8.11, registered before any replicate was computed.
{len(report['replicates'])} replicates of `small_l126` over
{report['valid_dates']} dates and {report['origin_rows']:,} origins. The
replicates differ only in their RNG stream.

| metric | {' | '.join(report['replicates'])} | sd |
|---|{'---|' * len(report['replicates'])}---|
{rows}

## Decision

`sd_seed` on {report['primary_metric']} is `{decision['sd_seed']:.6f}` against a
registered threshold of `{decision['threshold']:.6f}`
(`0.25 * sigma_date`, `sigma_date = {decision['sigma_date']:.6f}`).

Sampling noise is **{verdict}**. Combining it with date-resampling noise widens
every reported interval by a factor of
`{decision['interval_inflation_factor']:.4f}`.
""",
        encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read the M2.9 sampling-noise budget")
    parser.add_argument(
        "--config", type=Path, default=ROOT / "evaluation/configs/m2_9_seed_variance.yaml"
    )
    args = parser.parse_args(argv)
    report = run(args.config, command=" ".join(sys.argv))
    decision = report["decision"]
    for name, item in report["spreads"].items():
        print(f"  {name:<16} sd={item['sd']:.6f}  range={item['range']:.6f}")
    print(
        f"\nsd_seed({report['primary_metric']}) = {decision['sd_seed']:.6f} "
        f"vs threshold {decision['threshold']:.6f} -> "
        f"{'MATERIAL' if decision['material'] else 'immaterial'} (rule {decision['rule']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
