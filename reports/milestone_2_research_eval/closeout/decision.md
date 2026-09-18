# M2 Closeout: Decision Ledger

Closes Milestone 2 under SPEC section 11.4. Every row names the rule, the metric,
the threshold, the result and where the evidence lives. `manifest.json` beside
this file hashes every registration, evidence file, config, report and
evaluation output listed here, and records the lockbox check.

Nothing here is new evidence. It collects decisions already read and recorded,
so each one can be checked against its source in one step.

## 1. Gates read confirmatorily

M2.10: 683 dates never used by any earlier Kronos run, 93,637 origins per arm,
run on the L4. Intervals are paired stationary date-block bootstrap at 95%,
5,000 replicates, widened by the section 8.11 seed correction. Source:
`docs/evidence/3.9-m2-10-full-registry-evidence.md`, full reading in
`full_registry/decision.md`, numbers in
`full_registry/paired_inference/paired_comparisons.csv`.

| gate | rule | metric | pass condition | `small_l126` result | verdict |
|---|---|---|---|---|---|
| cross-sectional | 8.10 | RankIC vs `short_term_reversal` | interval excludes zero, in favour | `0.0208` vs `0.0154`, `+0.0054` `[-0.0161, +0.0268]` | **fail** |
| naive | 8.6 rule 5 | RankIC vs `recent_return_bootstrap` | interval excludes zero, in favour | `+0.0287` `[+0.0072, +0.0503]` | pass |
| non-inferiority, RankIC | 8.6 rule 4 | small minus base | lower bound above `-0.01` | `+0.0010` `[-0.0089, +0.0109]` | pass, **provisional** |
| non-inferiority, MW-DA | 8.6 rule 4 | small minus base | lower bound above `-1.0` pp | `+1.1711` `[-0.2868, +2.6289]` | pass |

The RankIC non-inferiority reading stays provisional permanently: the
contingency of section 8.12 fired on it, and the seed measurement that would
resolve it was withdrawn by the SPEC 2.16 amendment. It may not be cited as
settled in either direction.

**Zero-shot Kronos does not beat a five-line formula at ranking.** No metric has
either arm beating `short_term_reversal` with an interval excluding zero.

## 2. Measurement decisions

| decision | rule | result | source |
|---|---|---|---|
| backbone for M3 | 8.6 rule 4 + distributional intervals | **Kronos-small**. Base scores MW-DA `49.40` at 4x compute; small is better on CRPS, coverage and width with intervals excluding zero | 3.9 |
| seed noise, pooled | 8.11.4 | immaterial: `sd_seed` RankIC `0.001849` against a threshold of `0.003763` | 3.8 |
| seed noise, per fold | 8.11 | material: up to 83% of a fold's mean at 49 dates. Every fold and slice reading must state its precision is unmeasured | 3.8 |
| sampler | 8.13 | **unchanged**, `T 0.6, top_p 0.9`. The CRPS winner failed the RankIC guard | 3.11 |
| `sample_count` | exploratory | **10**. Ten samples keep 87% of the ranking signal; the loss is shared across arms, so paired contrasts barely move | `docs/research/2026-09-07-ranking-statistic-and-sample-count.md` |
| ranking statistic | exploratory | **sample mean**. No dispersion-weighted variant beats it; width alone has RankIC `-0.0023` | same note |
| interval ceiling | analytic | a perfectly calibrated sampler reaches coverage `0.66`, not `0.80`, at ten samples | 3.10 |
| calibration gap | 8.13 | coverage `0.393` against `0.66`. 72% of the gap is sampler configuration; the residual `0.073` belongs to the model | 3.9, 3.11 |
| context length | 8.15 | **`L=126` kept**, the only confirmed arm. `L=40` with normalizer 126 matches it on RankIC at 2.4x throughput, as a screen only | 3.13 |
| normalizer | 8.6 rule 1, 8.15 | **126**. A short normalizer is what costs the ranking signal, at every context length tested | 3.3, 3.13 |
| host | 8.14 | results reproduce bitwise on one host. Cross-host equivalence is **unresolved**, so a local and an L4 result MUST NOT be paired | 3.12 |

## 3. Withdrawn and failed

Recorded as they are, never restated as met.

| item | status | reason | where |
|---|---|---|---|
| `base_l126` seed noise | withdrawn | base leaves the project; measuring it would cost about 26 hours locally | SPEC M2 exit scope amendment |
| comparability with M0 | withdrawn | M0 used a different dataset, backbone, origin set and sampler | same |
| `worktree_dirty: false` | failed | no run can satisfy it; the manifest is written after outputs exist | 3.9 |
| section 8.14 premise | defective | M2.5 had run on the same host, so the test was vacuous | 3.12 |

## 4. Open questions carried into M3

| question | why it is open | what would settle it |
|---|---|---|
| does `L=40`, normalizer 126, match `L=126` | screen on spent dates only | a confirmatory run on dates not used to select it |
| is `H=5` the right horizon | never varied in M2 | section 6.4, before the lockbox |
| does a host change move results | 3.12 was vacuous | a local re-run of an L4 arm with the same `arm_id` and dates |
| is the ranking signal tradeable | RankIC rises as liquidity falls, `0.0162 / 0.0313 / 0.0466` at M2.7 | a registered per-tier contrast; an M5 constraint |

## 5. What a fine-tuned model must clear

From SPEC sections 8.4, 8.10 and 12. M3's registration fixes the numbers not
yet fixed here, before any training.

1. **Cross-sectional gate.** RankIC against `short_term_reversal`, paired 95%
   interval with seed correction, excluding zero in its favour. On the 683 dates
   the formula scores `0.0154`, and the achieved half-width was about `0.0215`.
   That half-width is a property of the design rather than a threshold, and it
   implies a fine-tuned model needs RankIC somewhere near `0.037` on those dates
   before the interval can clear zero.
2. **Beat zero-shot.** RankIC against zero-shot `small_l126`, run on the **same
   host** in the same run, interval excluding zero.
3. **Naive gate.** Against `recent_return_bootstrap`. Necessary, not sufficient.
4. **Guardrails.** MW-DA and calibration (CRPS, coverage against the `0.66`
   ceiling) must not degrade beyond a non-inferiority bound. **The bound is not
   yet registered** and must be, before training.
5. **Stability.** Per-fold results reported with their unmeasured precision
   stated; a gain carried by one fold is reported as such.

Failing every one of these is a valid M3 outcome. SPEC section 12: keeping
zero-shot or stopping fine-tuning is a result.

## 6. Lockbox

No origin or target in the registry, and no date in any M2 per-date output,
reaches 2026-01-01. The latest origin is 2025-12-24 and the latest target end is
2025-12-31. `manifest.json` records the check.
