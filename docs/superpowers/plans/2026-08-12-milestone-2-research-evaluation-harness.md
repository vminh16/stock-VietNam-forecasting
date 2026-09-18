# Milestone 2 Research Evaluation Harness Implementation Plan

> **Status:** Superseded as a single execution package. Keep this document as a
> roadmap only. Execute M2 through separate plans beginning with M2.1 temporal
> common-origin registry after M1.1 data readiness closure.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, cache-first evaluation harness that compares naive forecasts, Kronos-small, and Kronos-base on identical VN150 forecast origins, selects `L in {63, 126}` at `H=5`, and reports paired date-block uncertainty without training or opening a contaminated historical lockbox.

**Architecture:** Keep the frozen M0 pipeline untouched and add a separate M2 research package. A deterministic fold/origin registry becomes the join key for every candidate; runners emit one canonical forecast table, metrics aggregate by forecast date, and a stationary block bootstrap compares paired date series. Expensive model outputs are resumable local cache artifacts, while compact manifests, decision reports, and hashes are committed.

**Tech Stack:** Python 3.10+, pandas, NumPy, SciPy, PyTorch, PyYAML, Kronos, pytest, CSV/JSON artifacts.

## Global Constraints

- Read `AGENTS.md`, `GEMINI.md`, `SPEC.md`, and the `vn-stock-market-radar` skill before each execution session.
- Preserve daily bars, fixed VN150 universe `2026-08-09`, strict segmented dataset `vn150_strict_v1`, and no-imputation policy.
- Never allow a lookback or target to cross `security_id` or `segment_id`.
- Keep `H=5`; compare only `L={63,126}` in M2.
- Keep Kronos-base as frozen zero-shot reference and Kronos-small as the development candidate.
- Do not modify `model/kronos.py`, `model/module.py`, tokenizer weights, architecture, heads, or losses.
- Do not train or adapt a model in M2.
- Use identical symbols, origins, seeds, sample counts, and target rows for every paired comparison.
- Treat `RankIC` as primary; report `HitRate@Top10`, `MW-DA`, `DA`, CRPS, and 80% interval coverage/width only.
- Preserve `direction(x)=+1` for `x>0`, otherwise `-1`.
- Treat all M1 `amount` values as `derived_ohlc4`, never provider-reported turnover.
- Treat the fixed VN150 result as conditional and survivorship-biased.
- The old paired t-test is diagnostic only; canonical inference uses paired date-block bootstrap.
- `2026 H1` is already observed by M0 and is not a valid untouched lockbox. Register a prospective closed lockbox beginning `2026-08-10`; M2 must not evaluate it.
- Full sampled paths and per-origin cache files remain local/ignored. Commit only compact reports, manifests, configs, and aggregate CSVs.

---

## File Map

**Create**

- `evaluation/research/__init__.py`: public M2 interfaces.
- `evaluation/research/config.py`: validated YAML configuration dataclasses.
- `evaluation/research/folds.py`: fold parsing, prospective lockbox guard, and symbol holdout construction.
- `evaluation/research/origins.py`: deterministic common-origin registry over strict segments.
- `evaluation/research/baselines.py`: persistence and recent-return bootstrap forecasts.
- `evaluation/research/kronos_runner.py`: zero-shot path sampling adapter around existing Kronos code.
- `evaluation/research/artifacts.py`: canonical forecast schema, cache key, atomic write, and manifest hashing.
- `evaluation/research/metrics.py`: locked point and probabilistic metrics with date aggregation.
- `evaluation/research/bootstrap.py`: paired stationary date-block bootstrap and decision gates.
- `evaluation/run_research_eval.py`: CLI orchestration for registry, screen, confirm, and report stages.
- `evaluation/configs/milestone2_research.yaml`: pre-registered folds, candidates, seeds, compute profiles, and thresholds.
- `tests/test_research_config.py`
- `tests/test_origin_registry.py`
- `tests/test_research_baselines.py`
- `tests/test_research_artifacts.py`
- `tests/test_research_metrics.py`
- `tests/test_block_bootstrap.py`
- `tests/test_research_runner.py`
- `reports/milestone_2_research_eval/README.md`: commands and Colab handoff.

**Modify**

- `.gitignore`: ignore only `reports/milestone_2_research_eval/cache/`.
- `SPEC.md`: update M2 status only after the exit gate passes.
- `GEMINI.md`: point current sequence to M3 only after M2 closes.
- `.codex/skills/vn-stock-market-radar/references/project-context.md`: record M2 evidence and decision.
- `.codex/skills/vn-stock-market-radar/references/milestone-map.md`: mark M2 complete only after canonical report exists.

**Do Not Modify**

- `evaluation/inference_pipeline.py`: frozen M0 historical implementation.
- `evaluation/freeze_baseline.py`: frozen M0 report builder.
- `model/kronos.py`
- `model/module.py`
- `finetune_csv/legacy_dataset.py`
- M0 and M1 report artifacts.

---

### Task 0: Verify And Freeze Milestone 1

**Files:**
- Verify: `reports/milestone_1_data/vn150_strict_v1/dataset_manifest.json`
- Verify: `reports/milestone_1_data/vn150_strict_v1/data_quality_report.md`
- Commit: existing M1 source, tests, docs, and reports

**Interfaces:**
- Consumes: current dirty M1 working tree and local `data/curated/vn150_strict_v1`.
- Produces: one clean M1 commit on `main`; M2 work begins from a named revision.

- [ ] **Step 1: Confirm branch and inspect scope**

```powershell
git branch --show-current
git status --short
git diff --stat
```

Expected: branch is `main`; changes correspond to M1 data foundation and its documentation.

- [ ] **Step 2: Run the complete M1 test suite**

```powershell
$env:PYTHONPATH='finetune_csv'; C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests -q
```

Expected: all tests pass; the known dependency deprecation warnings may remain.

- [ ] **Step 3: Re-run deterministic M1 audit**

```powershell
$verify = Join-Path $env:TEMP ("m1-audit-" + [guid]::NewGuid())
C:\Users\USER\anaconda3\envs\stock\python.exe -m data_pipeline.audit --dataset-dir data/curated/vn150_strict_v1 --out-dir $verify
@("data_quality.csv", "data_quality_report.md", "dataset_manifest.json") | ForEach-Object {
    $expected = (Get-FileHash (Join-Path "reports/milestone_1_data/vn150_strict_v1" $_) -Algorithm SHA256).Hash
    $actual = (Get-FileHash (Join-Path $verify $_) -Algorithm SHA256).Hash
    if ($expected -ne $actual) { throw "M1 audit mismatch: $_" }
}
```

Expected: the three independently regenerated audit artifacts match the published M1 artifacts byte-for-byte. Curated artifact hash reproducibility remains covered by `test_repeated_builds_produce_identical_curated_hashes`.

- [ ] **Step 4: Commit M1 without M2 implementation files**

```powershell
git add AGENTS.md GEMINI.md SPEC.md requirements.txt finetune_csv data_pipeline tests .codex/skills/vn-stock-market-radar reports/milestone_1_data docs/superpowers/plans/2026-07-28-milestone-1-vn150-data-foundation.md
git commit -m "feat: freeze VN150 strict data foundation"
```

Expected: commit succeeds on `main`; local ignored raw and curated datasets are not staged.

- [ ] **Step 5: Record the M1 commit before starting M2**

```powershell
git rev-parse HEAD
git status --short
```

Expected: a concrete M1 revision is available for the M2 manifest; only this M2 plan may remain untracked.

---

### Task 1: Pre-Register M2 Folds, Profiles, And Decision Rules

**Files:**
- Create: `evaluation/research/__init__.py`
- Create: `evaluation/research/config.py`
- Create: `evaluation/research/folds.py`
- Create: `evaluation/configs/milestone2_research.yaml`
- Test: `tests/test_research_config.py`

**Interfaces:**
- Consumes: `load_research_config(path: Path) -> ResearchConfig`.
- Produces: immutable fold/profile/candidate definitions and `assert_outside_lockbox(origins, config) -> None`.

- [ ] **Step 1: Write failing config and lockbox tests**

```python
def test_m2_config_has_four_outer_folds_and_prospective_lockbox():
    config = load_research_config(Path("evaluation/configs/milestone2_research.yaml"))
    assert [fold.fold_id for fold in config.folds] == [
        "outer_2022", "outer_2023", "outer_2024", "outer_2025"
    ]
    assert config.horizon == 5
    assert config.lookbacks == (63, 126)
    assert config.lockbox.start == pd.Timestamp("2026-08-10")
    assert config.lockbox.status == "prospective_closed"


def test_lockbox_guard_rejects_future_origin():
    config = make_config(lockbox_start="2026-08-10")
    with pytest.raises(ValueError, match="closed lockbox"):
        assert_outside_lockbox(
            pd.Series(pd.to_datetime(["2026-08-10"])), config
        )
```

- [ ] **Step 2: Run tests and confirm they fail**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_config.py -q
```

Expected: FAIL because the research config package does not exist.

- [ ] **Step 3: Add the explicit configuration contract**

Use these outer folds:

```yaml
folds:
  - fold_id: outer_2022
    inner_train_end: 2020-12-31
    inner_validation_start: 2021-01-01
    inner_validation_end: 2021-12-31
    outer_train_end: 2021-12-31
    evaluation_start: 2022-01-01
    evaluation_end: 2022-12-31
  - fold_id: outer_2023
    inner_train_end: 2021-12-31
    inner_validation_start: 2022-01-01
    inner_validation_end: 2022-12-31
    outer_train_end: 2022-12-31
    evaluation_start: 2023-01-01
    evaluation_end: 2023-12-31
  - fold_id: outer_2024
    inner_train_end: 2022-12-31
    inner_validation_start: 2023-01-01
    inner_validation_end: 2023-12-31
    outer_train_end: 2023-12-31
    evaluation_start: 2024-01-01
    evaluation_end: 2024-12-31
  - fold_id: outer_2025
    inner_train_end: 2023-12-31
    inner_validation_start: 2024-01-01
    inner_validation_end: 2024-12-31
    outer_train_end: 2024-12-31
    evaluation_start: 2025-01-01
    evaluation_end: 2025-12-31
lockbox:
  start: 2026-08-10
  status: prospective_closed
```

Pre-register these profiles and thresholds:

```yaml
research:
  dataset_id: vn150_strict_v1
  dataset_dir: data/curated/vn150_strict_v1
  dataset_manifest: reports/milestone_1_data/vn150_strict_v1/dataset_manifest.json
  universe_path: data_pipeline/universe_150.csv
  horizon: 5
  lookbacks: [63, 126]
  sampling_seed: 20260812
  interval_quantiles: [0.10, 0.90]
profiles:
  smoke:
    origin_stride: 63
    sample_count: 2
    max_dates_per_fold: 2
  screen:
    origin_stride: 20
    sample_count: 5
    max_dates_per_fold: -1
  confirm:
    origin_stride: 5
    sample_count: 20
    max_dates_per_fold: -1
bootstrap:
  method: stationary
  replicates: 5000
  mean_block_dates: 10
  confidence: 0.95
decision:
  rankic_noninferiority: 0.01
  mwda_noninferiority_pp: 1.0
  max_crps_ratio: 1.05
  max_coverage_error_increase: 0.05
  minimum_cost_reduction: 0.25
  da_utility_floor_percent: 52.0
```

Model revisions and paths must be explicit, not inferred from a mutable cache. Use local `pretrained/Kronos-base`; pin Kronos-small to the official revision already used by `tests/test_kronos_regression.py` (`901c26c1332695a2a8f243eb2f37243a37bea320`) and tokenizer revision `0e0117387f39004a9016484a186a908917e22426`.

- [ ] **Step 4: Implement strict config validation**

Reject configurations when folds overlap, dates are not increasing, `H != 5`, lookbacks differ from `{63,126}`, lockbox is not after every evaluation period, quantiles are not `(0.10,0.90)`, or candidates omit the two naive references and both Kronos backbones.

- [ ] **Step 5: Run tests**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_config.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the pre-registration**

```powershell
git add evaluation/research evaluation/configs/milestone2_research.yaml tests/test_research_config.py docs/superpowers/plans/2026-08-12-milestone-2-research-evaluation-harness.md
git commit -m "test: preregister milestone 2 evaluation"
```

---

### Task 2: Build Stable Symbol Groups And Common Origins

**Files:**
- Modify: `evaluation/research/folds.py`
- Create: `evaluation/research/origins.py`
- Test: `tests/test_origin_registry.py`

**Interfaces:**
- Consumes: strict symbol CSVs, `ResearchConfig`, and universe CSV.
- Produces: `build_symbol_groups(...) -> DataFrame` and `build_common_origins(...) -> DataFrame`.

Canonical origin columns:

```text
fold_id,origin_id,security_id,symbol,exchange,segment_id,origin_session_id,
origin_date,target_end_date,evaluation_start,evaluation_end,start_l63,start_l126,target_start,target_end,
symbol_group,listing_age_tier,liquidity_tier,market_regime
```

- [ ] **Step 1: Write failing segmentation, pairing, and purge tests**

```python
def test_common_origins_are_valid_for_both_lookbacks():
    origins = build_common_origins(fixture_dataset, fixture_config, profile="confirm")
    assert (origins["target_start"] - origins["start_l126"] == 126).all()
    assert (origins["target_end"] - origins["target_start"] == 4).all()
    assert origins.groupby("origin_id")["symbol"].nunique().eq(1).all()


def test_origin_never_crosses_segment_or_fold_boundary():
    origins = build_common_origins(gapped_dataset, fixture_config, profile="confirm")
    assert "gap_origin" not in set(origins["origin_id"])
    assert (origins["target_end_date"] <= origins["evaluation_end"]).all()


def test_symbol_file_order_does_not_change_registry(fixture_dataset, fixture_config):
    forward = build_common_origins(
        fixture_dataset, fixture_config, profile="confirm", symbols=["AAA", "BBB"]
    )
    reverse = build_common_origins(
        fixture_dataset, fixture_config, profile="confirm", symbols=["BBB", "AAA"]
    )
    pd.testing.assert_frame_equal(forward, reverse)
```

- [ ] **Step 2: Run tests and confirm failure**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_origin_registry.py -q
```

Expected: FAIL because origin construction is absent.

- [ ] **Step 3: Implement deterministic symbol groups**

Create a stable 120/30 `development`/`unseen_holdout` split using SHA256 ordering within exchange, listing-cohort, and static-liquidity strata. Allocate exactly 30 holdout slots with proportional largest-remainder quotas, then take the lowest SHA256 values inside each stratum. Listing cohort comes from the symbol's immutable `first_valid` date. Static liquidity uses median `close * volume` through `2021-12-31`; symbols not yet listed form an explicit `not_listed_by_cutoff` stratum. This keeps the holdout stable and avoids using 2022-2025 targets.

For report slices, recompute liquidity tiers at each origin from the trailing 63 observed sessions. Define market regime as `up` when the equal-weight trailing-20-session return of eligible development symbols is positive and `down` otherwise. Both features use origin-time history only. Do not use derived `amount` as provider turnover.

Sector stratification is not implemented in M2 because M1 has no frozen, point-in-time sector master. Record `sector_status="unavailable_in_m1"` in the manifest rather than crawling mutable metadata during evaluation. This is an explicit scoped deviation from the ideal SPEC stratification, not a hidden substitution.

- [ ] **Step 4: Implement common-origin construction**

For each fold:

1. Enumerate sorted exchange-session origins in the evaluation interval.
2. Select dates deterministically by `origin_stride`, anchored at the first eligible session.
3. For each symbol, require 126 contiguous history rows ending at the origin and five contiguous target rows after it in the same segment.
4. Emit both `start_l63` and `start_l126` for the exact same `(symbol, origin_date)`.
5. Exclude an origin when its target end leaves the fold or reaches the closed lockbox.
6. Hash `dataset_id|fold_id|security_id|origin_date|H` into `origin_id`.

Do not reuse `StrictKlineDataset.window=L+H+1` for inference origins. M2 needs exactly `L` observed rows plus `H` future target rows; the extra next-token row belongs to training semantics.

- [ ] **Step 5: Run origin tests**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_origin_registry.py -q
```

Expected: PASS.

- [ ] **Step 6: Materialize and inspect the screen registry**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation/run_research_eval.py registry --config evaluation/configs/milestone2_research.yaml --profile screen
```

Expected: `reports/milestone_2_research_eval/registry/screen_origins.csv` and manifest are written; all rows are valid for both lookbacks, and no date is in 2026.

- [ ] **Step 7: Commit**

```powershell
git add evaluation/research/folds.py evaluation/research/origins.py tests/test_origin_registry.py reports/milestone_2_research_eval/registry
git commit -m "feat: add paired VN150 origin registry"
```

---

### Task 3: Define Canonical Forecast Artifacts And Resumable Cache

**Files:**
- Create: `evaluation/research/artifacts.py`
- Modify: `.gitignore`
- Test: `tests/test_research_artifacts.py`

**Interfaces:**
- Produces: `ForecastBatch`, `cache_key(...) -> str`, `write_forecasts_atomic(...)`, `read_forecasts(...)`, and `hash_artifacts(...)`.

Canonical long-form forecast rows:

```text
run_id,candidate_id,fold_id,origin_id,symbol,origin_date,horizon_step,
sample_id,predicted_close_return,actual_close_return,sampling_seed
```

- [ ] **Step 1: Write failing schema and cache-key tests**

```python
def test_cache_key_changes_with_scientific_inputs():
    base = cache_key(model_hash="a", data_hash="b", origin_hash="c", seed=7,
                     lookback=63, horizon=5, sample_count=20)
    changed = cache_key(model_hash="a", data_hash="b", origin_hash="c", seed=8,
                        lookback=63, horizon=5, sample_count=20)
    assert base != changed


def test_atomic_round_trip_preserves_forecast_schema(tmp_path):
    path = tmp_path / "forecast.csv.gz"
    write_forecasts_atomic(path, forecast_fixture())
    assert read_forecasts(path).equals(forecast_fixture())
```

- [ ] **Step 2: Run tests and confirm failure**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_artifacts.py -q
```

- [ ] **Step 3: Implement immutable cache identity**

The cache key must hash model artifact/revision, tokenizer revision, dataset manifest hash, universe hash, origin-registry hash, candidate, `L`, `H`, sampling parameters, shard size, and seed. Sort origins by `fold_id,origin_date,security_id`, use fixed shard boundaries, and seed each shard from `SHA256(global_seed|fold_id|shard_id)`. The same shard seed is used across paired model candidates, and resume cannot alter shard membership.

Write to `*.tmp`, flush, then atomically rename. Reject an existing artifact whose embedded cache key differs; never overwrite it under the same name.

- [ ] **Step 4: Bound committed storage**

Add exactly this ignore rule:

```gitignore
reports/milestone_2_research_eval/cache/
```

The report keeps aggregate metrics and hashes. Full sample paths stay in the ignored cache and can be copied to Colab storage independently.

- [ ] **Step 5: Run tests**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_artifacts.py -q
```

Expected: PASS, including interrupted-write cleanup.

- [ ] **Step 6: Commit**

```powershell
git add .gitignore evaluation/research/artifacts.py tests/test_research_artifacts.py
git commit -m "feat: add versioned forecast cache contract"
```

---

### Task 4: Add Naive Probabilistic References

**Files:**
- Create: `evaluation/research/baselines.py`
- Test: `tests/test_research_baselines.py`

**Interfaces:**
- Consumes: one origin's observed close series, five realized future closes, sample count, and origin seed.
- Produces: `(S, H)` arrays of cumulative close returns for `persistence` and `recent_return_bootstrap`.

- [ ] **Step 1: Write failing causal and reproducibility tests**

```python
def test_persistence_is_zero_return_for_every_path():
    paths = persistence_paths(history_close, horizon=5, sample_count=20)
    np.testing.assert_array_equal(paths, np.zeros((20, 5)))


def test_recent_bootstrap_uses_history_only_and_is_reproducible():
    first = recent_return_bootstrap_paths(history_close, 5, 20, seed=17)
    second = recent_return_bootstrap_paths(history_close, 5, 20, seed=17)
    np.testing.assert_array_equal(first, second)
    assert first.shape == (20, 5)


def test_baselines_do_not_read_future_values():
    first = forecast_baselines(history_close, future_close=np.ones(5), seed=17)
    changed = forecast_baselines(history_close, future_close=np.full(5, 999.0), seed=17)
    np.testing.assert_array_equal(first["persistence"], changed["persistence"])
    np.testing.assert_array_equal(first["recent_return_bootstrap"], changed["recent_return_bootstrap"])
```

- [ ] **Step 2: Run tests and confirm failure**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_baselines.py -q
```

- [ ] **Step 3: Implement two references**

`persistence` predicts zero cumulative return at every horizon step. `recent_return_bootstrap` computes log returns from the trailing 63 observed closes, samples contiguous five-return blocks with replacement, and converts each sampled path to cumulative simple return. If fewer than 63 observations exist, the origin is already ineligible through the common-origin contract.

- [ ] **Step 4: Run tests**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_baselines.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add evaluation/research/baselines.py tests/test_research_baselines.py
git commit -m "feat: add causal naive forecast references"
```

---

### Task 5: Add Zero-Shot Kronos Path Runner

**Files:**
- Create: `evaluation/research/kronos_runner.py`
- Test: `tests/test_research_runner.py`

**Interfaces:**
- Consumes: `CandidateConfig`, origin rows, strict frames, and cache writer.
- Produces: sampled cumulative close-return paths `(batch, S, H)` plus runtime metadata.

- [ ] **Step 1: Write failing path-shape, de-normalization, and seed tests**

```python
def test_kronos_runner_returns_sample_paths_not_only_mean(fake_predictor):
    paths = run_kronos_batch(fake_predictor, batch_fixture(), sample_count=3, seed=11)
    assert paths.shape == (2, 3, 5)


def test_shard_seed_is_stable_across_resume():
    first = run_fixture(shard_id="outer_2022-0003")
    resumed = run_fixture(shard_id="outer_2022-0003")
    np.testing.assert_array_equal(first, resumed)


def test_sample_mean_matches_frozen_batch_mean(real_predictor, batch_fixture):
    paths = run_kronos_batch(real_predictor, batch_fixture, sample_count=3, seed=11)
    frozen = run_frozen_batch_mean(real_predictor, batch_fixture, sample_count=3, seed=11)
    np.testing.assert_allclose(paths.mean(axis=1), frozen, rtol=1e-5)
```

- [ ] **Step 2: Run tests and confirm failure**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_runner.py -q
```

- [ ] **Step 3: Implement the adapter without touching model code**

Reuse `evaluation.inference_pipeline.generate_raw` to retain the existing vectorized stochastic paths. Keep lookback-only normalization and de-normalize every sample independently. Extract close column index `3`, then calculate cumulative return from the observed origin close.

Record model revision/hash, tokenizer revision/hash, parameter count, elapsed seconds, origins/second, and CUDA peak allocated memory. Runtime metrics are diagnostics for the `minimum_cost_reduction` gate, not product latency SLAs.

- [ ] **Step 4: Add resumable candidate execution**

For each fold and candidate, skip only cache shards whose key and SHA256 validate. On failure, retain completed shards and write a failure record containing candidate, fold, origin range, exception type, and command. Never substitute stale forecasts.

- [ ] **Step 5: Run runner tests**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_runner.py tests/test_inference_pipeline_console.py -q
```

Expected: PASS; no edits to frozen M0 files.

- [ ] **Step 6: Run CPU smoke with fake/tiny fixtures, then one real GPU batch**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation/run_research_eval.py smoke --config evaluation/configs/milestone2_research.yaml --profile smoke
```

Expected: both naive candidates and the configured real Kronos candidates produce schema-valid cache shards for two dates per fold. This stage is engineering validation only and must not select a model.

- [ ] **Step 7: Commit**

```powershell
git add evaluation/research/kronos_runner.py evaluation/run_research_eval.py tests/test_research_runner.py
git commit -m "feat: add resumable zero-shot Kronos runner"
```

---

### Task 6: Implement Locked Metrics And Date Aggregation

**Files:**
- Create: `evaluation/research/metrics.py`
- Test: `tests/test_research_metrics.py`

**Interfaces:**
- Consumes: canonical sample-path forecast rows.
- Produces: per-origin metrics, per-date metrics, and compact candidate summaries.

- [ ] **Step 1: Write failing metric tests with hand-calculated fixtures**

```python
def test_direction_zero_is_non_positive():
    assert direction(np.array([0.0, 0.1, -0.1])).tolist() == [-1, 1, -1]


def test_top10_requires_ten_eligible_symbols():
    with pytest.raises(ValueError, match="fewer than 10"):
        hit_rate_top10(nine_symbol_fixture())


def test_ensemble_crps_matches_two_sample_formula():
    samples = np.array([0.0, 2.0])
    assert ensemble_crps(samples, observation=1.0) == pytest.approx(0.5)


def test_locked_point_metrics_match_hand_calculation():
    frame = hand_calculated_ten_symbol_fixture()
    result = summarize_point_metrics(frame)
    assert result["DA"] == pytest.approx(60.0)
    assert result["MW-DA"] == pytest.approx(frame.correct_abs_return.sum() / frame.abs_return.sum() * 100)
    assert result["RankIC"] == pytest.approx(scipy.stats.spearmanr(frame.predicted, frame.actual).statistic)
    assert result["HitRate@Top10"] == pytest.approx((frame.actual > 0).mean() * 100)


def test_interval_metrics_use_10th_and_90th_percentiles():
    samples = np.arange(10, dtype=float)
    coverage, width = interval_metrics(samples, observation=4.5, lower=0.10, upper=0.90)
    assert coverage == 1.0
    assert width == pytest.approx(np.quantile(samples, 0.90) - np.quantile(samples, 0.10))
```

- [ ] **Step 2: Run tests and confirm failure**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_metrics.py -q
```

- [ ] **Step 3: Implement the exact metric contract**

At `H=5`, use ensemble mean cumulative return for DA, MW-DA, RankIC, and Top10 ranking. Compute marginal ensemble CRPS at each horizon step and average over `h=1..5`. Compute 80% coverage and width at `H=5` from the 10th and 90th percentiles. Report width in return units, not price units.

Aggregate RankIC and HitRate by date first; break equal predicted-return ties by ascending `security_id`. For DA and MW-DA, retain date-level sufficient statistics (`correct_count`, `origin_count`, `correct_abs_return`, `total_abs_return`) so pooled point estimates and bootstrap replicates preserve the locked formulas. CRPS, coverage, and width retain date sums and counts. Every summary includes valid dates, unique symbols, origin rows, sample count, and horizon.

- [ ] **Step 4: Run tests**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_metrics.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add evaluation/research/metrics.py tests/test_research_metrics.py
git commit -m "feat: add locked research evaluation metrics"
```

---

### Task 7: Add Paired Stationary Date-Block Inference

**Files:**
- Create: `evaluation/research/bootstrap.py`
- Test: `tests/test_block_bootstrap.py`

**Interfaces:**
- Consumes: two candidate per-date metric tables keyed by `fold_id,origin_date`.
- Produces: paired differences, 95% intervals, fold estimates, pooled estimates, and deterministic gate decisions.

- [ ] **Step 1: Write failing pairing and dependence tests**

```python
def test_comparison_intersects_identical_dates_before_bootstrap():
    result = compare_candidates(left_dates, right_dates, spec, seed=7)
    assert result.n_paired_dates == len(set(left_dates.date) & set(right_dates.date))


def test_stationary_bootstrap_is_reproducible():
    first = stationary_block_ci(series, mean_block=10, replicates=5000, seed=7)
    second = stationary_block_ci(series, mean_block=10, replicates=5000, seed=7)
    assert first == second


def test_comparison_rejects_nonmatching_origin_sets():
    with pytest.raises(ValueError, match="origin sets differ"):
        compare_candidates(left_origins, right_origins.iloc[:-1], spec, seed=7)
```

- [ ] **Step 2: Run tests and confirm failure**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_block_bootstrap.py -q
```

- [ ] **Step 3: Implement paired date-block bootstrap**

Retain each date's full cross-section and use a stationary bootstrap with expected block length ten forecast dates. Produce 5,000 replicates and percentile 95% intervals using the registered seed. For ratio metrics such as MW-DA, resample date-level numerators and denominators and recompute the ratio inside each replicate; do not average daily ratios. Report fold-specific intervals and a pooled date-block interval; never treat origin rows as independent samples.

- [ ] **Step 4: Implement deterministic gates**

Lookback screen on Kronos-small:

- choose `L=63` when its RankIC is within one standard error of the better lookback;
- require paired MW-DA lower bound versus `L=126` above `-1.0` percentage point;
- require CRPS ratio versus `L=126` at most `1.05`;
- otherwise choose `L=126`.

Small versus base confirmation:

- RankIC paired lower bound must exceed `-0.01`;
- MW-DA paired lower bound must exceed `-1.0` percentage point;
- CRPS ratio must be at most `1.05`;
- 80% coverage absolute-error increase must be at most `0.05`;
- measured latency or peak VRAM must improve by at least 25%.

`DA >= 52%` is reported separately as a product utility floor. Failing it prevents product promotion but does not prevent Kronos-small from remaining the M3 research backbone.

- [ ] **Step 5: Run tests**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_block_bootstrap.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add evaluation/research/bootstrap.py tests/test_block_bootstrap.py
git commit -m "feat: add paired date-block model inference"
```

---

### Task 8: Orchestrate Screen And Confirm Runs

**Files:**
- Modify: `evaluation/run_research_eval.py`
- Modify: `evaluation/research/artifacts.py`
- Test: `tests/test_research_runner.py`
- Create: `reports/milestone_2_research_eval/README.md`

**Interfaces:**
- Produces CLI stages `registry`, `smoke`, `screen`, `confirm`, and `report`.
- Produces `promotion.json` from screen; confirm consumes it without manual candidate editing.

- [ ] **Step 1: Write failing CLI orchestration tests**

```python
def test_confirm_requires_machine_generated_promotion(tmp_path):
    result = invoke_cli(["confirm", "--out-dir", str(tmp_path)])
    assert result.exit_code != 0
    assert "promotion.json" in result.output


def test_screen_promotion_is_deterministic(tmp_path):
    first = run_screen_fixture(tmp_path / "a")
    second = run_screen_fixture(tmp_path / "b")
    assert first["selected_lookback"] == second["selected_lookback"]
```

- [ ] **Step 2: Run tests and confirm failure**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_runner.py -q
```

- [ ] **Step 3: Implement the screen stage**

Run both naive references plus Kronos-small at `L=63` and `L=126` using `origin_stride=20`, `sample_count=5`, and all four outer folds. Write:

```text
reports/milestone_2_research_eval/screen/origins.csv
reports/milestone_2_research_eval/screen/per_date_metrics.csv
reports/milestone_2_research_eval/screen/comparisons.csv
reports/milestone_2_research_eval/screen/promotion.json
reports/milestone_2_research_eval/screen/manifest.json
```

The promotion file is entirely derived from Task 7's registered rule and includes the selected lookback, reason, metric estimates, confidence intervals, config hash, and screen artifact hashes.

- [ ] **Step 4: Implement the confirm stage**

Use `origin_stride=5`, `sample_count=20`, and all four outer folds. Always run naive references, Kronos-small at the selected lookback, and Kronos-base at the same lookback. When selected lookback is 63, also run Kronos-base at 126 to retain the historical-context comparator. Confirm must use a newly materialized common-origin registry and verify every candidate has exactly the same origin IDs.

- [ ] **Step 5: Document Colab commands**

`reports/milestone_2_research_eval/README.md` must include:

```bash
python evaluation/run_research_eval.py registry --config evaluation/configs/milestone2_research.yaml --profile screen
python evaluation/run_research_eval.py screen --config evaluation/configs/milestone2_research.yaml
python evaluation/run_research_eval.py registry --config evaluation/configs/milestone2_research.yaml --profile confirm
python evaluation/run_research_eval.py confirm --config evaluation/configs/milestone2_research.yaml
python evaluation/run_research_eval.py report --config evaluation/configs/milestone2_research.yaml
```

Document mounting Drive for the ignored cache, resume behavior, expected output paths, and the exact files to download back into the repo. Do not put secrets or mutable model aliases into the notebook instructions.

- [ ] **Step 6: Run orchestration tests**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests/test_research_runner.py tests/test_research_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit orchestration**

```powershell
git add evaluation/run_research_eval.py evaluation/research/artifacts.py tests/test_research_runner.py reports/milestone_2_research_eval/README.md
git commit -m "feat: orchestrate milestone 2 benchmark stages"
```

---

### Task 9: Execute Canonical M2 Benchmark And Publish Decision

**Files:**
- Create: `reports/milestone_2_research_eval/final/research_evaluation_report.md`
- Create: `reports/milestone_2_research_eval/final/metric_summary.csv`
- Create: `reports/milestone_2_research_eval/final/paired_comparisons.csv`
- Create: `reports/milestone_2_research_eval/final/runtime_summary.csv`
- Create: `reports/milestone_2_research_eval/final/manifest.json`
- Modify after acceptance: `SPEC.md`, `GEMINI.md`, project context, milestone map

**Interfaces:**
- Consumes: complete screen and confirm artifacts.
- Produces: frozen M2 decision and the only allowed handoff to M3.

- [ ] **Step 1: Run screen on Colab/GPU and preserve cache**

```bash
python evaluation/run_research_eval.py screen --config evaluation/configs/milestone2_research.yaml
```

Expected: all screen candidates complete on identical origins; `promotion.json` selects one lookback without manual editing.

- [ ] **Step 2: Review screen only for integrity**

Check missing candidate shards, duplicate origin IDs, nonmatching paired origins, non-finite paths, model revision mismatch, and lockbox dates. Do not alter thresholds after seeing metrics.

- [ ] **Step 3: Run confirmation once**

```bash
python evaluation/run_research_eval.py confirm --config evaluation/configs/milestone2_research.yaml
python evaluation/run_research_eval.py report --config evaluation/configs/milestone2_research.yaml
```

Expected: compact final report artifacts are generated; the prospective lockbox remains absent.

- [ ] **Step 4: Validate report completeness**

The report must state:

- dataset, universe, model, tokenizer, config, origin registry, code revision, and seeds;
- dates, symbols, origins, and sample counts per candidate/fold;
- RankIC, HitRate@Top10, MW-DA, DA, CRPS, 80% coverage and width;
- paired date-block intervals against naive and base references;
- development/unseen-holdout, exchange, listing-age, liquidity, and market-regime slices;
- runtime, throughput, and peak VRAM;
- selected lookback and whether small is non-inferior and materially cheaper;
- whether `DA >= 52%` was met;
- the explicit limitation that sector stratification was unavailable in M1;
- the explicit limitation that VN150 is current-membership and survivorship-biased;
- one of three conclusions: `small preferred for M3`, `base retained`, or `insufficient evidence`.

- [ ] **Step 5: Run the full verification suite**

```powershell
$env:PYTHONPATH='finetune_csv'; C:\Users\USER\anaconda3\envs\stock\python.exe -m pytest tests -q
C:\Users\USER\anaconda3\python.exe C:\Users\USER\.codex\skills\.system\skill-creator\scripts\quick_validate.py .codex\skills\vn-stock-market-radar
git diff --check
```

Expected: all tests and skill validation pass; no whitespace errors.

- [ ] **Step 6: Update project context only after evidence exists**

Increment `SPEC.md` version, mark M2 complete, record the selected lookback/backbone decision, and make M3 the next active milestone. If evidence is insufficient, record that result without forcing a winner; M3 may remain blocked or proceed with both finalists only through a newly approved plan.

- [ ] **Step 7: Commit the M2 freeze**

```powershell
git add evaluation reports/milestone_2_research_eval/final SPEC.md GEMINI.md .codex/skills/vn-stock-market-radar
git commit -m "chore: freeze milestone 2 research evaluation"
```

Expected: cache files remain ignored; committed manifest hashes every compact decision artifact.

---

## Acceptance Gates

M2 closes only when all are true:

1. M1 has its own verified commit and dataset hash.
2. Four outer folds cover 2022-2025; no evaluated target reaches 2026 or the prospective lockbox.
3. Every paired candidate comparison has identical origin IDs, targets, seeds, and sample counts.
4. Both lookbacks are evaluated on common origins; one is selected by the registered screen rule.
5. Persistence, recent-return bootstrap, Kronos-small, and Kronos-base are present in confirmation evidence.
6. Canonical inference uses paired stationary date-block intervals, not window-level t-tests.
7. Probabilistic metrics consume sample paths, not only the ensemble mean.
8. Reports contain counts, regime/data slices, runtime, provenance, limitations, and artifact hashes.
9. The prospective lockbox remains closed and absent from model-selection outputs.
10. The project records `small preferred for M3`, `base retained`, or `insufficient evidence`; no winner is forced.

## Explicitly Deferred

- Any LoRA or full fine-tuning.
- Forecast-tail CE masking/weighting.
- Changing `H=5` or adding more lookbacks.
- Tokenizer adaptation.
- Portfolio backtests, Sharpe, MaxDrawdown, costs, and turnover.
- Path Viewer/frontend work.
- Dynamic historical universe reconstruction.
- Tick/intraday streaming.

## Estimated Compute Shape

- Smoke: two dates per fold, two samples; engineering validation only.
- Screen: approximately 12-13 dates per fold (`stride=20`), two Kronos-small lookbacks, five samples.
- Confirm: approximately 50 dates per fold (`stride=5`), two or three Kronos arms, 20 samples, up to 150 eligible symbols/date.
- Cache/resume is mandatory because confirmation may involve roughly 25,000-30,000 common symbol-origins per model arm.

The screen is intentionally cheap. The confirm run is the first expensive M2 action and must not start until config, origins, metrics, bootstrap, and promotion rules all pass tests.
