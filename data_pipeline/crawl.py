import argparse
import hashlib
import importlib.metadata
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .universe import load_universe


CALENDAR_SYMBOLS = {
    "HOSE": "VNINDEX",
    "HNX": "HNXINDEX",
    "UPCOM": "UPCOMINDEX",
}


def sha256_file(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class VnstockProvider:
    def __init__(self, source="kbs"):
        from vnstock import Quote

        self._quote_class = Quote
        self.source = source
        self.version = importlib.metadata.version("vnstock")

    def history(self, symbol, start, end):
        quote = self._quote_class(source=self.source, symbol=symbol)
        return quote.history(start=start, end=end, interval="1D")


def _write_raw_frame(frame, path):
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("Provider returned no rows")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def crawl_snapshot(universe_path, snapshot_id, start, end, out_dir, provider,
                   expected_size=150, request_delay=0.0):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", snapshot_id):
        raise ValueError("snapshot_id contains unsupported characters")

    universe_path = Path(universe_path)
    universe = load_universe(universe_path, expected_size=expected_size)
    snapshot_dir = Path(out_dir) / snapshot_id
    symbols_dir = snapshot_dir / "symbols"
    calendars_dir = snapshot_dir / "calendars"
    manifest_path = snapshot_dir / "crawl_manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        same_request = existing.get("request") == {
            "start": start, "end": end, "interval": "1D"
        }
        same_universe = existing.get("universe", {}).get("sha256") == sha256_file(universe_path)
        if not same_request or not same_universe:
            raise ValueError("Existing snapshot uses different request or universe inputs")
        if existing.get("status") == "complete":
            for relative_path, artifact in existing["artifacts"].items():
                path = snapshot_dir / relative_path
                if not path.exists() or sha256_file(path) != artifact["sha256"]:
                    raise ValueError(f"Complete snapshot artifact changed: {relative_path}")
            return manifest_path
    symbols_dir.mkdir(parents=True, exist_ok=True)
    calendars_dir.mkdir(parents=True, exist_ok=True)

    targets = [
        (row.symbol, symbols_dir / f"{row.symbol}.csv")
        for row in universe.itertuples(index=False)
    ]
    targets.extend(
        (symbol, calendars_dir / f"{exchange}.csv")
        for exchange, symbol in CALENDAR_SYMBOLS.items()
    )

    failures = {}
    artifacts = {}
    for _, path in targets:
        if path.exists():
            relative_path = path.relative_to(snapshot_dir).as_posix()
            artifacts[relative_path] = {
                "rows": len(pd.read_csv(path)),
                "sha256": sha256_file(path),
            }

    def write_manifest():
        manifest = {
            "snapshot_id": snapshot_id,
            "status": "complete" if len(artifacts) == len(targets) else "incomplete",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "provider": {
                "name": provider.__class__.__name__,
                "version": str(provider.version),
            },
            "request": {"start": start, "end": end, "interval": "1D"},
            "universe": {
                "path": universe_path.as_posix(),
                "rows": len(universe),
                "sha256": sha256_file(universe_path),
            },
            "calendar_symbols": CALENDAR_SYMBOLS,
            "failures": failures,
            "artifacts": dict(sorted(artifacts.items())),
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )

    for symbol, path in targets:
        if path.exists():
            continue
        try:
            _write_raw_frame(provider.history(symbol, start, end), path)
            relative_path = path.relative_to(snapshot_dir).as_posix()
            artifacts[relative_path] = {
                "rows": len(pd.read_csv(path)),
                "sha256": sha256_file(path),
            }
            failures.pop(symbol, None)
        except Exception as exc:
            failures[symbol] = str(exc)
        write_manifest()
        if request_delay > 0:
            time.sleep(request_delay)

    write_manifest()
    return manifest_path


def main():
    parser = argparse.ArgumentParser(description="Create an immutable VN150 raw snapshot")
    parser.add_argument("--universe", required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--source", default="kbs")
    parser.add_argument("--request-delay", type=float, default=3.2)
    args = parser.parse_args()

    manifest_path = crawl_snapshot(
        universe_path=args.universe,
        snapshot_id=args.snapshot_id,
        start=args.start,
        end=args.end,
        out_dir=args.out_dir,
        provider=VnstockProvider(source=args.source),
        request_delay=args.request_delay,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"Raw snapshot: {manifest_path}")
    print(f"Status: {manifest['status']}")
    if manifest["failures"]:
        print(f"Failures: {len(manifest['failures'])}")


if __name__ == "__main__":
    main()
