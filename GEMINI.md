# GEMINI.md - Agent Instructions for Stock-VN-Forecasting

> This file is the operational companion to `SPEC.md`. Read `AGENTS.md` first,
> then this file, then `SPEC.md`, as required by the repository first-read rule.
> `SPEC.md` is the source of truth for product, data, model, evaluation, and
> milestone decisions.

## Project Identity

Stock-VN-Forecasting is an end-to-end Vietnam Stock Market Radar built around
Kronos. The model generates probabilistic daily paths; the application derives
interpretable ranking and risk features from those paths.

The project is research-first. It does not provide investment advice and is not
currently optimized for commercialization.

## Decision States

Do not treat every number in the repository as fixed.

- **Invariant:** requires explicit user approval and a spec revision.
- **Frozen baseline:** reproducible historical reference, not a quality claim.
- **Research candidate:** must pass the protocol in `SPEC.md`.
- **Deferred:** outside the current milestone.

Current incumbents `lookback=126`, `horizon=5`, Kronos-base, 50 symbols, and
Q/V LoRA rank 8 are baselines or candidates. They are not proven optima.

## Technical Stack

- Python 3.10+
- PyTorch
- Daily data from `vnstock`
- pandas, numpy, scipy, PyYAML, huggingface_hub
- Single GPU or `torchrun` multi-GPU

## Invariants

1. Use daily bars only.
2. Use temporal or nested walk-forward validation; never random time-series
   splits.
3. Keep windows inside one security.
4. Use point-in-time preprocessing information. Treat the fixed VN150 M1
   population as a conditional benchmark, not an unbiased historical universe.
5. Do not modify `model/kronos.py` or `model/module.py` unless explicitly
   instructed.
6. Do not add prediction heads or new loss families by default.
7. Derive Trend, ranking, and Risk from forecast outputs and business logic.
8. Keep every output traceable to data, universe, model, config, code revision,
   origin, and seed.

The original S1+S2 Cross-Entropy remains the loss family. Forecast-position
masking or weighting is a research candidate, not permission to implement it
without a reviewed experiment plan.

## Current Research Direction

- Kronos-base is the frozen zero-shot reference.
- Kronos-small is the primary adaptation and deployment candidate.
- Freeze the pretrained tokenizer for the first small-model experiments.
- Compare LoRA target modules at equal trainable-parameter budget.
- Gate full fine-tuning behind evidence that broad LoRA is underfitting.
- Build the approved fixed VN150 strict dataset before model work. Dynamic
  point-in-time universe reconstruction is deferred.
- Compare only `L in {63, 126}` at `H=5` in the next research step.

## Data Contract

Each security must remain separately grouped, preferably one CSV per symbol.
Canonical columns are:

```csv
timestamps,open,close,high,low,volume,amount
2024/01/02 9:00,30500,31000,31200,30200,1500000,46500000000
```

Model feature order is `[open, high, low, close, volume, amount]`.

For `vn150_strict_v2`, prices are retained in KBS thousand-VND units and
corporate-action adjustment semantics are unverified. `amount` is exactly the
`volume * OHLC4` Kronos compatibility proxy, not provider turnover. Large
overnight jumps are audited but never rewritten or used to split data without
point-in-time reference-price or corporate-action evidence.

Do not zero-fill or forward-fill missing history. M1 uses `valid`,
`unavailable`, and implicit `pre_history`; every unavailable exchange session
splits the sequence. Historical identity and detailed status reconstruction are
deferred.

## Evaluation Contract

Use a small metric set tied to decisions:

- Forecast direction: `MW-DA`, `DA`
- Ranking: `RankIC`, `HitRate@Top10`
- Probabilistic path: `CRPS`, interval coverage/width
- Portfolio sanity later: `Sharpe`, `MaxDrawdown`

The app is ranking-oriented, so `RankIC` is the primary product metric. A model
must still pass forecast and calibration guardrails. `DA >= 52%` is a utility
floor, not statistical significance.

Compare models on identical dates, symbols, origins, sample counts, and seeds.
Use paired date-block inference because overlapping horizons and common market
factors invalidate independent-window tests.

M0 locks the four point metrics and provenance only. Before promoting a new
model, M2 must add paired date-block confidence intervals plus CRPS and interval
coverage/width. The current paired t-test output is diagnostic, not canonical.

## Baseline Status

- M0 is closed with zero-shot Kronos-base final as the accepted reference.
- The former fine-tuned v2 result has mismatched date coverage and is
  noncanonical.
- Do not claim fine-tuning improvement from the mixed-coverage report.
- M1.1 data readiness is conditionally complete: there is no structural blocker
  for M2 evaluation, while price-adjustment semantics and the derived amount
  proxy remain explicit limitations.
- M2.1 common-origin registry is complete for 2022-2025 with 133,937 origins,
  977 dates, and 147 symbols. The 2026 lockbox remains closed.
- M2.2 naive references are complete on those origins. Pooled 2022-2025:
  `persistence` DA 50.88, MW-DA 48.04, RankIC 0.0000; `recent_return_bootstrap`
  DA 49.53, MW-DA 50.11, RankIC -0.0086, CRPS 0.024238, 80% coverage 0.6869.
- The `persistence` down call reaches DA 55.96 in the 2022 fold, so DA above the
  52% floor is not evidence of skill. Judge candidates on MW-DA and RankIC.
- M2.3 paired date-block bootstrap is complete and replaces the diagnostic
  t-test. On 977 paired dates the 95% interval half-width is 3.79 pp for DA,
  6.69 pp for MW-DA, 0.0204 for RankIC, and 2.36 pp for HitRate@Top10.
- Consequence: the 52% DA floor is not decidable against the 51.63% zero-shot
  reference, and a RankIC gain below about 0.02 cannot be separated from zero
  against a naive reference. Pre-register the target effect size before M3.
- M2.5 zero-shot screen is complete on 13,431 origins over 98 dates. Pooled
  RankIC: small_l63 0.0013, small_l126 0.0247, small_l63_norm126 0.0224,
  base_l63 0.0149, base_l126 0.0267, recent_return_bootstrap 0.0050.
- No arm cleared the registered naive gate. base_l126 versus
  recent_return_bootstrap is +0.0217 with interval [-0.0238, +0.0705].
- The lookback gap decomposes mostly into normalization: borrowing the
  126-session normalizer while keeping 63 rows recovers -0.0211 of the -0.0235
  confounded gap, and the context-only contrast is -0.0023.
- Every arm covers only 0.33 to 0.40 inside its nominal 80% band and has worse
  CRPS than the naive bootstrap. Do not describe Kronos intervals as calibrated.
- Training remains out of scope until a confirmation run with roughly 210 paired
  dates settles the non-inferiority margin.
- M2.6 registered two evaluation slice keys: `liquidity_tier` (three
  point-in-time tiers by trailing 63-session median amount) and `symbol_group`
  (five salted-hash groups of security_id, for unseen-symbol holdouts).
- Every runner now persists per-origin metrics. A run that keeps only per-date
  aggregates cannot be sliced afterwards, so the M2.5 arms have no slice
  evidence; slice results for a model begin at the confirmation run.
- Inside the illiquid `tier_2`, the zero-information `persistence` reference
  reaches DA 52.87 against 50.12 in the liquid `tier_0`. A slice DA above the
  52% floor is even weaker evidence of skill than a pooled one.
- M2.7 confirmed `small_l126` and `base_l126` on 196 dates disjoint from the
  screen. Pooled RankIC 0.0270 and 0.0300. Both clear the naive gate for the
  first time: +0.0446 [+0.0134, +0.0741] and +0.0476 [+0.0104, +0.0831].
- The registered backbone margin still fails: small versus base is -0.0030
  [-0.0215, +0.0158] against a required lower bound of -0.01. The interval is too
  wide, not the difference too large.
- Achieved half-width is 0.0186 against a 0.0100 margin. The old estimate of 210
  dates was wrong; the margin needs about 681 paired dates, ~22.5 GPU hours for
  two arms. Do not renegotiate the margin after seeing a result it would flip.
- RankIC rises monotonically as liquidity falls, 0.0162/0.0313/0.0466 for small.
  The ranking signal lives in the least tradeable third of the market. Treat this
  as an M5 product constraint; testing it needs a registered Kronos-versus-naive
  contrast per tier, which does not exist yet.
- Calibration is still broken on fresh dates: coverage 0.398 and 0.359 against a
  nominal 0.80.

## Commands

```powershell
# Unit tests
$env:PYTHONPATH='finetune_csv'; python -m pytest tests -q

# M2.7 confirmation: run, then registered inference, then slices
python evaluation/run_zero_shot_screen.py --config evaluation/configs/m2_7_confirmation.yaml
python evaluation/run_paired_comparison.py --config evaluation/configs/m2_7_paired_inference.yaml
python evaluation/run_metric_slices.py --config evaluation/configs/m2_7_metric_slices.yaml
python evaluation/run_paired_comparison.py --config evaluation/configs/m2_7_slice_inference.yaml

# Slice labels, then metrics inside each slice; neither runs a model
python evaluation/run_origin_slices.py --config evaluation/configs/m2_6_origin_slices.yaml
python evaluation/run_metric_slices.py --config evaluation/configs/m2_6_metric_slices.yaml

# Frozen zero-shot evaluation
python evaluation/inference_pipeline.py --config evaluation/configs/milestone0_baseline_zero_shot.yaml --mode final

# Current predictor training entry point; config remains an incumbent baseline
python finetune_csv/finetune_base_model.py --config finetune_csv/configs/vn50.yaml
```

Do not run expensive training until the experiment has a pre-registered data
version, folds, candidates, budget, promotion rule, and acceptance criterion.

## Coding Discipline

- Follow `AGENTS.md` without exception.
- Make the smallest change that satisfies the active milestone.
- Do not refactor adjacent code or remove pre-existing dead code.
- Use tests before implementation for behavior changes.
- Preserve user changes in a dirty worktree.
- State assumptions and stop when requirements are genuinely ambiguous.

## First-Read References

- `SPEC.md`
- `.codex/skills/vn-stock-market-radar/references/project-context.md`
- `.codex/skills/vn-stock-market-radar/references/milestone-map.md`
- `reports/milestone_0_baseline_freeze/baseline_freeze_report.md`
- `finetune_csv/README.md`
