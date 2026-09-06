"""Check a GPU host before committing hours of inference to it.

Runs five checks and writes one JSON report:

1. environment    - python, torch, CUDA, GPU name and memory
2. prerequisites  - every path the screen runner needs, with sizes
3. correctness    - one real batch produces finite returns of the right shape
4. fingerprint    - a fixed batch under a fixed seed, hashed twice: once through
                    the sampler the runs actually use, and once with greedy
                    decoding, which is the only one of the two that separates a
                    wrong checkpoint from a difference in float32 rounding
5. throughput     - origins per second across arms, batch sizes, sample counts

It computes no metric, writes nothing except the report at `--output`, and
evaluates only dates the M2.5 screen already used, so it cannot leak information
about an unevaluated date.
"""

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_VERSION = "device_benchmark_v1"

# Fixed by construction so two hosts fingerprint the same work.
FINGERPRINT_ARM = "small_l126"
FINGERPRINT_ORIGINS = 8
FINGERPRINT_SEED = 20260901
HORIZON = 5
TEMPERATURE = 0.6
TOP_K = 0
TOP_P = 0.9
CLIP = 5.0
MAX_CONTEXT = 512

# A second, deterministic fingerprint. top_k=1 leaves one token after filtering,
# so softmax gives it probability 1 and the multinomial draw is forced. Sampling
# is what makes the ordinary fingerprint differ between hosts, so this is the
# only one of the two that can tell a wrong checkpoint from a rounding change.
GREEDY_TEMPERATURE = 1.0
GREEDY_TOP_K = 1
GREEDY_TOP_P = 1.0

ARM_SPECS = {
    "small_l63": ("pretrained/Kronos-small", 63, 63),
    "small_l126": ("pretrained/Kronos-small", 126, 126),
    "base_l126": ("pretrained/Kronos-base", 126, 126),
}

REQUIRED_PATHS = [
    ("tokenizer", "pretrained/Kronos-Tokenizer-base/model.safetensors"),
    ("kronos_small", "pretrained/Kronos-small/model.safetensors"),
    ("kronos_base", "pretrained/Kronos-base/model.safetensors"),
    ("curated_data", "data/curated/vn150_strict_v2/symbols"),
    ("dataset_manifest", "reports/milestone_1_data/vn150_strict_v2/dataset_manifest.json"),
    ("origin_registry", "data/evaluation/m2_1/common_origins.csv.gz"),
    ("registry_manifest", "reports/milestone_2_research_eval/origin_registry/manifest.json"),
]


def check_environment():
    import torch

    record = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_version": torch.version.cuda,
        "tf32_matmul": bool(torch.backends.cuda.matmul.allow_tf32),
        "tf32_cudnn": bool(torch.backends.cudnn.allow_tf32),
        "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
    }
    if record["cuda_available"]:
        properties = torch.cuda.get_device_properties(0)
        record["gpu_name"] = properties.name
        record["gpu_memory_gb"] = round(properties.total_memory / 1024**3, 2)
        record["gpu_capability"] = f"{properties.major}.{properties.minor}"
    return record


def check_prerequisites():
    records = []
    for name, relative in REQUIRED_PATHS:
        path = ROOT / relative
        if path.is_dir():
            files = sorted(path.glob("*.csv"))
            size = sum(item.stat().st_size for item in files)
            records.append(
                {
                    "name": name,
                    "path": relative,
                    "present": bool(files),
                    "detail": f"{len(files)} files, {size / 1024**2:.1f} MB",
                }
            )
        else:
            present = path.is_file()
            records.append(
                {
                    "name": name,
                    "path": relative,
                    "present": present,
                    "detail": (
                        f"{path.stat().st_size / 1024**2:.1f} MB" if present else "MISSING"
                    ),
                }
            )
    return records


def load_screen_slice(origin_count):
    """Load origins from dates the M2.5 screen already evaluated."""
    from evaluation.research.origins import OriginRegistryConfig, read_symbol_frame
    from evaluation.run_zero_shot_screen import select_dates

    registry = pd.read_csv(ROOT / "data/evaluation/m2_1/common_origins.csv.gz")
    registry["origin_date"] = pd.to_datetime(registry["origin_date"])
    screen_dates = select_dates(
        np.sort(registry["origin_date"].unique()), stride=10, residues=[0]
    )
    registry = registry[registry["origin_date"].isin(screen_dates)]
    registry = registry.sort_values(
        ["origin_date", "security_id"], kind="mergesort"
    ).head(origin_count).reset_index(drop=True)

    dataset_manifest = json.loads(
        (ROOT / "reports/milestone_1_data/vn150_strict_v2/dataset_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    source_config = OriginRegistryConfig(
        schema_version="m2_1_origin_registry_v1",
        dataset_id="vn150_strict_v2",
        dataset_dir=ROOT / "data/curated/vn150_strict_v2",
        dataset_manifest_path=ROOT
        / "reports/milestone_1_data/vn150_strict_v2/dataset_manifest.json",
        universe_path=Path("."),
        registry_path=ROOT / "data/evaluation/m2_1/common_origins.csv.gz",
        report_dir=Path("."),
        lookbacks=(63, 126),
        horizon=HORIZON,
        minimum_cross_section=10,
        lockbox_start=datetime(2026, 1, 1).date(),
        folds=(),
    )
    frames = {
        symbol: read_symbol_frame(source_config, dataset_manifest, symbol, security_id)
        for symbol, security_id in registry[["symbol", "security_id"]]
        .drop_duplicates()
        .itertuples(index=False)
    }
    return registry, frames


def _arm(arm_id):
    from evaluation.research.kronos_runner import ArmSpec

    model_path, lookback, normalizer = ARM_SPECS[arm_id]
    return ArmSpec(
        arm_id=arm_id,
        model_path=ROOT / model_path,
        lookback=lookback,
        normalizer_lookback=normalizer,
    )


def _predict(predictor, frames, rows, arm, sample_count, seed, device,
             temperature=TEMPERATURE, top_k=TOP_K, top_p=TOP_P):
    from evaluation.research.kronos_runner import build_batch, run_batch

    batch = build_batch(frames, rows, arm, clip=CLIP)
    return run_batch(
        predictor,
        batch,
        horizon=HORIZON,
        sample_count=sample_count,
        seed=seed,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
        device=device,
    )


def _fingerprint(values, rows, sample_count, seed, arm_id):
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    return {
        "arm_id": arm_id,
        "origins": int(len(rows)),
        "sample_count": sample_count,
        "seed": seed,
        "origin_ids": rows["origin_id"].tolist(),
        "sha256": hashlib.sha256(flat.tobytes()).hexdigest(),
        "mean": float(flat.mean()),
        "std": float(flat.std()),
        "first_five": [float(value) for value in flat[:5]],
    }


def check_correctness_and_fingerprint(registry, frames, device):
    """One fixed batch three ways: sampled twice for repeatability, then greedy."""
    from evaluation.research.kronos_runner import load_predictor

    arm = _arm(FINGERPRINT_ARM)
    rows = registry.head(FINGERPRINT_ORIGINS)
    predictor = load_predictor(
        ROOT / "pretrained/Kronos-Tokenizer-base",
        arm.model_path,
        device=device,
        max_context=MAX_CONTEXT,
        clip=CLIP,
    )
    first = _predict(predictor, frames, rows, arm, 10, FINGERPRINT_SEED, device)
    second = _predict(predictor, frames, rows, arm, 10, FINGERPRINT_SEED, device)
    greedy = _predict(
        predictor,
        frames,
        rows,
        arm,
        1,
        FINGERPRINT_SEED,
        device,
        temperature=GREEDY_TEMPERATURE,
        top_k=GREEDY_TOP_K,
        top_p=GREEDY_TOP_P,
    )
    del predictor

    correctness = {
        "shape": list(first.shape),
        "expected_shape": [len(rows), 10, HORIZON],
        "shape_ok": list(first.shape) == [len(rows), 10, HORIZON],
        "all_finite": bool(np.isfinite(first).all()),
        "max_abs_return": float(np.abs(first).max()),
        "plausible_magnitude": bool(np.abs(first).max() < 2.0),
        "repeatable_same_seed": bool(np.array_equal(first, second)),
        "max_repeat_delta": float(np.abs(first - second).max()),
    }
    fingerprint = _fingerprint(first, rows, 10, FINGERPRINT_SEED, arm.arm_id)
    greedy_fingerprint = _fingerprint(greedy, rows, 1, FINGERPRINT_SEED, arm.arm_id)
    greedy_fingerprint["decoding"] = "greedy"
    return correctness, fingerprint, greedy_fingerprint


def measure_throughput(registry, frames, device, arm_ids, batch_sizes, sample_counts,
                       origins_per_cell, warmup_batches):
    import torch

    from evaluation.research.kronos_runner import load_predictor

    results = []
    for arm_id in arm_ids:
        arm = _arm(arm_id)
        predictor = load_predictor(
            ROOT / "pretrained/Kronos-Tokenizer-base",
            arm.model_path,
            device=device,
            max_context=MAX_CONTEXT,
            clip=CLIP,
        )
        for sample_count in sample_counts:
            for batch_size in batch_sizes:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.reset_peak_memory_stats()
                try:
                    for index in range(warmup_batches):
                        rows = registry.iloc[
                            index * batch_size : (index + 1) * batch_size
                        ]
                        if rows.empty:
                            break
                        _predict(predictor, frames, rows, arm, sample_count, 1, device)

                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                    started = time.perf_counter()
                    done = 0
                    position = 0
                    while done < origins_per_cell:
                        rows = registry.iloc[position : position + batch_size]
                        if rows.empty:
                            position = 0
                            continue
                        _predict(predictor, frames, rows, arm, sample_count, 1, device)
                        done += len(rows)
                        position += batch_size
                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                    elapsed = time.perf_counter() - started
                    record = {
                        "arm_id": arm_id,
                        "sample_count": sample_count,
                        "batch_size": batch_size,
                        "effective_sequences": batch_size * sample_count,
                        "origins": done,
                        "seconds": round(elapsed, 3),
                        "origins_per_second": round(done / elapsed, 4),
                        "peak_vram_gb": round(
                            torch.cuda.max_memory_allocated() / 1024**3, 3
                        )
                        if torch.cuda.is_available()
                        else 0.0,
                        "status": "ok",
                    }
                except RuntimeError as error:
                    record = {
                        "arm_id": arm_id,
                        "sample_count": sample_count,
                        "batch_size": batch_size,
                        "effective_sequences": batch_size * sample_count,
                        "status": f"failed: {type(error).__name__}: {error}"[:200],
                    }
                results.append(record)
                print(
                    f"  {arm_id:<12} samples={sample_count:<3} batch={batch_size:<3} "
                    + (
                        f"{record['origins_per_second']:>7.2f} origins/s  "
                        f"VRAM {record['peak_vram_gb']:.2f} GB"
                        if record["status"] == "ok"
                        else record["status"]
                    ),
                    flush=True,
                )
        del predictor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return results


def project_cost(results, dates, origins_per_date=13431 / 98):
    """Turn the measured best rate per arm into hours for a full-registry run."""
    best = {}
    for record in results:
        if record["status"] != "ok":
            continue
        key = (record["arm_id"], record["sample_count"])
        if record["origins_per_second"] > best.get(key, {}).get("origins_per_second", 0):
            best[key] = record
    projections = []
    for (arm_id, sample_count), record in sorted(best.items()):
        origins = origins_per_date * dates
        projections.append(
            {
                "arm_id": arm_id,
                "sample_count": sample_count,
                "best_batch_size": record["batch_size"],
                "origins_per_second": record["origins_per_second"],
                "dates": dates,
                "projected_origins": int(round(origins)),
                "projected_hours": round(origins / record["origins_per_second"] / 3600, 2),
            }
        )
    return projections


def main(argv=None):
    parser = argparse.ArgumentParser(description="Benchmark a GPU host for M2 inference")
    parser.add_argument("--output", type=Path, default=Path("device_benchmark.json"))
    parser.add_argument("--arms", nargs="+", default=["small_l126", "base_l126"])
    parser.add_argument("--batch-sizes", nargs="+", type=int, default=[2, 8, 16, 32, 64])
    parser.add_argument("--sample-counts", nargs="+", type=int, default=[10, 20])
    parser.add_argument("--origins-per-cell", type=int, default=48)
    parser.add_argument("--warmup-batches", type=int, default=2)
    parser.add_argument("--project-dates", type=int, default=977)
    parser.add_argument("--skip-throughput", action="store_true")
    args = parser.parse_args(argv)
    # Created up front: the report is written after the grid, and a missing
    # directory would throw away a run that already took its full time.
    args.output.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 62)
    print("1. ENVIRONMENT")
    environment = check_environment()
    for key, value in environment.items():
        print(f"   {key:<18} {value}")
    if not environment["cuda_available"]:
        print("\n   CUDA is not available. Fix the environment before benchmarking.")

    print("\n2. PREREQUISITES")
    prerequisites = check_prerequisites()
    for record in prerequisites:
        mark = "ok " if record["present"] else "!! "
        print(f"   {mark}{record['name']:<18} {record['detail']:<24} {record['path']}")
    missing = [record["path"] for record in prerequisites if not record["present"]]
    if missing:
        print("\n   Missing inputs. Copy them to this host before running anything else:")
        for path in missing:
            print(f"     {path}")
        report = {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "environment": environment,
            "prerequisites": prerequisites,
            "missing": missing,
        }
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\n   Partial report written to {args.output}")
        return 1

    device = "cuda" if environment["cuda_available"] else "cpu"
    print(f"\n   Loading a slice of already-screened origins on {device} ...")
    needed = max(args.origins_per_cell, max(args.batch_sizes) * (args.warmup_batches + 1))
    registry, frames = load_screen_slice(max(needed, FINGERPRINT_ORIGINS))
    print(f"   {len(registry)} origins over {registry['origin_date'].nunique()} dates")

    print("\n3-4. CORRECTNESS AND FINGERPRINT")
    correctness, fingerprint, greedy_fingerprint = check_correctness_and_fingerprint(
        registry, frames, device
    )
    for key, value in correctness.items():
        print(f"   {key:<24} {value}")
    print(f"   sampled sha256           {fingerprint['sha256']}")
    print(f"   sampled mean/std         {fingerprint['mean']:.10f} / {fingerprint['std']:.10f}")
    print(f"   greedy sha256            {greedy_fingerprint['sha256']}")
    print(f"   greedy mean/std          {greedy_fingerprint['mean']:.10f} / {greedy_fingerprint['std']:.10f}")

    throughput = []
    projections = []
    if not args.skip_throughput:
        print("\n5. THROUGHPUT")
        throughput = measure_throughput(
            registry,
            frames,
            device,
            args.arms,
            args.batch_sizes,
            args.sample_counts,
            args.origins_per_cell,
            args.warmup_batches,
        )
        projections = project_cost(throughput, args.project_dates)
        print(f"\n   Projected full run over {args.project_dates} dates, best batch per arm:")
        for record in projections:
            print(
                f"     {record['arm_id']:<12} samples={record['sample_count']:<3} "
                f"batch={record['best_batch_size']:<3} "
                f"{record['projected_hours']:>6.2f} h"
            )

    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": platform.node(),
        "environment": environment,
        "prerequisites": prerequisites,
        "correctness": correctness,
        "fingerprint": fingerprint,
        "greedy_fingerprint": greedy_fingerprint,
        "throughput": throughput,
        "projections": projections,
        "settings": {
            "horizon": HORIZON,
            "temperature": TEMPERATURE,
            "top_k": TOP_K,
            "top_p": TOP_P,
            "greedy_temperature": GREEDY_TEMPERATURE,
            "greedy_top_k": GREEDY_TOP_K,
            "greedy_top_p": GREEDY_TOP_P,
            "clip": CLIP,
            "max_context": MAX_CONTEXT,
            "origins_per_cell": args.origins_per_cell,
            "warmup_batches": args.warmup_batches,
        },
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nReport written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
