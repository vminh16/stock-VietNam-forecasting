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
- Paired dates (pooled): 98
- Metrics: DA, MW-DA, RankIC, HitRate@Top10, CRPS, coverage, interval_width

### `base_l126` versus `persistence`

| metric | base_l126 | persistence | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.8725 | 49.8920 | +1.9805 | [-1.2254, +5.2592] | insufficient evidence |
| MW-DA | 49.1754 | 47.2578 | +1.9176 | [-4.3414, +9.3839] | insufficient evidence |
| RankIC | 0.0267 | 0.0000 | +0.0267 | [+0.0081, +0.0460] | base_l126 higher |
| HitRate@Top10 | 54.7959 | 46.6327 | +8.1633 | [+5.9184, +10.3061] | base_l126 higher |
| CRPS | 0.0258 | 0.0294 | -0.0035 | [-0.0046, -0.0027] | persistence higher |
| coverage | 0.3563 | 0.0342 | +0.3221 | [+0.2972, +0.3485] | base_l126 higher |
| interval_width | 0.0459 | 0.0000 | +0.0459 | [+0.0358, +0.0572] | base_l126 higher |

### `base_l126` versus `recent_return_bootstrap`

| metric | base_l126 | recent_return_bootstrap | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.8725 | 49.5793 | +2.2932 | [-0.7446, +5.4964] | insufficient evidence |
| MW-DA | 49.1754 | 50.6958 | -1.5204 | [-7.1052, +3.6219] | insufficient evidence |
| RankIC | 0.0267 | 0.0050 | +0.0217 | [-0.0238, +0.0705] | insufficient evidence |
| HitRate@Top10 | 54.7959 | 52.7551 | +2.0408 | [-1.5306, +6.1224] | insufficient evidence |
| CRPS | 0.0258 | 0.0239 | +0.0020 | [+0.0015, +0.0024] | base_l126 higher |
| coverage | 0.3563 | 0.6889 | -0.3325 | [-0.3575, -0.3015] | recent_return_bootstrap higher |
| interval_width | 0.0459 | 0.1155 | -0.0696 | [-0.0795, -0.0606] | recent_return_bootstrap higher |

### `base_l63` versus `base_l126`

| metric | base_l63 | base_l126 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.0833 | 51.8725 | -0.7892 | [-2.0695, +0.4041] | insufficient evidence |
| MW-DA | 48.4624 | 49.1754 | -0.7130 | [-2.7753, +1.3883] | insufficient evidence |
| RankIC | 0.0149 | 0.0267 | -0.0118 | [-0.0382, +0.0150] | insufficient evidence |
| HitRate@Top10 | 54.6939 | 54.7959 | -0.1020 | [-3.0612, +2.7551] | insufficient evidence |
| CRPS | 0.0256 | 0.0258 | -0.0002 | [-0.0006, +0.0001] | insufficient evidence |
| coverage | 0.3313 | 0.3563 | -0.0250 | [-0.0374, -0.0125] | base_l126 higher |
| interval_width | 0.0419 | 0.0459 | -0.0040 | [-0.0063, -0.0020] | base_l126 higher |

### `small_l126` versus `base_l126`

| metric | small_l126 | base_l126 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 50.6813 | 51.8725 | -1.1913 | [-2.8623, +0.4326] | insufficient evidence |
| MW-DA | 50.0655 | 49.1754 | +0.8902 | [-1.3777, +3.2740] | insufficient evidence |
| RankIC | 0.0247 | 0.0267 | -0.0020 | [-0.0184, +0.0129] | insufficient evidence |
| HitRate@Top10 | 53.9796 | 54.7959 | -0.8163 | [-2.7551, +1.2245] | insufficient evidence |
| CRPS | 0.0255 | 0.0258 | -0.0003 | [-0.0006, +0.0000] | insufficient evidence |
| coverage | 0.4003 | 0.3563 | +0.0439 | [+0.0294, +0.0587] | small_l126 higher |
| interval_width | 0.0513 | 0.0459 | +0.0054 | [+0.0046, +0.0062] | small_l126 higher |

### `small_l63` versus `base_l63`

| metric | small_l63 | base_l63 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 49.8920 | 51.0833 | -1.1913 | [-2.6920, +0.3070] | insufficient evidence |
| MW-DA | 48.2319 | 48.4624 | -0.2304 | [-1.9717, +1.7813] | insufficient evidence |
| RankIC | 0.0013 | 0.0149 | -0.0136 | [-0.0285, +0.0005] | insufficient evidence |
| HitRate@Top10 | 53.2653 | 54.6939 | -1.4286 | [-4.7959, +1.9388] | insufficient evidence |
| CRPS | 0.0253 | 0.0256 | -0.0003 | [-0.0006, +0.0000] | insufficient evidence |
| coverage | 0.3677 | 0.3313 | +0.0363 | [+0.0278, +0.0445] | small_l63 higher |
| interval_width | 0.0470 | 0.0419 | +0.0051 | [+0.0041, +0.0064] | small_l63 higher |

### `small_l63` versus `recent_return_bootstrap`

| metric | small_l63 | recent_return_bootstrap | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 49.8920 | 49.5793 | +0.3127 | [-1.6232, +2.2385] | insufficient evidence |
| MW-DA | 48.2319 | 50.6958 | -2.4639 | [-6.3876, +0.9890] | insufficient evidence |
| RankIC | 0.0013 | 0.0050 | -0.0037 | [-0.0437, +0.0332] | insufficient evidence |
| HitRate@Top10 | 53.2653 | 52.7551 | +0.5102 | [-3.7755, +4.7959] | insufficient evidence |
| CRPS | 0.0253 | 0.0239 | +0.0015 | [+0.0011, +0.0019] | small_l63 higher |
| coverage | 0.3677 | 0.6889 | -0.3212 | [-0.3432, -0.2967] | recent_return_bootstrap higher |
| interval_width | 0.0470 | 0.1155 | -0.0685 | [-0.0785, -0.0592] | recent_return_bootstrap higher |

### `small_l63` versus `small_l126`

| metric | small_l63 | small_l126 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 49.8920 | 50.6813 | -0.7892 | [-2.0642, +0.5637] | insufficient evidence |
| MW-DA | 48.2319 | 50.0655 | -1.8336 | [-3.3719, -0.2252] | small_l126 higher |
| RankIC | 0.0013 | 0.0247 | -0.0235 | [-0.0461, -0.0016] | small_l126 higher |
| HitRate@Top10 | 53.2653 | 53.9796 | -0.7143 | [-3.2653, +2.1429] | insufficient evidence |
| CRPS | 0.0253 | 0.0255 | -0.0002 | [-0.0005, +0.0000] | insufficient evidence |
| coverage | 0.3677 | 0.4003 | -0.0326 | [-0.0465, -0.0193] | small_l126 higher |
| interval_width | 0.0470 | 0.0513 | -0.0043 | [-0.0069, -0.0023] | small_l126 higher |

### `small_l63` versus `small_l63_norm126`

| metric | small_l63 | small_l63_norm126 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 49.8920 | 50.6887 | -0.7967 | [-1.8942, +0.4079] | insufficient evidence |
| MW-DA | 48.2319 | 49.5272 | -1.2953 | [-2.7305, +0.3315] | insufficient evidence |
| RankIC | 0.0013 | 0.0224 | -0.0211 | [-0.0437, +0.0001] | insufficient evidence |
| HitRate@Top10 | 53.2653 | 53.9796 | -0.7143 | [-5.0000, +3.7755] | insufficient evidence |
| CRPS | 0.0253 | 0.0255 | -0.0002 | [-0.0004, +0.0001] | insufficient evidence |
| coverage | 0.3677 | 0.3829 | -0.0153 | [-0.0236, -0.0073] | small_l63_norm126 higher |
| interval_width | 0.0470 | 0.0493 | -0.0023 | [-0.0034, -0.0013] | small_l63_norm126 higher |

### `small_l63_norm126` versus `small_l126`

| metric | small_l63_norm126 | small_l126 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 50.6887 | 50.6813 | +0.0074 | [-0.7123, +0.6925] | insufficient evidence |
| MW-DA | 49.5272 | 50.0655 | -0.5383 | [-1.5542, +0.3788] | insufficient evidence |
| RankIC | 0.0224 | 0.0247 | -0.0023 | [-0.0143, +0.0099] | insufficient evidence |
| HitRate@Top10 | 53.9796 | 53.9796 | +0.0000 | [-3.5714, +3.6735] | insufficient evidence |
| CRPS | 0.0255 | 0.0255 | -0.0001 | [-0.0002, +0.0001] | insufficient evidence |
| coverage | 0.3829 | 0.4003 | -0.0173 | [-0.0266, -0.0074] | small_l126 higher |
| interval_width | 0.0493 | 0.0513 | -0.0020 | [-0.0037, -0.0006] | small_l126 higher |

## Design Resolution

| metric | paired 95% CI half-width | smallest resolvable difference |
|---|---:|---|
| DA | 1.1511 | a true difference below 1.1511 cannot be separated from zero here |
| MW-DA | 1.5310 | a true difference below 1.5310 cannot be separated from zero here |
| RankIC | 0.0219 | a true difference below 0.0219 cannot be separated from zero here |
| HitRate@Top10 | 4.3878 | a true difference below 4.3878 cannot be separated from zero here |
| CRPS | 0.0002 | a true difference below 0.0002 cannot be separated from zero here |
| coverage | 0.0081 | a true difference below 0.0081 cannot be separated from zero here |
| interval_width | 0.0010 | a true difference below 0.0010 cannot be separated from zero here |

Read these widths as the resolution of a comparison between two weakly
correlated candidates on 98 paired dates. Paired difference variance falls
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
