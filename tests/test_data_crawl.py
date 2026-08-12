import json
from pathlib import Path

import pandas as pd

from data_pipeline.crawl import crawl_snapshot, sha256_file


class FakeProvider:
    version = "test-provider"

    def __init__(self, failing=None):
        self.failing = set(failing or [])
        self.calls = []

    def history(self, symbol, start, end):
        self.calls.append(symbol)
        if symbol in self.failing:
            raise RuntimeError("provider failure")
        return pd.DataFrame(
            {
                "time": ["2024-01-02", "2024-01-03"],
                "open": [10, 11],
                "high": [11, 12],
                "low": [9, 10],
                "close": [10.5, 11.5],
                "volume": [100, 200],
            }
        )


def write_universe(path):
    pd.DataFrame(
        [
            ["HOSE_AAA", "AAA", "HOSE", "2026-08-09"],
            ["HNX_BBB", "BBB", "HNX", "2026-08-09"],
        ],
        columns=["security_id", "symbol", "exchange", "included_as_of"],
    ).to_csv(path, index=False)


def test_crawl_writes_raw_files_and_manifest(tmp_path):
    universe_path = tmp_path / "universe.csv"
    write_universe(universe_path)
    provider = FakeProvider()

    manifest_path = crawl_snapshot(
        universe_path=universe_path,
        snapshot_id="test-snapshot",
        start="2024-01-01",
        end="2024-01-31",
        out_dir=tmp_path / "raw",
        provider=provider,
        expected_size=2,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert set(provider.calls) == {"AAA", "BBB", "VNINDEX", "HNXINDEX", "UPCOMINDEX"}
    assert len(manifest["artifacts"]) == 5
    for relative_path, artifact in manifest["artifacts"].items():
        path = manifest_path.parent / relative_path
        assert artifact["sha256"] == sha256_file(path)
        assert artifact["rows"] == 2


def test_crawl_resume_does_not_overwrite_existing_files(tmp_path):
    universe_path = tmp_path / "universe.csv"
    write_universe(universe_path)
    provider = FakeProvider(failing={"BBB"})

    manifest_path = crawl_snapshot(
        universe_path, "resume", "2024-01-01", "2024-01-31",
        tmp_path / "raw", provider, expected_size=2,
    )
    first_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    aaa_path = manifest_path.parent / "symbols" / "AAA.csv"
    original_bytes = aaa_path.read_bytes()
    assert first_manifest["status"] == "incomplete"

    resumed_provider = FakeProvider()
    crawl_snapshot(
        universe_path, "resume", "2024-01-01", "2024-01-31",
        tmp_path / "raw", resumed_provider, expected_size=2,
    )

    assert "AAA" not in resumed_provider.calls
    assert "BBB" in resumed_provider.calls
    assert aaa_path.read_bytes() == original_bytes
    final_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert final_manifest["status"] == "complete"


def test_crawler_preserves_provider_columns(tmp_path):
    universe_path = tmp_path / "universe.csv"
    write_universe(universe_path)
    manifest_path = crawl_snapshot(
        universe_path, "raw-columns", "2024-01-01", "2024-01-31",
        tmp_path / "raw", FakeProvider(), expected_size=2,
    )

    raw = pd.read_csv(manifest_path.parent / "symbols" / "AAA.csv")
    assert list(raw.columns) == ["time", "open", "high", "low", "close", "volume"]


def test_complete_snapshot_is_immutable(tmp_path):
    universe_path = tmp_path / "universe.csv"
    write_universe(universe_path)
    manifest_path = crawl_snapshot(
        universe_path, "complete", "2024-01-01", "2024-01-31",
        tmp_path / "raw", FakeProvider(), expected_size=2,
    )
    original_manifest = manifest_path.read_bytes()
    provider = FakeProvider()

    crawl_snapshot(
        universe_path, "complete", "2024-01-01", "2024-01-31",
        tmp_path / "raw", provider, expected_size=2,
    )

    assert provider.calls == []
    assert manifest_path.read_bytes() == original_manifest
