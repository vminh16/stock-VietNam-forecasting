# Project Context

## Product Goal

Build an end-to-end Kronos-powered Vietnam Stock Market Radar for research.
The application is ranking-oriented, while the model remains forecast-first:
probabilistic paths produce expected-return, direction, uncertainty, and risk
features that drive cross-sectional comparison.

The project does not currently target commercialization or investment advice.

## Source Of Truth

Read `SPEC.md` before project-level decisions. It distinguishes invariants,
frozen baselines, research candidates, and deferred work. Do not promote a
candidate into a fixed rule without evidence and a spec revision.

## Baseline Evidence

The current dataset contains 50 daily symbol files, approximately 99,851 rows,
and approximately 56,205 valid pre-2023 train bars. Histories were aligned to a
common calendar; SSB has a concentrated block of 692 missing/zero rows. The
50-symbol panel is a baseline, not the target universe.

The accepted model reference is the Kronos-base zero-shot final run:

- Test DA: `51.6343`
- Test MW-DA: `49.0046`
- Test RankIC: `-0.0026`
- Test HitRate: `49.7500`

The former fine-tuned v2 artifact has different date coverage and is
noncanonical. Do not use mixed-coverage deltas to claim improvement. `DA >= 52`
is an operational floor, not a significance test.

M0 is closed with the zero-shot-only canonical manifest. M1 fixed VN150 data
foundation is complete. M1.1 closes data readiness conditionally at
`reports/milestone_1_data/vn150_strict_v2/`.

The frozen M1 dataset contains 279,973 raw rows and 278,303 strict valid rows
from 2018-08-09 through 2026-08-07. It has 1,594 contiguous segments and
provides 247,999 nominal `63/5` windows or 229,734 nominal `126/5` windows.
`VCK`, `VPX`, and `TCX` have fewer than 252 valid sessions. The community API
does not return traded amount, so all curated `amount` values are explicitly
marked `derived_ohlc4`; do not describe them as provider-reported turnover.

`vn150_strict_v2` centralizes feature/normalization contracts and records price
units, canonical timestamp semantics, and amount provenance in its manifest.
The readiness audit found zero duplicate symbol-session keys, non-finite
features, invalid curated OHLC rows, timestamp violations, or session gaps
inside segments. It records 19 overnight jumps above 17% for review without
rewriting prices or splitting segments. Lookback-only clipping affects 0.0667%
of sampled values at `L=63` and 0.0942% at `L=126`; no sampled window has a
constant feature. Status is `CONDITIONAL` because KBS corporate-action
adjustment semantics remain unverified and `amount` is a deterministic proxy.

## Research Direction

- Daily data remains invariant.
- Use the fixed 150-symbol benchmark frozen on 2026-08-09. It is conditional on
  current membership and cannot support survivorship-free market claims.
- Keep raw snapshots immutable and split strict sequences at every unavailable
  exchange session; never impute missing history.
- Keep Kronos-base as the zero-shot reference.
- Use Kronos-small as the primary adaptation/deployment candidate.
- Freeze the pretrained tokenizer for initial small-model experiments.
- Treat Q/V rank 8 as an incumbent, not an optimum. Compare Q/V, QKVO, MLP, and
  all-linear LoRA at equal trainable-parameter budget.
- Gate full fine-tuning behind evidence that broad LoRA is underfitting.
- Compare `L={63,126}` at fixed `H=5` after the data foundation is frozen.
- Test alignment of the original all-position token CE against forecast-tail
  masking/weighting before expensive adaptation. This requires a reviewed plan.

## Effective Sample Warning

The baseline's 49,727 sliding train windows are highly overlapping. A
non-overlap planning proxy is only about 377 blocks, but actual effective sample
size must be estimated from date-level autocorrelation and cross-sectional
dependence. Never report raw windows as independent observations.

## Metric Contract

- Forecast direction: `MW-DA`, `DA`
- Ranking: `RankIC`, `HitRate@Top10`
- Probabilistic path: `CRPS`, interval coverage/width
- Portfolio sanity later: `Sharpe`, `MaxDrawdown`

RankIC is the primary product metric because the app is a radar. Model promotion
is still forecast-gated and requires paired date-block confidence intervals.
The current paired t-test is diagnostic only; M2 must add block bootstrap plus
CRPS and interval coverage/width before any model is promoted.

## Current Sequence

1. Zero-shot reference: accepted.
2. Fixed VN150 raw/curated foundation and readiness closure: conditional complete.
3. M2.1 temporal common-origin registry: next.
4. Kronos-small objective and LoRA study.
5. Path Viewer.
6. Ranking and risk radar.
7. Daily operations, cache, and deployment.

## Non-Negotiables

- Do not modify Kronos architecture without explicit approval.
- Do not add Trend or Risk heads.
- Do not add a new loss family by default.
- Do not use random splits or current-universe backfills.
- Do not let windows cross symbol boundaries.
- Do not run expensive training without pre-registered data, folds, candidates,
  budget, promotion rule, and acceptance criteria.
- Do not present output as investment advice.

## Repo Anchors

- `AGENTS.md`
- `SPEC.md`
- `GEMINI.md`
- `finetune_csv/README.md`
- `reports/milestone_0_baseline_freeze/`
- `reports/walkthrough_finetuning.md`
- `reports/walkthrough_evaluation_fix.md`
