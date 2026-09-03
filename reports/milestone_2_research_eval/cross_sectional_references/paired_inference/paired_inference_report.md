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
- Paired dates (pooled): 196
- Metrics: DA, MW-DA, RankIC, HitRate@Top10, CRPS, coverage, interval_width

### `base_l126` versus `momentum_126_21`

| metric | base_l126 | momentum_126_21 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.4422 | 50.7127 | +0.7295 | [-2.3772, +3.6649] | insufficient evidence |
| MW-DA | 49.9554 | 49.5869 | +0.3685 | [-5.2086, +5.5446] | insufficient evidence |
| RankIC | 0.0300 | 0.0004 | +0.0296 | [-0.0068, +0.0667] | insufficient evidence |
| HitRate@Top10 | 52.7551 | 51.4796 | +1.2755 | [-1.2755, +3.8265] | insufficient evidence |
| CRPS | 0.0264 | 0.0311 | -0.0048 | [-0.0061, -0.0037] | momentum_126_21 higher |
| coverage | 0.3587 | 0.0001 | +0.3586 | [+0.3341, +0.3866] | base_l126 higher |
| interval_width | 0.0455 | 0.0000 | +0.0455 | [+0.0374, +0.0555] | base_l126 higher |

### `base_l126` versus `short_term_reversal`

| metric | base_l126 | short_term_reversal | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.4422 | 49.7637 | +1.6785 | [-0.4332, +3.9168] | insufficient evidence |
| MW-DA | 49.9554 | 47.9655 | +1.9899 | [-1.1956, +5.1068] | insufficient evidence |
| RankIC | 0.0300 | 0.0210 | +0.0090 | [-0.0184, +0.0378] | insufficient evidence |
| HitRate@Top10 | 52.7551 | 50.8163 | +1.9388 | [-0.9184, +4.5918] | insufficient evidence |
| CRPS | 0.0264 | 0.0392 | -0.0129 | [-0.0152, -0.0110] | short_term_reversal higher |
| coverage | 0.3587 | 0.0027 | +0.3560 | [+0.3315, +0.3840] | base_l126 higher |
| interval_width | 0.0455 | 0.0000 | +0.0455 | [+0.0374, +0.0555] | base_l126 higher |

### `small_l126` versus `momentum_126_21`

| metric | small_l126 | momentum_126_21 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.1407 | 50.7127 | +0.4280 | [-2.0733, +2.8910] | insufficient evidence |
| MW-DA | 50.8173 | 49.5869 | +1.2304 | [-3.0810, +5.4520] | insufficient evidence |
| RankIC | 0.0270 | 0.0004 | +0.0266 | [-0.0057, +0.0591] | insufficient evidence |
| HitRate@Top10 | 52.7551 | 51.4796 | +1.2755 | [-1.3776, +3.9286] | insufficient evidence |
| CRPS | 0.0261 | 0.0311 | -0.0050 | [-0.0061, -0.0041] | momentum_126_21 higher |
| coverage | 0.3980 | 0.0001 | +0.3979 | [+0.3725, +0.4265] | small_l126 higher |
| interval_width | 0.0510 | 0.0000 | +0.0510 | [+0.0426, +0.0614] | small_l126 higher |

### `small_l126` versus `short_term_reversal`

| metric | small_l126 | short_term_reversal | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.1407 | 49.7637 | +1.3771 | [-0.3877, +3.2024] | insufficient evidence |
| MW-DA | 50.8173 | 47.9655 | +2.8518 | [+0.1202, +5.6249] | small_l126 higher |
| RankIC | 0.0270 | 0.0210 | +0.0060 | [-0.0234, +0.0356] | insufficient evidence |
| HitRate@Top10 | 52.7551 | 50.8163 | +1.9388 | [-1.5306, +5.4082] | insufficient evidence |
| CRPS | 0.0261 | 0.0392 | -0.0131 | [-0.0153, -0.0113] | short_term_reversal higher |
| coverage | 0.3980 | 0.0027 | +0.3953 | [+0.3703, +0.4239] | small_l126 higher |
| interval_width | 0.0510 | 0.0000 | +0.0510 | [+0.0426, +0.0614] | small_l126 higher |

## Design Resolution

| metric | paired 95% CI half-width | smallest resolvable difference |
|---|---:|---|
| DA | 1.7951 | a true difference below 1.7951 cannot be separated from zero here |
| MW-DA | 2.7523 | a true difference below 2.7523 cannot be separated from zero here |
| RankIC | 0.0295 | a true difference below 0.0295 cannot be separated from zero here |
| HitRate@Top10 | 3.4694 | a true difference below 3.4694 cannot be separated from zero here |
| CRPS | 0.0020 | a true difference below 0.0020 cannot be separated from zero here |
| coverage | 0.0268 | a true difference below 0.0268 cannot be separated from zero here |
| interval_width | 0.0094 | a true difference below 0.0094 cannot be separated from zero here |

Read these widths as the resolution of a comparison between two weakly
correlated candidates on 196 paired dates. Paired difference variance falls
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
