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

M0 is closed with the zero-shot-only canonical manifest. M1 point-in-time data
and universe work is active.

## Research Direction

- Daily data remains invariant.
- Use point-in-time dynamic universes and ragged histories; never fill
  pre-listing periods.
- Evaluate data scale at 50, 150, and 300 symbols on a fixed point-in-time target
  universe.
- Keep Kronos-base as the zero-shot reference.
- Use Kronos-small as the primary adaptation/deployment candidate.
- Freeze the pretrained tokenizer for initial small-model experiments.
- Treat Q/V rank 8 as an incumbent, not an optimum. Compare Q/V, QKVO, MLP, and
  all-linear LoRA at equal trainable-parameter budget.
- Gate full fine-tuning behind evidence that broad LoRA is underfitting.
- Treat lookback 126 and horizon 5 as incumbents. Research candidates are
  `L={40,63,126,252}` and `H={3,5,10,20}`, selected sequentially.
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
2. Point-in-time data and universe foundation.
3. Research evaluation harness and small/base diagnostics.
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
