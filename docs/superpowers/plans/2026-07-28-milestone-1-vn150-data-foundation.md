# Milestone 1 VN150 Data Foundation Plan

> Date: 2026-07-28
>
> Status: Implemented and verified on 2026-08-09

## Goal

Build the smallest reproducible daily-data foundation needed to compare Kronos
on a fixed 150-symbol Vietnam-stock benchmark.

The milestone ends with an immutable raw snapshot, a strict curated dataset,
exchange-session calendars, a data-quality report, and a manifest. It does not
run model training.

## Locked Scope

- Universe size is exactly 150 symbols.
- The benchmark is conditional on a fixed universe selected as of 2026-08-09.
- Data frequency is daily.
- Data source is `vnstock`.
- The validated community API exposes at most eight years of daily index
  calendar data; actual coverage must be reported and older unverified bars are
  excluded as `outside_calendar_coverage`.
- Exchange calendars are derived from VNINDEX, HNXINDEX, and UPCOMINDEX data.
- Missing or invalid observations split a sequence; no imputation is allowed.
- Row states are reduced to `valid`, `unavailable`, and implicit `pre_history`.
- Model research initially compares `L=63` and `L=126` with `H=5`.
- CSV is used for raw and curated artifacts to avoid a new storage dependency.
- Existing M0 artifacts and baseline behavior remain unchanged.

The fixed current universe is reproducible but has survivorship bias. It may be
used for matched model comparisons and the current-universe app, but not for
claims about unbiased historical whole-market performance.

## Out Of Scope

- Dynamic point-in-time universe reconstruction.
- Historical ticker and exchange-transfer graph.
- Delisted-security recovery.
- Detailed suspension/provider-missing classification.
- Multi-provider reconciliation.
- Missing-value imputation.
- Streaming ingestion, scheduling, database storage, and model training.

## Target Layout

```text
data_pipeline/
  __init__.py
  universe_150.csv
  crawl.py
  build_dataset.py
  audit.py

data/
  raw/<snapshot_id>/
    symbols/*.csv
    calendars/*.csv
    crawl_manifest.json
  curated/<dataset_id>/
    symbols/*.csv
    calendars/*.csv
    exclusions.csv
    manifest.json

reports/milestone_1_data/
  <dataset_id>/
    data_quality.csv
    data_quality_report.md

tests/
  test_universe_contract.py
  test_data_crawl.py
  test_dataset_builder.py
  test_strict_dataset.py
```

`data/` remains git-ignored. The universe definition, code, tests, configs, and
small report/manifest artifacts are committed. Large symbol files remain local
or are moved explicitly between environments.

## Task 1: Revise The Project Contract

**Files**

- Modify: `SPEC.md`
- Modify: `GEMINI.md`
- Modify: `.codex/skills/vn-stock-market-radar/references/project-context.md`
- Modify: `.codex/skills/vn-stock-market-radar/references/milestone-map.md`

**Changes**

1. Increment the SPEC version.
2. Record the fixed VN150 benchmark as the approved M1 scope.
3. State explicitly that it is conditional on current membership and cannot
   support survivorship-free whole-market claims.
4. Defer dynamic point-in-time reconstruction rather than silently deleting it.
5. Replace the broad M1 exit gate with the raw snapshot, strict curated data,
   calendar, quality report, and manifest.
6. Record `L={63,126}` and `H=5` as the next comparison protocol, not a selected
   winner.

**Verify**

```powershell
rg -n "fixed|VN150|survivorship|63|126|H=5" SPEC.md GEMINI.md .codex/skills/vn-stock-market-radar/references
```

## Task 2: Freeze And Validate The Universe

**Files**

- Create: `data_pipeline/__init__.py`
- Create: `data_pipeline/universe_150.csv`
- Create: `tests/test_universe_contract.py`

**Universe schema**

```csv
security_id,symbol,exchange,included_as_of
HOSE_FPT,FPT,HOSE,2026-08-09
```

**Tests first**

1. The file contains exactly 150 rows.
2. `security_id` and `(symbol, exchange)` are unique.
3. Exchange belongs to `HOSE`, `HNX`, or `UPCOM`.
4. Symbols are uppercase and non-empty.
5. `included_as_of` is identical and parseable.
6. The existing 50 baseline symbols are either present or explicitly documented
   as excluded before the universe is accepted.

The crawler must refuse to run when this contract fails. The exact constituent
list must be reviewed before the first network crawl.

**Verify**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_universe_contract.py -q
```

## Task 3: Implement Immutable Raw Crawling

**Files**

- Create: `data_pipeline/crawl.py`
- Create: `tests/test_data_crawl.py`
- Modify: `requirements.txt`

**CLI**

```powershell
python -m data_pipeline.crawl `
  --universe data_pipeline/universe_150.csv `
  --snapshot-id 2026-08-09 `
  --start 2010-01-01 `
  --end 2026-08-09 `
  --request-delay 3.2 `
  --out-dir data/raw
```

**Behavior**

1. Validate the universe before making network calls.
2. Fetch the provider's daily OHLCV payload for every symbol without inventing
   a raw `amount` field when the provider omits it.
3. Fetch VNINDEX, HNXINDEX, and UPCOMINDEX for calendar dates.
4. Save one provider response per symbol without cleaning, filling, or
   reindexing it.
5. Record request parameters, provider/library version, command, timestamps,
   row counts, failures, and SHA256 hashes in `crawl_manifest.json`.
6. Refuse to overwrite an existing snapshot. A retry fills only missing files
   and updates the manifest deterministically.
7. Pin the exact validated `vnstock` version in `requirements.txt`.
8. Throttle guest API requests and persist an incomplete progress manifest after
   each attempted artifact so a provider termination can resume safely.

**Tests first, with a fake provider**

- Successful symbol and calendar writes.
- Partial failure is reported and produces a non-complete manifest.
- Existing files are not overwritten.
- A resumed crawl requests only missing artifacts.
- Hashes match saved bytes.
- No preprocessing occurs in the crawler.

**Verify**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_data_crawl.py -q
```

Run a three-symbol smoke crawl before the full network job. The full crawl is
not accepted while any of the 150 symbols or three calendars are missing.

## Task 4: Build The Strict Curated Dataset

**Files**

- Create: `data_pipeline/build_dataset.py`
- Create: `tests/test_dataset_builder.py`

**CLI**

```powershell
python -m data_pipeline.build_dataset `
  --raw-dir data/raw/2026-08-09 `
  --universe data_pipeline/universe_150.csv `
  --dataset-id vn150_strict_v1 `
  --out-dir data/curated
```

**Valid-row contract**

```text
timestamp is an exchange session
OHLC are finite and positive
high >= max(open, close, low)
low <= min(open, close, high)
volume > 0
provider amount > 0 when present
timestamp is unique for the security
```

**Behavior**

1. Parse and sort daily timestamps.
2. Remove byte-for-byte or value-identical duplicate bars deterministically.
3. Quarantine conflicting duplicates instead of choosing one silently.
4. Map each bar to the matching exchange calendar and integer `session_id`.
5. Mark all invalid, zero-trade, missing-session, and conflicting observations
   as `unavailable`.
6. Increment `segment_id` after every unavailable exchange session.
7. Write only valid bars to each curated symbol CSV, retaining `security_id`,
   `session_id`, and `segment_id`.
8. Never synthesize pre-history rows and never use `ffill`, `bfill`, or zero
   fill.
9. When raw `amount` is absent, derive `volume * OHLC4` in the curated layer and
   record `amount_source=derived_ohlc4` on every affected row.
10. Write every excluded observation and reason to `exclusions.csv`.
11. Generate a deterministic manifest with input/output hashes, policy version,
    universe hash, calendar hashes, row counts, segment counts, command, and code
    revision.

**Tests first**

- Weekend and market holiday do not split a segment.
- A missing official exchange session splits a segment.
- NaN, invalid OHLC, zero volume, and zero amount split a segment.
- No rows are created before the first observation.
- Identical duplicates collapse to one row.
- Conflicting duplicates are excluded and reported.
- Output is byte-identical across repeated builds from identical inputs.

**Verify**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_dataset_builder.py -q
```

## Task 5: Produce The Data Audit

**Files**

- Create: `data_pipeline/audit.py`
- Extend: `tests/test_dataset_builder.py`

**CLI**

```powershell
python -m data_pipeline.audit `
  --dataset-dir data/curated/vn150_strict_v1 `
  --out-dir reports/milestone_1_data/vn150_strict_v1
```

**Outputs**

- `data_quality.csv`: one row per symbol.
- `data_quality_report.md`: aggregate research report.

**Required statistics**

- Raw, valid, and excluded row counts.
- First and last valid session.
- Number and distribution of contiguous segments.
- Duplicate, invalid-OHLC, zero-trade, and missing-session counts.
- Available windows for `L={63,126}`, `H=5`.
- Symbols failing minimum history of 252 valid sessions.
- Counts by exchange and calendar coverage.

Raw sliding-window counts must be labeled as dependent observations, not
effective sample size.

**Acceptance**

- Exactly 150 symbols are reported.
- Every raw row is accounted for as valid, duplicate, or excluded.
- No curated window can cross a `segment_id`.
- Report and manifest identify the same dataset and universe hashes.

## Task 6: Add A Strict Model Dataset Without Changing M0

**Files**

- Create: `finetune_csv/strict_dataset.py`
- Create: `tests/test_strict_dataset.py`
- Modify later, only after tests: new M2/M3 configs and entry points

Do not alter `CustomKlineDataset` during M1. M0 uses the legacy data contract,
and its frozen artifact must remain reproducible.

**Strict dataset behavior**

1. Read curated symbol CSVs.
2. Build windows only within one `(security_id, segment_id)`.
3. Require the full `L + H + 1` training sequence.
4. Apply temporal partitions before indexing windows.
5. Use an `H`-session purge instead of the legacy fixed five-row buffer.
6. Normalize all features from lookback statistics only.
7. Reject non-finite input; never repair it in `__getitem__`.

**Tests first**

- No symbol or segment crossing.
- No missing-value repair.
- Lookback-only normalization.
- `L=63` and `L=126` produce expected counts from the same curated fixture.
- Purge length follows `H`.

**Verify**

```powershell
$env:PYTHONPATH='finetune_csv'
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests\test_strict_dataset.py -q
```

## Task 7: End-To-End Dry Run And Freeze M1

Run, in order:

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests -q

C:\Users\USER\anaconda3\envs\stock\python.exe -m data_pipeline.crawl `
  --universe data_pipeline/universe_150.csv `
  --snapshot-id 2026-08-09 `
  --start 2010-01-01 `
  --end 2026-08-09 `
  --request-delay 3.2 `
  --out-dir data/raw

C:\Users\USER\anaconda3\envs\stock\python.exe -m data_pipeline.build_dataset `
  --raw-dir data/raw/2026-08-09 `
  --universe data_pipeline/universe_150.csv `
  --dataset-id vn150_strict_v1 `
  --out-dir data/curated

C:\Users\USER\anaconda3\envs\stock\python.exe -m data_pipeline.audit `
  --dataset-dir data/curated/vn150_strict_v1 `
  --out-dir reports/milestone_1_data/vn150_strict_v1
```

M1 is complete only when:

- the raw manifest is complete for 150 symbols and three calendars;
- strict curated files contain no invalid values or synthetic rows;
- all gaps are represented by segment boundaries;
- hashes reproduce on a second build;
- the audit reports both `63/5` and `126/5` availability;
- all tests pass;
- no model training has started.

## Commit Sequence

1. `docs: lock simplified VN150 data scope`
2. `feat: add immutable VN150 raw crawler`
3. `feat: build strict segmented stock dataset`
4. `feat: add VN150 data audit and strict dataset`
5. `chore: freeze milestone 1 data manifest`

Each commit must contain its corresponding passing tests. Raw and curated stock
files remain outside git; manifests and reports are committed.

## Implementation Outcome

- Raw snapshot: `data/raw/2026-08-09` (local, ignored), 153 hashed artifacts.
- Curated dataset: `data/curated/vn150_strict_v1` (local, ignored), 154 hashed artifacts.
- Committed report surface: `reports/milestone_1_data/vn150_strict_v1`.
- A second full build matched all 154 curated artifact hashes.
- No model training was run.
