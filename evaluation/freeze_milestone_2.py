"""Freeze the evidence M2 was closed on, as SPEC section 11.4 steps 1 and 4 require.

Hashes every registration, evidence file, config, report and evaluation output
the M2 decisions rest on, and checks that no origin or target reached the 2026
lockbox. Writes one manifest; it reads everything and changes nothing.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.crawl import sha256_file  # noqa: E402

FREEZE_ID = "milestone_2_closeout"
LOCKBOX_START = "2026-01-01"
REGISTRY = Path("data/evaluation/m2_1/common_origins.csv.gz")
EVALUATION_DIR = Path("data/evaluation")
FROZEN = [
    Path("docs/registrations"),
    Path("docs/evidence"),
    Path("evaluation/configs"),
    Path("reports/milestone_2_research_eval"),
    EVALUATION_DIR,
]
OUTPUT = Path("reports/milestone_2_research_eval/closeout/manifest.json")


def collect_hashes(root, paths):
    hashes = {}
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
        for file in files:
            hashes[file.relative_to(root).as_posix()] = sha256_file(file)
    return dict(sorted(hashes.items()))


def check_lockbox(registry_path, evaluation_dir, lockbox_start):
    registry = pd.read_csv(registry_path, usecols=["origin_date", "target_end_date"])
    latest_target = str(registry["target_end_date"].max())
    latest_origin = str(registry["origin_date"].max())
    files = sorted(Path(evaluation_dir).rglob("*per_date_metrics.csv.gz"))
    for file in files:
        latest_origin = max(latest_origin, str(pd.read_csv(file, usecols=["origin_date"])["origin_date"].max()))
    return {
        "lockbox_start": lockbox_start,
        "latest_origin_date": latest_origin,
        "latest_target_end_date": latest_target,
        "per_date_files_checked": len(files),
        "lockbox_opened": latest_target >= lockbox_start or latest_origin >= lockbox_start,
    }


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def freeze(root=ROOT):
    hashes = collect_hashes(root, [root / p for p in FROZEN])
    hashes.pop(OUTPUT.as_posix(), None)  # the manifest cannot hash itself
    return {
        "freeze_id": FREEZE_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_revision": _git("rev-parse", "HEAD"),
        "worktree_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "registry_sha256": sha256_file(root / REGISTRY),
        "lockbox": check_lockbox(root / REGISTRY, root / EVALUATION_DIR, LOCKBOX_START),
        "artifact_count": len(hashes),
        "artifact_hashes": hashes,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    manifest = freeze()
    if manifest["lockbox"]["lockbox_opened"]:
        raise SystemExit(f"Lockbox reached: {manifest['lockbox']}")
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{manifest['artifact_count']} artifacts hashed at {manifest['code_revision'][:7]}; "
          f"lockbox opened: {manifest['lockbox']['lockbox_opened']}")


if __name__ == "__main__":
    main()
