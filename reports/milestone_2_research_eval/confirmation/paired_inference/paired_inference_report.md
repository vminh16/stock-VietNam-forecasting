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

### `base_l126` versus `persistence`

| metric | base_l126 | persistence | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.4422 | 50.8988 | +0.5434 | [-2.3826, +3.3760] | insufficient evidence |
| MW-DA | 49.9554 | 46.5397 | +3.4157 | [-1.7383, +8.3657] | insufficient evidence |
| RankIC | 0.0300 | 0.0000 | +0.0300 | [+0.0147, +0.0452] | base_l126 higher |
| HitRate@Top10 | 52.7551 | 47.9592 | +4.7959 | [+1.9898, +7.6020] | base_l126 higher |
| CRPS | 0.0264 | 0.0301 | -0.0037 | [-0.0047, -0.0030] | persistence higher |
| coverage | 0.3587 | 0.0335 | +0.3252 | [+0.3005, +0.3536] | base_l126 higher |
| interval_width | 0.0455 | 0.0000 | +0.0455 | [+0.0374, +0.0555] | base_l126 higher |

### `base_l126` versus `recent_return_bootstrap`

| metric | base_l126 | recent_return_bootstrap | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.4422 | 49.6222 | +1.8199 | [-1.3822, +4.7982] | insufficient evidence |
| MW-DA | 49.9554 | 49.0475 | +0.9079 | [-5.4326, +6.3024] | insufficient evidence |
| RankIC | 0.0300 | -0.0176 | +0.0476 | [+0.0104, +0.0831] | base_l126 higher |
| HitRate@Top10 | 52.7551 | 51.1735 | +1.5816 | [-0.8673, +3.9796] | insufficient evidence |
| CRPS | 0.0264 | 0.0247 | +0.0017 | [+0.0012, +0.0022] | base_l126 higher |
| coverage | 0.3587 | 0.6926 | -0.3339 | [-0.3536, -0.3097] | recent_return_bootstrap higher |
| interval_width | 0.0455 | 0.1152 | -0.0697 | [-0.0785, -0.0618] | recent_return_bootstrap higher |

### `small_l126` versus `base_l126`

| metric | small_l126 | base_l126 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.1407 | 51.4422 | -0.3015 | [-1.5700, +1.0517] | insufficient evidence |
| MW-DA | 50.8173 | 49.9554 | +0.8619 | [-1.1373, +3.0939] | insufficient evidence |
| RankIC | 0.0270 | 0.0300 | -0.0030 | [-0.0215, +0.0158] | insufficient evidence |
| HitRate@Top10 | 52.7551 | 52.7551 | +0.0000 | [-1.8878, +2.0918] | insufficient evidence |
| CRPS | 0.0261 | 0.0264 | -0.0003 | [-0.0005, +0.0000] | insufficient evidence |
| coverage | 0.3980 | 0.3587 | +0.0393 | [+0.0310, +0.0470] | small_l126 higher |
| interval_width | 0.0510 | 0.0455 | +0.0056 | [+0.0048, +0.0064] | small_l126 higher |

### `small_l126` versus `persistence`

| metric | small_l126 | persistence | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.1407 | 50.8988 | +0.2419 | [-3.6259, +4.0292] | insufficient evidence |
| MW-DA | 50.8173 | 46.5397 | +4.2775 | [-2.0880, +10.4857] | insufficient evidence |
| RankIC | 0.0270 | 0.0000 | +0.0270 | [+0.0120, +0.0429] | small_l126 higher |
| HitRate@Top10 | 52.7551 | 47.9592 | +4.7959 | [+2.5000, +7.0408] | small_l126 higher |
| CRPS | 0.0261 | 0.0301 | -0.0040 | [-0.0047, -0.0034] | persistence higher |
| coverage | 0.3980 | 0.0335 | +0.3644 | [+0.3397, +0.3926] | small_l126 higher |
| interval_width | 0.0510 | 0.0000 | +0.0510 | [+0.0426, +0.0614] | small_l126 higher |

### `small_l126` versus `recent_return_bootstrap`

| metric | small_l126 | recent_return_bootstrap | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.1407 | 49.6222 | +1.5185 | [-0.7420, +3.7111] | insufficient evidence |
| MW-DA | 50.8173 | 49.0475 | +1.7698 | [-2.9008, +5.9765] | insufficient evidence |
| RankIC | 0.0270 | -0.0176 | +0.0446 | [+0.0134, +0.0741] | small_l126 higher |
| HitRate@Top10 | 52.7551 | 51.1735 | +1.5816 | [-1.4796, +4.6429] | insufficient evidence |
| CRPS | 0.0261 | 0.0247 | +0.0015 | [+0.0011, +0.0018] | small_l126 higher |
| coverage | 0.3980 | 0.6926 | -0.2947 | [-0.3115, -0.2749] | recent_return_bootstrap higher |
| interval_width | 0.0510 | 0.1152 | -0.0641 | [-0.0725, -0.0566] | recent_return_bootstrap higher |

## Design Resolution

| metric | paired 95% CI half-width | smallest resolvable difference |
|---|---:|---|
| DA | 1.3109 | a true difference below 1.3109 cannot be separated from zero here |
| MW-DA | 2.1156 | a true difference below 2.1156 cannot be separated from zero here |
| RankIC | 0.0186 | a true difference below 0.0186 cannot be separated from zero here |
| HitRate@Top10 | 1.9898 | a true difference below 1.9898 cannot be separated from zero here |
| CRPS | 0.0003 | a true difference below 0.0003 cannot be separated from zero here |
| coverage | 0.0080 | a true difference below 0.0080 cannot be separated from zero here |
| interval_width | 0.0008 | a true difference below 0.0008 cannot be separated from zero here |

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
