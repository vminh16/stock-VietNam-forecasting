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

### `small_l126__liquidity_tier_tier_0` versus `base_l126__liquidity_tier_tier_0`

| metric | small_l126__liquidity_tier_tier_0 | base_l126__liquidity_tier_tier_0 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 50.2435 | 50.8411 | -0.5976 | [-2.3694, +1.2549] | insufficient evidence |
| MW-DA | 50.0216 | 49.5055 | +0.5161 | [-2.1244, +3.0663] | insufficient evidence |
| RankIC | 0.0162 | 0.0182 | -0.0020 | [-0.0227, +0.0180] | insufficient evidence |
| HitRate@Top10 | 50.7143 | 49.7959 | +0.9184 | [-0.9184, +2.7041] | insufficient evidence |
| CRPS | 0.0277 | 0.0280 | -0.0003 | [-0.0006, +0.0001] | insufficient evidence |
| coverage | 0.3993 | 0.3587 | +0.0406 | [+0.0298, +0.0515] | small_l126__liquidity_tier_tier_0 higher |
| interval_width | 0.0562 | 0.0503 | +0.0058 | [+0.0050, +0.0067] | small_l126__liquidity_tier_tier_0 higher |

### `small_l126__liquidity_tier_tier_1` versus `base_l126__liquidity_tier_tier_1`

| metric | small_l126__liquidity_tier_tier_1 | base_l126__liquidity_tier_tier_1 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.1742 | 51.1631 | +0.0112 | [-1.7568, +1.5939] | insufficient evidence |
| MW-DA | 50.5576 | 49.9785 | +0.5791 | [-1.8695, +3.2497] | insufficient evidence |
| RankIC | 0.0313 | 0.0361 | -0.0048 | [-0.0321, +0.0234] | insufficient evidence |
| HitRate@Top10 | 52.0408 | 52.8571 | -0.8163 | [-2.5000, +0.8163] | insufficient evidence |
| CRPS | 0.0262 | 0.0264 | -0.0002 | [-0.0005, +0.0001] | insufficient evidence |
| coverage | 0.3996 | 0.3646 | +0.0350 | [+0.0236, +0.0463] | small_l126__liquidity_tier_tier_1 higher |
| interval_width | 0.0515 | 0.0462 | +0.0053 | [+0.0042, +0.0065] | small_l126__liquidity_tier_tier_1 higher |

### `small_l126__liquidity_tier_tier_2` versus `base_l126__liquidity_tier_tier_2`

| metric | small_l126__liquidity_tier_tier_2 | base_l126__liquidity_tier_tier_2 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 52.0189 | 52.3338 | -0.3149 | [-1.8069, +1.2141] | insufficient evidence |
| MW-DA | 52.0158 | 50.4512 | +1.5646 | [-0.5581, +3.9561] | insufficient evidence |
| RankIC | 0.0466 | 0.0440 | +0.0026 | [-0.0192, +0.0241] | insufficient evidence |
| HitRate@Top10 | 49.0816 | 48.8265 | +0.2551 | [-1.6837, +2.1939] | insufficient evidence |
| CRPS | 0.0244 | 0.0247 | -0.0003 | [-0.0005, -0.0000] | base_l126__liquidity_tier_tier_2 higher |
| coverage | 0.3950 | 0.3528 | +0.0422 | [+0.0320, +0.0529] | small_l126__liquidity_tier_tier_2 higher |
| interval_width | 0.0454 | 0.0398 | +0.0056 | [+0.0047, +0.0066] | small_l126__liquidity_tier_tier_2 higher |

### `small_l126__symbol_group_group_0` versus `base_l126__symbol_group_group_0`

| metric | small_l126__symbol_group_group_0 | base_l126__symbol_group_group_0 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.7010 | 51.2075 | +0.4936 | [-1.0689, +2.1438] | insufficient evidence |
| MW-DA | 51.0329 | 49.6383 | +1.3946 | [-1.3282, +4.1790] | insufficient evidence |
| RankIC | 0.0181 | 0.0259 | -0.0078 | [-0.0328, +0.0174] | insufficient evidence |
| HitRate@Top10 | 50.8163 | 49.3367 | +1.4796 | [-0.0510, +2.9592] | insufficient evidence |
| CRPS | 0.0264 | 0.0265 | -0.0001 | [-0.0005, +0.0003] | insufficient evidence |
| coverage | 0.3947 | 0.3534 | +0.0412 | [+0.0245, +0.0575] | small_l126__symbol_group_group_0 higher |
| interval_width | 0.0512 | 0.0461 | +0.0051 | [+0.0041, +0.0062] | small_l126__symbol_group_group_0 higher |

### `small_l126__symbol_group_group_1` versus `base_l126__symbol_group_group_1`

| metric | small_l126__symbol_group_group_1 | base_l126__symbol_group_group_1 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.5822 | 52.1907 | -0.6085 | [-2.0645, +0.9472] | insufficient evidence |
| MW-DA | 51.7274 | 52.2249 | -0.4975 | [-2.7598, +1.7773] | insufficient evidence |
| RankIC | 0.0336 | 0.0396 | -0.0060 | [-0.0359, +0.0230] | insufficient evidence |
| HitRate@Top10 | 49.0816 | 49.3367 | -0.2551 | [-1.7347, +1.3265] | insufficient evidence |
| CRPS | 0.0261 | 0.0262 | -0.0002 | [-0.0004, +0.0001] | insufficient evidence |
| coverage | 0.4043 | 0.3596 | +0.0446 | [+0.0320, +0.0575] | small_l126__symbol_group_group_1 higher |
| interval_width | 0.0525 | 0.0470 | +0.0055 | [+0.0041, +0.0072] | small_l126__symbol_group_group_1 higher |

### `small_l126__symbol_group_group_2` versus `base_l126__symbol_group_group_2`

| metric | small_l126__symbol_group_group_2 | base_l126__symbol_group_group_2 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 50.6401 | 50.7773 | -0.1372 | [-2.1872, +1.9445] | insufficient evidence |
| MW-DA | 50.4391 | 48.3048 | +2.1343 | [-0.1543, +4.5503] | insufficient evidence |
| RankIC | 0.0195 | 0.0402 | -0.0208 | [-0.0515, +0.0099] | insufficient evidence |
| HitRate@Top10 | 49.6429 | 49.5918 | +0.0510 | [-1.8367, +1.7857] | insufficient evidence |
| CRPS | 0.0264 | 0.0267 | -0.0003 | [-0.0006, -0.0000] | base_l126__symbol_group_group_2 higher |
| coverage | 0.3898 | 0.3532 | +0.0366 | [+0.0240, +0.0486] | small_l126__symbol_group_group_2 higher |
| interval_width | 0.0497 | 0.0436 | +0.0061 | [+0.0049, +0.0073] | small_l126__symbol_group_group_2 higher |

### `small_l126__symbol_group_group_3` versus `base_l126__symbol_group_group_3`

| metric | small_l126__symbol_group_group_3 | base_l126__symbol_group_group_3 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 50.7279 | 51.5686 | -0.8407 | [-2.5209, +1.0077] | insufficient evidence |
| MW-DA | 50.1389 | 50.3678 | -0.2288 | [-3.2593, +3.2470] | insufficient evidence |
| RankIC | 0.0281 | 0.0146 | +0.0135 | [-0.0110, +0.0417] | insufficient evidence |
| HitRate@Top10 | 50.5612 | 49.3367 | +1.2245 | [-0.2041, +2.7041] | insufficient evidence |
| CRPS | 0.0282 | 0.0286 | -0.0004 | [-0.0007, +0.0000] | insufficient evidence |
| coverage | 0.3986 | 0.3617 | +0.0369 | [+0.0256, +0.0476] | small_l126__symbol_group_group_3 higher |
| interval_width | 0.0554 | 0.0496 | +0.0058 | [+0.0046, +0.0069] | small_l126__symbol_group_group_3 higher |

### `small_l126__symbol_group_group_4` versus `base_l126__symbol_group_group_4`

| metric | small_l126__symbol_group_group_4 | base_l126__symbol_group_group_4 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 50.9765 | 51.4326 | -0.4562 | [-2.3974, +1.5622] | insufficient evidence |
| MW-DA | 50.7306 | 49.2791 | +1.4515 | [-1.2783, +4.5411] | insufficient evidence |
| RankIC | 0.0303 | 0.0204 | +0.0098 | [-0.0224, +0.0424] | insufficient evidence |
| HitRate@Top10 | 51.0714 | 50.7143 | +0.3571 | [-1.7347, +2.4490] | insufficient evidence |
| CRPS | 0.0243 | 0.0247 | -0.0003 | [-0.0006, -0.0001] | base_l126__symbol_group_group_4 higher |
| coverage | 0.4009 | 0.3636 | +0.0372 | [+0.0257, +0.0487] | small_l126__symbol_group_group_4 higher |
| interval_width | 0.0477 | 0.0422 | +0.0055 | [+0.0045, +0.0067] | small_l126__symbol_group_group_4 higher |

## Design Resolution

| metric | paired 95% CI half-width | smallest resolvable difference |
|---|---:|---|
| DA | 1.8122 | a true difference below 1.8122 cannot be separated from zero here |
| MW-DA | 2.5953 | a true difference below 2.5953 cannot be separated from zero here |
| RankIC | 0.0204 | a true difference below 0.0204 cannot be separated from zero here |
| HitRate@Top10 | 1.8112 | a true difference below 1.8112 cannot be separated from zero here |
| CRPS | 0.0004 | a true difference below 0.0004 cannot be separated from zero here |
| coverage | 0.0108 | a true difference below 0.0108 cannot be separated from zero here |
| interval_width | 0.0009 | a true difference below 0.0009 cannot be separated from zero here |

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
