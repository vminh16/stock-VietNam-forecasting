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

M2.1 is complete. The canonical common-origin registry contains 133,937
symbol-origins across 977 dates and 147 symbols for folds 2022-2025. Every row
supports both `L=63` and `L=126` at `H=5` in one segment. The minimum daily
cross-section is 128 symbols, no duplicate origin exists, and the last target
is 2025-12-31. `TCX`, `VCK`, and `VPX` have no eligible origin because their
short histories do not support the registered folds. The ignored registry is
`data/evaluation/m2_1/common_origins.csv.gz`; its SHA256 is
`dcd71d14c5016b721111172d6a2ff384122eb74d2cc9c27252d359857e6726c6`.
Compact provenance is under
`reports/milestone_2_research_eval/origin_registry/`. The 2026 lockbox remains
closed.

M2.2 is complete. Both causal naive references were scored on every M2.1 origin
with 20 sample paths and seed `20260812`. Pooled 2022-2025: `persistence` DA
50.88, MW-DA 48.04, RankIC 0.0000, HitRate@Top10 45.84, CRPS 0.029795;
`recent_return_bootstrap` DA 49.53, MW-DA 50.11, RankIC -0.0086,
HitRate@Top10 50.30, CRPS 0.024238, 80% coverage 0.6869, width 0.1153. Two
findings matter for later decisions: the trivial `persistence` down call reaches
DA 55.96 in the falling 2022 fold, so DA above the 52% floor is not skill; and
the bootstrap reference under-covers its nominal 80% band, so coverage is a live
diagnostic, not a formality. Compact provenance is under
`reports/milestone_2_research_eval/naive_references/`; per-date metrics stay in
the ignored `data/evaluation/m2_2/`.

M2.3 is complete. `evaluation/research/bootstrap.py` implements the paired
stationary date-block bootstrap (expected block ten dates, 5,000 replicates,
seed `20260901`) and replaces the diagnostic t-test. Measured resolution over
977 paired dates for two weakly correlated candidates: 95% interval half-width
3.79 pp for DA, 6.69 pp for MW-DA, 0.0204 for RankIC, 2.36 pp for
HitRate@Top10. The 52% DA floor is therefore not decidable against the 51.63%
zero-shot reference, and a RankIC gain below roughly 0.02 cannot be separated
from zero against a naive reference. Evidence is under
`reports/milestone_2_research_eval/paired_inference/`.

M2.5 is complete. Five zero-shot arms ran on 13,431 common origins over 98
strided dates with ten sample paths, `T=0.6`, `top_p=0.9`, seed `20260901`.
Pooled RankIC: `small_l63` 0.0013, `small_l126` 0.0247, `small_l63_norm126`
0.0224, `base_l63` 0.0149, `base_l126` 0.0267, against 0.0050 for
`recent_return_bootstrap`. No arm cleared the registered naive gate; `base_l126`
beats `persistence` at +0.0267 with interval [+0.0081, +0.0460] but reaches only
+0.0217 with interval [-0.0238, +0.0705] against the bootstrap reference. The
lookback gap decomposes mostly into normalization rather than context. At
`L=126` small and base differ by -0.0020 RankIC, a dead heat that the 98-date
design cannot certify against the registered 0.01 margin; that needs about 210
paired dates. All arms are overconfident: 0.33 to 0.40 coverage inside a nominal
80% band, and worse CRPS than the naive bootstrap. Cost gap is 6.7x in
throughput. Evidence is under
`reports/milestone_2_research_eval/zero_shot_screen/`.

M2.6 is complete and training-free. It labelled all 133,937 origins with two
pre-registered slice keys and recomputed the locked metrics inside each slice.
`liquidity_tier` splits each date's cross-section into three balanced tiers by
the trailing 63-session median `amount`; median amount is 133.8M, 36.3M, and
4.4M, and every tier keeps at least 42 symbols on every date, so no date is
dropped. `symbol_group` is a salted hash of `security_id` into five groups of
30/27/24/27/39 symbols that reads no price and no result, which is what makes an
unseen-symbol holdout honest; its liquidity balance is uneven by chance, with
`group_2` at 0.181 and `group_1` at 0.417 of origins in the top tier against
0.333 under a balanced split. The slice table SHA256 is
`8e474264cfc8b16af3dd2b053d9e965cdee2608f625f46556c57cc6aa83bd61b`.

Two consequences matter. First, `persistence` reaches DA 52.87 inside `tier_2`
against 50.12 in `tier_0`, so the 52% floor is cleared by a zero-information
down call exactly where prices fall hardest. Second, every runner now persists
per-origin metrics, because per-date aggregates cannot be sliced afterwards; the
M2.5 arms predate that artifact and therefore carry no slice evidence at all.
Evidence is under `reports/milestone_2_research_eval/origin_slices/` and
`reports/milestone_2_research_eval/metric_slices/`.

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
The legacy paired t-test in `evaluation/inference_pipeline.py` stays diagnostic
only. Canonical inference is the M2.3 paired stationary date-block bootstrap,
and CRPS plus interval coverage/width ship with the M2.2 metric layer.

## Current Sequence

1. Zero-shot reference: accepted.
2. Fixed VN150 raw/curated foundation and readiness closure: conditional complete.
3. M2.1 temporal common-origin registry: complete.
4. M2.2 causal naive references and locked metric implementation: complete.
5. M2.3 paired stationary date-block inference: complete.
6. M2.4 training-free data diagnostics: complete.
7. M2.5 zero-shot screen: complete, no arm cleared the naive gate.
8. M2.6 origin slices and per-origin metric persistence: complete.
9. Confirmation run with about 210 paired dates, at least two seeds, and an
   unseen-symbol holdout, then the M3 decision: next.
10. Kronos-small objective and LoRA study.
11. Path Viewer.
12. Ranking and risk radar.
13. Daily operations, cache, and deployment.

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
