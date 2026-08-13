# M2.1 Common-Origin Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one deterministic registry of VN150 forecast origins that is valid for both `L=63` and `L=126` at `H=5`, while keeping all 2026 observations outside model selection.

**Architecture:** Read only the frozen `vn150_strict_v2` curated symbol files and their manifest. Build the complete common population of eligible `(security_id, origin_date)` rows, store only dates and row offsets in a compressed local registry, and publish a compact manifest, summary, and report. Later smoke, screen, and confirm runs will select deterministic views from this registry instead of rebuilding or redefining the evaluation population.

**Tech Stack:** Python 3.10+, pandas, PyYAML, hashlib, pytest.

## Global Constraints

- Work directly on the current `main` worktree; do not create a branch or worktree.
- Follow `AGENTS.md`, `GEMINI.md`, and `SPEC.md`.
- Use `vn150_strict_v2`; do not rebuild or mutate M1 data.
- Use daily bars only and never cross `security_id` or `segment_id`.
- Keep `H=5`; the only lookbacks are `L={63,126}`.
- A common origin must have 126 contiguous history rows ending at the origin and five contiguous target rows after it in the same segment.
- The origin is the final observed row; targets are the next five rows.
- Evaluation folds are calendar years 2022, 2023, 2024, and 2025.
- No origin or target dated 2026 or later may enter the registry. `2026-01-01` starts the unopened lockbox.
- Keep dates with at least ten eligible symbols so every registered date can support `HitRate@Top10` later.
- Do not run Kronos, calculate model metrics, create unseen-symbol groups, or fine-tune in M2.1.
- Do not copy OHLCV values into the registry. Store row offsets and provenance only.
- The full compressed registry is a local/cache artifact. Commit only config, code, tests, compact summary, report, and manifest.
- Preserve the M1 limitations: `price_adjustment_status=unverified_provider_history` and `amount_policy=derived_ohlc4_compatibility_proxy`.

---

## Scope Decision

Three registry shapes were considered:

1. **Complete common-origin registry, then derive profiles:** one immutable population supports all later runs. This is selected because sampling policy cannot silently alter eligibility.
2. **A separate registry for each stride/profile:** smaller files, but smoke, screen, and confirm can drift onto different populations.
3. **One registry row per lookback:** straightforward for runners, but duplicates targets and makes paired `L=63` versus `L=126` validation easier to break.

M2.1 uses option 1. One row represents one common `(symbol, origin)` and contains offsets for both lookbacks.

## Execution Precondition

M1/M1.1 is verified but currently uncommitted in the shared `main` worktree.
Before Task 1, review that existing diff, rerun the M1 verification commands,
and create a separate M1 checkpoint commit. Do not combine the current M1
implementation with M2.1 code in one commit, and do not use `git add -A`.

M2.1 may be designed before that checkpoint, but its canonical manifest must
record a commit that already contains the accepted M1 data contract.

## File Map

- Create `evaluation/research/__init__.py`: expose the small public registry interface.
- Create `evaluation/research/origins.py`: config parsing, dataset fingerprinting, origin construction, validation, and deterministic writing.
- Create `evaluation/build_origin_registry.py`: CLI orchestration and compact report/manifest generation.
- Create `evaluation/configs/m2_1_origins.yaml`: frozen M2.1 data, fold, lookback, horizon, and output paths.
- Create `tests/test_origin_registry.py`: contract, temporal-boundary, determinism, and CLI artifact tests.
- Create during canonical execution `data/evaluation/m2_1/common_origins.csv.gz`: full local registry.
- Create during canonical execution `reports/milestone_2_research_eval/origin_registry/registry_summary.csv`: fold/date counts.
- Create during canonical execution `reports/milestone_2_research_eval/origin_registry/manifest.json`: provenance and hashes.
- Create during canonical execution `reports/milestone_2_research_eval/origin_registry/registry_report.md`: human-readable M2.1 decision report.
- Modify after canonical execution `.codex/skills/vn-stock-market-radar/references/project-context.md`: record M2.1 result and M2.2 handoff.
- Modify after canonical execution `.codex/skills/vn-stock-market-radar/references/milestone-map.md`: mark M2.1 complete without marking all M2 complete.

Frozen M0 files, `model/`, M1 builders, and training code are out of scope.

---

### Task 1: Lock The Registry Contract And Configuration

**Files:**
- Create: `evaluation/research/__init__.py`
- Create: `evaluation/research/origins.py`
- Create: `evaluation/configs/m2_1_origins.yaml`
- Create: `tests/test_origin_registry.py`

**Interfaces:**
- Produces: `OriginRegistryConfig`, `FoldSpec`, `load_origin_config(path)`, and `dataset_fingerprint(manifest)`.
- Consumes: M1 `dataset_manifest.json` and `data_pipeline/universe_150.csv`.

- [ ] **Step 1: Write failing config and fingerprint tests**

```python
import hashlib
import json
from pathlib import Path

import pytest

from evaluation.research.origins import dataset_fingerprint, load_origin_config


def test_m2_1_config_locks_common_origin_contract():
    config = load_origin_config(Path("evaluation/configs/m2_1_origins.yaml"))
    assert config.dataset_id == "vn150_strict_v2"
    assert config.lookbacks == (63, 126)
    assert config.horizon == 5
    assert config.minimum_cross_section == 10
    assert config.lockbox_start.isoformat() == "2026-01-01"
    assert [(f.start.isoformat(), f.end.isoformat()) for f in config.folds] == [
        ("2022-01-01", "2022-12-31"),
        ("2023-01-01", "2023-12-31"),
        ("2024-01-01", "2024-12-31"),
        ("2025-01-01", "2025-12-31"),
    ]


def test_config_rejects_a_fold_that_touches_lockbox(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
dataset_id: vn150_strict_v2
dataset_dir: data/curated/vn150_strict_v2
dataset_manifest_path: reports/milestone_1_data/vn150_strict_v2/dataset_manifest.json
universe_path: data_pipeline/universe_150.csv
registry_path: data/evaluation/m2_1/common_origins.csv.gz
report_dir: reports/milestone_2_research_eval/origin_registry
lookbacks: [63, 126]
horizon: 5
minimum_cross_section: 10
lockbox_start: 2026-01-01
folds:
  - {fold_id: eval_2025, start: 2025-01-01, end: 2026-01-02}
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="lockbox"):
        load_origin_config(path)


def test_dataset_fingerprint_ignores_generated_timestamp():
    base = {
        "dataset_id": "vn150_strict_v2",
        "policy_version": "strict_v2",
        "artifact_hashes": {"symbols/AAA.csv": "abc"},
    }
    first = dataset_fingerprint({**base, "generated_at_utc": "first"})
    second = dataset_fingerprint({**base, "generated_at_utc": "second"})
    expected = hashlib.sha256(
        json.dumps(base, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert first == second == expected
```

- [ ] **Step 2: Run tests and verify RED**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_origin_registry.py -q
```

Expected: collection fails because `evaluation.research.origins` does not exist.

- [ ] **Step 3: Add the frozen YAML configuration**

```yaml
schema_version: m2_1_origin_registry_v1
dataset_id: vn150_strict_v2
dataset_dir: data/curated/vn150_strict_v2
dataset_manifest_path: reports/milestone_1_data/vn150_strict_v2/dataset_manifest.json
universe_path: data_pipeline/universe_150.csv
registry_path: data/evaluation/m2_1/common_origins.csv.gz
report_dir: reports/milestone_2_research_eval/origin_registry
lookbacks: [63, 126]
horizon: 5
minimum_cross_section: 10
lockbox_start: 2026-01-01
folds:
  - {fold_id: eval_2022, start: 2022-01-01, end: 2022-12-31}
  - {fold_id: eval_2023, start: 2023-01-01, end: 2023-12-31}
  - {fold_id: eval_2024, start: 2024-01-01, end: 2024-12-31}
  - {fold_id: eval_2025, start: 2025-01-01, end: 2025-12-31}
```

- [ ] **Step 4: Implement minimal immutable config types and validation**

`FoldSpec` contains `fold_id: str`, `start: date`, and `end: date`.
`OriginRegistryConfig` contains the exact YAML fields above, with paths represented as `Path` and collections represented as tuples.

`load_origin_config()` must reject:

- `lookbacks != (63, 126)`;
- `horizon != 5`;
- `minimum_cross_section < 10`;
- duplicate, overlapping, or non-increasing folds;
- any fold whose end is on or after `lockbox_start`;
- a schema version other than `m2_1_origin_registry_v1`.

`dataset_fingerprint()` hashes only this canonical JSON payload:

```python
{
    "dataset_id": manifest["dataset_id"],
    "policy_version": manifest["policy_version"],
    "artifact_hashes": manifest["artifact_hashes"],
}
```

- [ ] **Step 5: Run focused tests and verify GREEN**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_origin_registry.py -q
```

- [ ] **Step 6: Commit the contract**

```powershell
git add evaluation/research evaluation/configs/m2_1_origins.yaml tests/test_origin_registry.py docs/superpowers/plans/2026-08-12-m2-1-common-origin-registry.md
git commit -m "test: lock m2 common-origin contract"
```

---

### Task 2: Build And Validate Common Origins

**Files:**
- Modify: `evaluation/research/origins.py`
- Modify: `evaluation/research/__init__.py`
- Modify: `tests/test_origin_registry.py`

**Interfaces:**
- Consumes: `OriginRegistryConfig`, strict symbol CSV files, the M1 manifest, and universe exchange metadata.
- Produces: `build_common_origins(config) -> pandas.DataFrame` and `validate_common_origins(frame, config) -> None`.

The canonical registry columns are:

```text
schema_version,dataset_fingerprint,fold_id,origin_id,security_id,symbol,exchange,
segment_id,origin_date,target_start_date,target_end_date,
row_start_l63,row_start_l126,row_origin,row_target_start,row_target_end
```

All `row_*` values are zero-based offsets into the corresponding curated symbol CSV whose hash is frozen by the dataset fingerprint.

- [ ] **Step 1: Add a synthetic strict-dataset fixture**

Create ten symbols with:

- one segment long enough for 126 history rows and five targets;
- a second short segment that must be excluded;
- an origin whose fifth target crosses the fold end;
- rows in 2026 that must remain absent;
- reversed universe and file iteration order for determinism testing.

Keep `minimum_cross_section=10` in both synthetic and canonical configs. On one
fixture date, shorten one symbol so that the remaining cross-section is nine
and the entire date must be removed.

- [ ] **Step 2: Write failing eligibility and leakage tests**

```python
def test_registry_requires_both_lookbacks_and_five_future_rows(registry_fixture):
    origins = build_common_origins(registry_fixture.config)
    assert (origins.row_origin - origins.row_start_l63 == 62).all()
    assert (origins.row_origin - origins.row_start_l126 == 125).all()
    assert (origins.row_target_start - origins.row_origin == 1).all()
    assert (origins.row_target_end - origins.row_origin == 5).all()


def test_registry_never_crosses_segment_fold_or_lockbox(registry_fixture):
    origins = build_common_origins(registry_fixture.config)
    assert origins.origin_date.max() < "2026-01-01"
    assert origins.target_end_date.max() < "2026-01-01"
    assert (origins.target_end_date <= origins.fold_id.map(registry_fixture.fold_ends)).all()
    validate_common_origins(origins, registry_fixture.config)


def test_dates_below_minimum_cross_section_are_removed(registry_fixture):
    origins = build_common_origins(registry_fixture.config)
    counts = origins.groupby(["fold_id", "origin_date"]).security_id.nunique()
    assert counts.ge(registry_fixture.config.minimum_cross_section).all()


def test_origin_ids_and_rows_are_stable_when_input_order_changes(registry_fixture):
    first = build_common_origins(registry_fixture.config)
    second = build_common_origins(registry_fixture.reordered_config)
    columns = ["origin_id", "security_id", "origin_date", "row_origin"]
    pd.testing.assert_frame_equal(first[columns], second[columns])
```

- [ ] **Step 3: Run focused tests and verify RED**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_origin_registry.py -q
```

Expected: failures because origin construction and validation are absent.

- [ ] **Step 4: Implement origin enumeration**

For every symbol file:

1. Verify its SHA256 against `dataset_manifest.json` before reading it.
2. Merge exchange from the fixed universe by `security_id`; do not crawl metadata.
3. Preserve CSV row order as the row-offset contract.
4. Group by `segment_id` and sort each segment by `session_id`.
5. For every possible origin position `p`, require `p >= 125` and `p + 5 < len(segment)`.
6. Assign a fold when `origin_date >= fold.start` and `target_end_date <= fold.end`.
7. Reject rows at or beyond `2026-01-01` before constructing IDs.
8. Emit both lookback starts in the same row.
9. Remove entire `(fold_id, origin_date)` groups with fewer than ten eligible symbols.
10. Sort by `fold_id`, `origin_date`, and `security_id`.

Construct the full SHA256 `origin_id` from:

```text
dataset_fingerprint|fold_id|security_id|origin_date|H=5
```

Do not include lookback in `origin_id`; the row is intentionally common to both lookbacks.

- [ ] **Step 5: Implement defensive registry validation**

`validate_common_origins()` must raise `ValueError` when:

- `origin_id` is duplicated;
- `(fold_id, security_id, origin_date)` is duplicated;
- a row lacks exactly 63 and 126 observations according to offsets;
- a target is not exactly five rows after the origin;
- a target leaves its fold or touches the lockbox;
- any registered date has fewer than `minimum_cross_section` distinct symbols;
- registry sorting is noncanonical.

- [ ] **Step 6: Run focused tests and verify GREEN**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_origin_registry.py -q
```

- [ ] **Step 7: Commit the builder**

```powershell
git add evaluation/research tests/test_origin_registry.py
git commit -m "feat: build deterministic common origins"
```

---

### Task 3: Materialize A Cache-Efficient Registry And Provenance Report

**Files:**
- Create: `evaluation/build_origin_registry.py`
- Modify: `evaluation/research/origins.py`
- Modify: `tests/test_origin_registry.py`

**Interfaces:**
- Consumes: `build_common_origins()` and the frozen YAML config.
- Produces: deterministic `common_origins.csv.gz`, `registry_summary.csv`, `manifest.json`, and `registry_report.md`.

- [ ] **Step 1: Write failing deterministic-artifact tests**

```python
def test_registry_writer_is_byte_reproducible(registry_fixture, tmp_path):
    frame = build_common_origins(registry_fixture.config)
    first = write_registry(frame, tmp_path / "first.csv.gz")
    second = write_registry(frame, tmp_path / "second.csv.gz")
    assert sha256_file(first) == sha256_file(second)


def test_manifest_records_provenance_and_lockbox(registry_cli_result):
    manifest = json.loads((registry_cli_result / "manifest.json").read_text())
    assert manifest["schema_version"] == "m2_1_origin_registry_v1"
    assert manifest["dataset_id"] == "vn150_strict_v2"
    assert manifest["lookbacks"] == [63, 126]
    assert manifest["horizon"] == 5
    assert manifest["lockbox_start"] == "2026-01-01"
    assert manifest["lockbox_opened"] is False
    assert len(manifest["registry_sha256"]) == 64
    assert manifest["price_adjustment_status"] == "unverified_provider_history"
    assert manifest["amount_policy"] == "derived_ohlc4_compatibility_proxy"


def test_summary_has_one_row_per_fold_and_registered_date(registry_cli_result):
    summary = pd.read_csv(registry_cli_result / "registry_summary.csv")
    assert set(summary["scope"]) == {"fold", "date"}
    assert set(summary.loc[summary.scope == "fold", "fold_id"]) == {
        "eval_2022", "eval_2023", "eval_2024", "eval_2025"
    }
```

- [ ] **Step 2: Run tests and verify RED**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_origin_registry.py -q
```

- [ ] **Step 3: Implement deterministic compressed writing**

Write dates as `YYYY-MM-DD`, use `lineterminator="\n"`, and gzip with `mtime=0`. Write to a temporary sibling path, hash the completed file, then atomically replace the target. Repeated materialization from identical M1 artifacts and config must produce the same registry SHA256.

The full registry remains under `data/evaluation/m2_1/`; it is not added to git.

- [ ] **Step 4: Implement the CLI**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation\build_origin_registry.py --config evaluation\configs\m2_1_origins.yaml
```

The CLI must:

1. load and validate config;
2. verify M1 manifest identity and every consumed symbol hash;
3. build and validate origins;
4. write the compressed registry atomically;
5. calculate date and fold summaries;
6. write the compact manifest and report;
7. print registry path, SHA256, row count, date count, symbol count, and fold counts.

The manifest records config SHA256, deterministic dataset fingerprint, registry SHA256, registry row/date/symbol counts, fold boundaries, source paths, command, git commit, dirty-worktree boolean, and all M1 data-policy limitations. `generated_at_utc` is allowed in the manifest but is not part of the deterministic registry hash.

- [ ] **Step 5: Keep the report decision-focused**

`registry_report.md` must state:

- M2.1 created metadata only; no model was evaluated;
- counts by fold and eligible date;
- all rows are common to both lookbacks;
- the 2026 lockbox exists in source data but was excluded completely;
- dates below ten eligible symbols were excluded;
- the fixed current VN150 population remains survivorship-biased;
- price adjustment and amount limitations remain unresolved;
- the only next step is M2.2 profile selection and naive forecast artifacts.

- [ ] **Step 6: Run artifact tests and verify GREEN**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_origin_registry.py -q
```

- [ ] **Step 7: Commit CLI and artifact contract**

```powershell
git add evaluation/build_origin_registry.py evaluation/research tests/test_origin_registry.py
git commit -m "feat: materialize common-origin registry"
```

---

### Task 4: Execute M2.1 On VN150 And Close Only This Subphase

**Files:**
- Create: `data/evaluation/m2_1/common_origins.csv.gz` (local/cache only)
- Create: `reports/milestone_2_research_eval/origin_registry/registry_summary.csv`
- Create: `reports/milestone_2_research_eval/origin_registry/manifest.json`
- Create: `reports/milestone_2_research_eval/origin_registry/registry_report.md`
- Modify: `.codex/skills/vn-stock-market-radar/references/project-context.md`
- Modify: `.codex/skills/vn-stock-market-radar/references/milestone-map.md`

**Interfaces:**
- Produces: the only origin population M2.2 and later M2 runners may consume.
- Does not produce: forecasts, metrics, model decisions, or training approval.

- [ ] **Step 1: Run the canonical registry build**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation\build_origin_registry.py --config evaluation\configs\m2_1_origins.yaml
```

Expected: four folds are present; all registry origins and targets end before `2026-01-01`.

- [ ] **Step 2: Rebuild to a temporary path and compare hashes**

Use the same config values with only `registry_path` and `report_dir` redirected to a temporary directory. The resulting registry SHA256 must exactly match the canonical hash. Remove only the temporary M2.1 output after comparison.

- [ ] **Step 3: Run structural acceptance checks**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_origin_registry.py tests\test_data_readiness.py tests\test_dataset_builder.py -q
```

Acceptance checks:

- four fold IDs are present;
- every date has at least ten distinct symbols;
- no duplicate origin ID or symbol-origin key exists;
- every row supports exactly 63 and 126 history observations plus five targets;
- every row remains inside one security and segment;
- no origin or target reaches 2026;
- repeated builds have identical registry SHA256;
- no M1 artifact hash changed.

- [ ] **Step 4: Run full project verification**

```powershell
$env:PYTHONPATH='finetune_csv'
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests -q
C:\Users\USER\anaconda3\python.exe C:\Users\USER\.codex\skills\.system\skill-creator\scripts\quick_validate.py .codex\skills\vn-stock-market-radar
git diff --check
```

- [ ] **Step 5: Update context without overstating completion**

Record M2.1 as complete with registry path, hash, folds, date count, origin count, symbol count, and lockbox exclusion. Keep M2 itself `in progress`. Set M2.2 as:

```text
Derive deterministic smoke/screen views from the frozen registry and implement
two causal naive forecast references. Do not run Kronos yet.
```

- [ ] **Step 6: Review the diff and commit M2.1**

```powershell
git status --short
git diff --stat
git add evaluation/research evaluation/build_origin_registry.py evaluation/configs/m2_1_origins.yaml tests/test_origin_registry.py reports/milestone_2_research_eval/origin_registry .codex/skills/vn-stock-market-radar/references
git commit -m "feat: freeze m2 common-origin registry"
```

Do not add `data/evaluation/m2_1/common_origins.csv.gz`; its hash and regeneration command are the committed contract.

---

## Acceptance Gate

M2.1 is complete only when all conditions below hold:

1. The M1 dataset fingerprint is derived from and agrees with the frozen artifact hashes.
2. A single registry row supports both `L=63` and `L=126`; no per-lookback population exists.
3. The target is exactly the next five contiguous rows in the same segment.
4. The registry has folds `eval_2022` through `eval_2025` and nothing from 2026.
5. Every registered date has at least ten eligible symbols.
6. Registry ordering, IDs, compressed bytes, and SHA256 are reproducible.
7. Compact artifacts record counts, hashes, config, code provenance, command, and M1 limitations.
8. The full test suite passes and M1 artifact hashes remain unchanged.
9. No model inference or metric calculation has occurred.
10. M2 remains open; only M2.1 is marked complete.

## Explicitly Deferred To M2.2 And Later

- Smoke/screen/confirm stride selection.
- Seen/unseen-symbol grouping and stratification.
- Persistence and recent-return bootstrap forecasts.
- Kronos-small or Kronos-base inference.
- Sample-path cache and resume behavior.
- DA, MW-DA, RankIC, HitRate@Top10, CRPS, or interval metrics.
- Paired date-block bootstrap and model promotion rules.
- Any fine-tuning, LoRA, tokenizer work, frontend, or deployment.

## Stop Condition

After the canonical registry, report, manifest, verification, and context update exist, stop. Do not begin M2.2 in the same implementation pass.
