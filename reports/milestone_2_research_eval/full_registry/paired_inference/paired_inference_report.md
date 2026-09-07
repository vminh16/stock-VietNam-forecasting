# M2.3 Paired Date-Block Inference Report

## Decision

This report replaces the diagnostic paired t-test with the canonical paired
stationary date-block bootstrap required by SPEC section 8.5. It currently
compares the two causal naive references only; no Kronos candidate has been
evaluated yet, so no model promotion decision follows from it.

## Registered Inference

- Method: stationary block bootstrap over forecast dates
- Expected block length: 10 dates
- Replicates: 5,000
- Confidence: 95% percentile interval
- Seed: 20260901
- Paired dates (pooled): 683
- Metrics: DA, MW-DA, RankIC, HitRate@Top10, CRPS, coverage, interval_width

### `base_l126` versus `momentum_126_21`

| metric | base_l126 | momentum_126_21 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.4284 | 50.6338 | +0.7946 | [-1.3680, +3.1091] | insufficient evidence |
| MW-DA | 49.4025 | 50.9754 | -1.5729 | [-5.6869, +2.6257] | insufficient evidence |
| RankIC | 0.0198 | 0.0091 | +0.0107 | [-0.0168, +0.0392] | insufficient evidence |
| HitRate@Top10 | 51.0542 | 50.1464 | +0.9078 | [-1.0835, +2.9722] | insufficient evidence |
| CRPS | 0.0261 | 0.0306 | -0.0045 | [-0.0053, -0.0038] | momentum_126_21 higher |
| coverage | 0.3526 | 0.0004 | +0.3523 | [+0.3349, +0.3695] | base_l126 higher |
| interval_width | 0.0453 | 0.0000 | +0.0453 | [+0.0404, +0.0512] | base_l126 higher |

### `base_l126` versus `persistence`

| metric | base_l126 | persistence | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.4284 | 51.0098 | +0.4186 | [-1.8053, +2.6417] | insufficient evidence |
| MW-DA | 49.4025 | 48.5812 | +0.8212 | [-3.5876, +5.4522] | insufficient evidence |
| RankIC | 0.0198 | 0.0000 | +0.0198 | [+0.0052, +0.0348] | base_l126 higher |
| HitRate@Top10 | 51.0542 | 45.1245 | +5.9297 | [+3.9971, +7.8624] | base_l126 higher |
| CRPS | 0.0261 | 0.0298 | -0.0036 | [-0.0043, -0.0031] | persistence higher |
| coverage | 0.3526 | 0.0329 | +0.3197 | [+0.3036, +0.3358] | base_l126 higher |
| interval_width | 0.0453 | 0.0000 | +0.0453 | [+0.0404, +0.0512] | base_l126 higher |

### `base_l126` versus `recent_return_bootstrap`

| metric | base_l126 | recent_return_bootstrap | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.4284 | 49.4922 | +1.9362 | [-0.3611, +4.1258] | insufficient evidence |
| MW-DA | 49.4025 | 50.3228 | -0.9203 | [-5.2178, +3.0303] | insufficient evidence |
| RankIC | 0.0198 | -0.0079 | +0.0278 | [+0.0040, +0.0523] | base_l126 higher |
| HitRate@Top10 | 51.0542 | 49.6925 | +1.3616 | [-0.3514, +3.0454] | insufficient evidence |
| CRPS | 0.0261 | 0.0242 | +0.0019 | [+0.0015, +0.0024] | base_l126 higher |
| coverage | 0.3526 | 0.6848 | -0.3322 | [-0.3500, -0.3132] | recent_return_bootstrap higher |
| interval_width | 0.0453 | 0.1153 | -0.0699 | [-0.0768, -0.0636] | recent_return_bootstrap higher |

### `base_l126` versus `short_term_reversal`

| metric | base_l126 | short_term_reversal | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.4284 | 50.2867 | +1.1416 | [-0.6538, +3.2023] | insufficient evidence |
| MW-DA | 49.4025 | 47.7662 | +1.6363 | [-1.6272, +5.0060] | insufficient evidence |
| RankIC | 0.0198 | 0.0154 | +0.0044 | [-0.0159, +0.0266] | insufficient evidence |
| HitRate@Top10 | 51.0542 | 49.3558 | +1.6984 | [+0.1318, +3.2943] | base_l126 higher |
| CRPS | 0.0261 | 0.0391 | -0.0130 | [-0.0148, -0.0114] | short_term_reversal higher |
| coverage | 0.3526 | 0.0026 | +0.3501 | [+0.3329, +0.3673] | base_l126 higher |
| interval_width | 0.0453 | 0.0000 | +0.0453 | [+0.0404, +0.0512] | base_l126 higher |

### `small_l126` versus `base_l126`

| metric | small_l126 | base_l126 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.0087 | 51.4284 | -0.4197 | [-1.2238, +0.3771] | insufficient evidence |
| MW-DA | 50.5735 | 49.4025 | +1.1711 | [-0.1126, +2.5813] | insufficient evidence |
| RankIC | 0.0208 | 0.0198 | +0.0010 | [-0.0081, +0.0102] | insufficient evidence |
| HitRate@Top10 | 50.8053 | 51.0542 | -0.2489 | [-1.4495, +1.0102] | insufficient evidence |
| CRPS | 0.0258 | 0.0261 | -0.0003 | [-0.0005, -0.0001] | base_l126 higher |
| coverage | 0.3927 | 0.3526 | +0.0401 | [+0.0336, +0.0462] | small_l126 higher |
| interval_width | 0.0510 | 0.0453 | +0.0056 | [+0.0050, +0.0063] | small_l126 higher |

### `small_l126` versus `momentum_126_21`

| metric | small_l126 | momentum_126_21 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.0087 | 50.6338 | +0.3749 | [-1.5075, +2.3629] | insufficient evidence |
| MW-DA | 50.5735 | 50.9754 | -0.4018 | [-3.9587, +3.3342] | insufficient evidence |
| RankIC | 0.0208 | 0.0091 | +0.0117 | [-0.0168, +0.0413] | insufficient evidence |
| HitRate@Top10 | 50.8053 | 50.1464 | +0.6589 | [-1.5231, +2.9286] | insufficient evidence |
| CRPS | 0.0258 | 0.0306 | -0.0048 | [-0.0055, -0.0042] | momentum_126_21 higher |
| coverage | 0.3927 | 0.0004 | +0.3923 | [+0.3716, +0.4133] | small_l126 higher |
| interval_width | 0.0510 | 0.0000 | +0.0510 | [+0.0458, +0.0570] | small_l126 higher |

### `small_l126` versus `persistence`

| metric | small_l126 | persistence | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.0087 | 51.0098 | -0.0011 | [-2.8957, +2.7910] | insufficient evidence |
| MW-DA | 50.5735 | 48.5812 | +1.9923 | [-3.2500, +7.4415] | insufficient evidence |
| RankIC | 0.0208 | 0.0000 | +0.0208 | [+0.0059, +0.0353] | small_l126 higher |
| HitRate@Top10 | 50.8053 | 45.1245 | +5.6808 | [+3.5575, +7.6867] | small_l126 higher |
| CRPS | 0.0258 | 0.0298 | -0.0039 | [-0.0045, -0.0035] | persistence higher |
| coverage | 0.3927 | 0.0329 | +0.3598 | [+0.3406, +0.3792] | small_l126 higher |
| interval_width | 0.0510 | 0.0000 | +0.0510 | [+0.0458, +0.0570] | small_l126 higher |

### `small_l126` versus `recent_return_bootstrap`

| metric | small_l126 | recent_return_bootstrap | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.0087 | 49.4922 | +1.5165 | [-0.3182, +3.2419] | insufficient evidence |
| MW-DA | 50.5735 | 50.3228 | +0.2508 | [-3.0444, +3.3433] | insufficient evidence |
| RankIC | 0.0208 | -0.0079 | +0.0287 | [+0.0072, +0.0497] | small_l126 higher |
| HitRate@Top10 | 50.8053 | 49.6925 | +1.1127 | [-0.8053, +3.0307] | insufficient evidence |
| CRPS | 0.0258 | 0.0242 | +0.0016 | [+0.0013, +0.0021] | small_l126 higher |
| coverage | 0.3927 | 0.6848 | -0.2922 | [-0.3076, -0.2757] | recent_return_bootstrap higher |
| interval_width | 0.0510 | 0.1153 | -0.0643 | [-0.0708, -0.0583] | recent_return_bootstrap higher |

### `small_l126` versus `short_term_reversal`

| metric | small_l126 | short_term_reversal | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.0087 | 50.2867 | +0.7219 | [-0.8446, +2.4998] | insufficient evidence |
| MW-DA | 50.5735 | 47.7662 | +2.8073 | [-0.0835, +5.7880] | insufficient evidence |
| RankIC | 0.0208 | 0.0154 | +0.0054 | [-0.0153, +0.0270] | insufficient evidence |
| HitRate@Top10 | 50.8053 | 49.3558 | +1.4495 | [-0.3514, +3.3239] | insufficient evidence |
| CRPS | 0.0258 | 0.0391 | -0.0133 | [-0.0151, -0.0117] | short_term_reversal higher |
| coverage | 0.3927 | 0.0026 | +0.3901 | [+0.3697, +0.4110] | small_l126 higher |
| interval_width | 0.0510 | 0.0000 | +0.0510 | [+0.0458, +0.0570] | small_l126 higher |

## Design Resolution

| metric | paired 95% CI half-width | smallest resolvable difference |
|---|---:|---|
| DA | 1.6722 | a true difference below 1.6722 cannot be separated from zero here |
| MW-DA | 2.9358 | a true difference below 2.9358 cannot be separated from zero here |
| RankIC | 0.0212 | a true difference below 0.0212 cannot be separated from zero here |
| HitRate@Top10 | 1.8377 | a true difference below 1.8377 cannot be separated from zero here |
| CRPS | 0.0017 | a true difference below 0.0017 cannot be separated from zero here |
| coverage | 0.0206 | a true difference below 0.0206 cannot be separated from zero here |
| interval_width | 0.0056 | a true difference below 0.0056 cannot be separated from zero here |

Read these widths as the resolution of a comparison between two weakly
correlated candidates on 683 paired dates. Paired difference variance falls
as the two candidates make more correlated predictions, so a Kronos-small versus
Kronos-base comparison should resolve smaller differences than this pair, while a
model versus naive comparison behaves closer to it. Fold-level intervals are
roughly twice as wide because each fold holds about a quarter of the dates.

## Reading These Intervals

- Each replicate resamples contiguous blocks of forecast dates and keeps the
  whole cross-section of that date, so overlapping horizons and market-wide
  dependence stay inside the resampled unit.
- Both candidates are evaluated on one shared resampled index, so the interval
  describes the paired difference, not two independent samples.
- Ratio metrics are recomputed from resampled numerator and denominator sums
  inside every replicate; daily ratios are never averaged.
- `verdict` states only the sign of the difference. Higher is better for DA,
  MW-DA, RankIC, and HitRate@Top10; lower is better for CRPS and
  interval_width; coverage is judged against its nominal 0.80 target.
- An interval containing zero means insufficient evidence, never equivalence.

## Guardrails

- Per-fold rows accompany the pooled row so a single regime cannot carry a
  conclusion on its own.
- No multiple-comparison correction is applied yet. Once several model
  candidates enter, SPEC section 8.9 requires a Model Confidence Set or an
  equivalent bootstrap correction before any winner is named.
- The 2026 lockbox remains closed.

## Next Step

M2.4 adds the zero-shot Kronos runner on the same origins and reuses this
inference layer to compare Kronos against these references.
