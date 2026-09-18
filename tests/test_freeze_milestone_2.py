import gzip

import pandas as pd
import pytest

from evaluation.freeze_milestone_2 import check_lockbox, collect_hashes


def _write_gz_csv(path, frame):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as handle:
        frame.to_csv(handle, index=False)


def test_collect_hashes_is_sorted_relative_and_skips_nothing(tmp_path):
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "x.md").write_text("x")
    (tmp_path / "a.md").write_text("a")

    hashes = collect_hashes(tmp_path, [tmp_path / "a.md", tmp_path / "b"])

    assert list(hashes) == ["a.md", "b/x.md"]
    assert all(len(value) == 64 for value in hashes.values())


def test_collect_hashes_rejects_a_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        collect_hashes(tmp_path, [tmp_path / "missing.md"])


def test_lockbox_passes_when_every_date_is_before_2026(tmp_path):
    registry = tmp_path / "registry.csv.gz"
    _write_gz_csv(registry, pd.DataFrame({"origin_date": ["2025-12-24"], "target_end_date": ["2025-12-31"]}))
    _write_gz_csv(tmp_path / "m2_5" / "a_per_date_metrics.csv.gz", pd.DataFrame({"origin_date": ["2025-12-24"]}))

    result = check_lockbox(registry, tmp_path, "2026-01-01")

    assert result["lockbox_opened"] is False
    assert result["latest_target_end_date"] == "2025-12-31"
    assert result["per_date_files_checked"] == 1


def test_lockbox_fails_when_a_target_reaches_2026(tmp_path):
    registry = tmp_path / "registry.csv.gz"
    _write_gz_csv(registry, pd.DataFrame({"origin_date": ["2025-12-30"], "target_end_date": ["2026-01-06"]}))

    assert check_lockbox(registry, tmp_path, "2026-01-01")["lockbox_opened"] is True


def test_lockbox_fails_when_an_output_date_reaches_2026(tmp_path):
    registry = tmp_path / "registry.csv.gz"
    _write_gz_csv(registry, pd.DataFrame({"origin_date": ["2025-12-24"], "target_end_date": ["2025-12-31"]}))
    _write_gz_csv(tmp_path / "m2_9" / "a_per_date_metrics.csv.gz", pd.DataFrame({"origin_date": ["2026-01-02"]}))

    assert check_lockbox(registry, tmp_path, "2026-01-01")["lockbox_opened"] is True
