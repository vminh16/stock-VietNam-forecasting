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
- Paired dates (pooled): 977
- Metrics: DA, MW-DA, RankIC, HitRate@Top10, CRPS, coverage, interval_width

### `recent_return_bootstrap` versus `persistence`

| metric | recent_return_bootstrap | persistence | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 49.5270 | 50.8754 | -1.3484 | [-5.1175, +2.4581] | insufficient evidence |
| MW-DA | 50.1075 | 48.0411 | +2.0664 | [-4.4339, +8.9480] | insufficient evidence |
| RankIC | -0.0086 | 0.0000 | -0.0086 | [-0.0294, +0.0114] | insufficient evidence |
| HitRate@Top10 | 50.2968 | 45.8444 | +4.4524 | [+2.1082, +6.8373] | recent_return_bootstrap higher |
| CRPS | 0.0242 | 0.0298 | -0.0056 | [-0.0063, -0.0049] | persistence higher |
| coverage | 0.6868 | 0.0332 | +0.6536 | [+0.6256, +0.6800] | recent_return_bootstrap higher |
| interval_width | 0.1153 | 0.0000 | +0.1153 | [+0.1064, +0.1252] | recent_return_bootstrap higher |

## Design Resolution

| metric | paired 95% CI half-width | smallest resolvable difference |
|---|---:|---|
| DA | 3.7878 | a true difference below 3.7878 cannot be separated from zero here |
| MW-DA | 6.6910 | a true difference below 6.6910 cannot be separated from zero here |
| RankIC | 0.0204 | a true difference below 0.0204 cannot be separated from zero here |
| HitRate@Top10 | 2.3645 | a true difference below 2.3645 cannot be separated from zero here |
| CRPS | 0.0007 | a true difference below 0.0007 cannot be separated from zero here |
| coverage | 0.0272 | a true difference below 0.0272 cannot be separated from zero here |
| interval_width | 0.0094 | a true difference below 0.0094 cannot be separated from zero here |

Read these widths as the resolution of a comparison between two weakly
correlated candidates on 977 paired dates. Paired difference variance falls
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
  candidates enter, SPEC section 8.6 requires a Model Confidence Set or an
  equivalent bootstrap correction before any winner is named.
- The 2026 lockbox remains closed.

## Next Step

M2.4 adds the zero-shot Kronos runner on the same origins and reuses this
inference layer to compare Kronos against these references.
