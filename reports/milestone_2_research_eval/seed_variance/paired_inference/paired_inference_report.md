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

### `small_l126_r1` versus `small_l126_r2`

| metric | small_l126_r1 | small_l126_r2 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.1519 | 51.3343 | -0.1824 | [-0.7776, +0.4218] | insufficient evidence |
| MW-DA | 50.4745 | 50.6031 | -0.1286 | [-0.7888, +0.6034] | insufficient evidence |
| RankIC | 0.0267 | 0.0253 | +0.0014 | [-0.0082, +0.0114] | insufficient evidence |
| HitRate@Top10 | 52.6531 | 52.1939 | +0.4592 | [-1.3776, +2.2959] | insufficient evidence |
| CRPS | 0.0261 | 0.0261 | +0.0000 | [-0.0001, +0.0001] | insufficient evidence |
| coverage | 0.4045 | 0.4025 | +0.0020 | [-0.0023, +0.0063] | insufficient evidence |
| interval_width | 0.0514 | 0.0511 | +0.0003 | [+0.0001, +0.0005] | small_l126_r1 higher |

### `small_l126_r1` versus `small_l126_r3`

| metric | small_l126_r1 | small_l126_r3 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.1519 | 50.8541 | +0.2977 | [-0.3938, +0.9599] | insufficient evidence |
| MW-DA | 50.4745 | 51.1580 | -0.6835 | [-1.7146, +0.4136] | insufficient evidence |
| RankIC | 0.0267 | 0.0255 | +0.0012 | [-0.0081, +0.0109] | insufficient evidence |
| HitRate@Top10 | 52.6531 | 51.9898 | +0.6633 | [-0.6122, +1.9898] | insufficient evidence |
| CRPS | 0.0261 | 0.0261 | -0.0000 | [-0.0001, +0.0001] | insufficient evidence |
| coverage | 0.4045 | 0.3954 | +0.0090 | [+0.0037, +0.0139] | small_l126_r1 higher |
| interval_width | 0.0514 | 0.0509 | +0.0005 | [+0.0001, +0.0008] | small_l126_r1 higher |

### `small_l126_r1` versus `small_l126_r4`

| metric | small_l126_r1 | small_l126_r4 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.1519 | 50.7797 | +0.3722 | [-0.4032, +1.1325] | insufficient evidence |
| MW-DA | 50.4745 | 50.5523 | -0.0778 | [-0.9369, +0.8310] | insufficient evidence |
| RankIC | 0.0267 | 0.0218 | +0.0049 | [-0.0060, +0.0166] | insufficient evidence |
| HitRate@Top10 | 52.6531 | 51.7857 | +0.8673 | [-0.6633, +2.4490] | insufficient evidence |
| CRPS | 0.0261 | 0.0261 | -0.0000 | [-0.0001, +0.0001] | insufficient evidence |
| coverage | 0.4045 | 0.4009 | +0.0036 | [-0.0023, +0.0091] | insufficient evidence |
| interval_width | 0.0514 | 0.0513 | +0.0001 | [-0.0001, +0.0004] | insufficient evidence |

### `small_l126_r1` versus `small_l126_r5`

| metric | small_l126_r1 | small_l126_r5 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.1519 | 51.3305 | -0.1786 | [-0.9679, +0.5577] | insufficient evidence |
| MW-DA | 50.4745 | 50.8970 | -0.4225 | [-1.4335, +0.6588] | insufficient evidence |
| RankIC | 0.0267 | 0.0253 | +0.0014 | [-0.0090, +0.0121] | insufficient evidence |
| HitRate@Top10 | 52.6531 | 52.6020 | +0.0510 | [-1.2755, +1.4286] | insufficient evidence |
| CRPS | 0.0261 | 0.0261 | +0.0000 | [-0.0000, +0.0001] | insufficient evidence |
| coverage | 0.4045 | 0.4021 | +0.0023 | [-0.0027, +0.0070] | insufficient evidence |
| interval_width | 0.0514 | 0.0512 | +0.0002 | [-0.0001, +0.0004] | insufficient evidence |

### `small_l126_r2` versus `small_l126_r3`

| metric | small_l126_r2 | small_l126_r3 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.3343 | 50.8541 | +0.4801 | [-0.0374, +1.0025] | insufficient evidence |
| MW-DA | 50.6031 | 51.1580 | -0.5550 | [-1.4718, +0.3260] | insufficient evidence |
| RankIC | 0.0253 | 0.0255 | -0.0002 | [-0.0102, +0.0095] | insufficient evidence |
| HitRate@Top10 | 52.1939 | 51.9898 | +0.2041 | [-1.4796, +1.9898] | insufficient evidence |
| CRPS | 0.0261 | 0.0261 | -0.0000 | [-0.0001, +0.0001] | insufficient evidence |
| coverage | 0.4025 | 0.3954 | +0.0070 | [+0.0017, +0.0121] | small_l126_r2 higher |
| interval_width | 0.0511 | 0.0509 | +0.0002 | [-0.0001, +0.0006] | insufficient evidence |

### `small_l126_r2` versus `small_l126_r4`

| metric | small_l126_r2 | small_l126_r4 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.3343 | 50.7797 | +0.5545 | [-0.0223, +1.1815] | insufficient evidence |
| MW-DA | 50.6031 | 50.5523 | +0.0508 | [-0.6429, +0.7844] | insufficient evidence |
| RankIC | 0.0253 | 0.0218 | +0.0035 | [-0.0073, +0.0167] | insufficient evidence |
| HitRate@Top10 | 52.1939 | 51.7857 | +0.4082 | [-1.7360, +2.7551] | insufficient evidence |
| CRPS | 0.0261 | 0.0261 | -0.0000 | [-0.0001, +0.0001] | insufficient evidence |
| coverage | 0.4025 | 0.4009 | +0.0016 | [-0.0030, +0.0065] | insufficient evidence |
| interval_width | 0.0511 | 0.0513 | -0.0001 | [-0.0004, +0.0001] | insufficient evidence |

### `small_l126_r2` versus `small_l126_r5`

| metric | small_l126_r2 | small_l126_r5 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 51.3343 | 51.3305 | +0.0037 | [-0.4800, +0.4839] | insufficient evidence |
| MW-DA | 50.6031 | 50.8970 | -0.2939 | [-1.0084, +0.4496] | insufficient evidence |
| RankIC | 0.0253 | 0.0253 | -0.0000 | [-0.0113, +0.0121] | insufficient evidence |
| HitRate@Top10 | 52.1939 | 52.6020 | -0.4082 | [-2.0408, +1.3776] | insufficient evidence |
| CRPS | 0.0261 | 0.0261 | +0.0000 | [-0.0001, +0.0001] | insufficient evidence |
| coverage | 0.4025 | 0.4021 | +0.0003 | [-0.0044, +0.0051] | insufficient evidence |
| interval_width | 0.0511 | 0.0512 | -0.0001 | [-0.0004, +0.0001] | insufficient evidence |

### `small_l126_r3` versus `small_l126_r4`

| metric | small_l126_r3 | small_l126_r4 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 50.8541 | 50.7797 | +0.0744 | [-0.4247, +0.6030] | insufficient evidence |
| MW-DA | 51.1580 | 50.5523 | +0.6057 | [-0.2970, +1.4742] | insufficient evidence |
| RankIC | 0.0255 | 0.0218 | +0.0037 | [-0.0071, +0.0148] | insufficient evidence |
| HitRate@Top10 | 51.9898 | 51.7857 | +0.2041 | [-1.2245, +1.6837] | insufficient evidence |
| CRPS | 0.0261 | 0.0261 | -0.0000 | [-0.0001, +0.0001] | insufficient evidence |
| coverage | 0.3954 | 0.4009 | -0.0054 | [-0.0119, +0.0018] | insufficient evidence |
| interval_width | 0.0509 | 0.0513 | -0.0003 | [-0.0007, +0.0000] | insufficient evidence |

### `small_l126_r3` versus `small_l126_r5`

| metric | small_l126_r3 | small_l126_r5 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 50.8541 | 51.3305 | -0.4764 | [-0.9384, -0.0224] | small_l126_r5 higher |
| MW-DA | 51.1580 | 50.8970 | +0.2610 | [-0.7468, +1.2159] | insufficient evidence |
| RankIC | 0.0255 | 0.0253 | +0.0002 | [-0.0080, +0.0086] | insufficient evidence |
| HitRate@Top10 | 51.9898 | 52.6020 | -0.6122 | [-2.0918, +0.8673] | insufficient evidence |
| CRPS | 0.0261 | 0.0261 | +0.0000 | [-0.0000, +0.0001] | insufficient evidence |
| coverage | 0.3954 | 0.4021 | -0.0067 | [-0.0122, -0.0008] | small_l126_r5 higher |
| interval_width | 0.0509 | 0.0512 | -0.0003 | [-0.0006, +0.0000] | insufficient evidence |

### `small_l126_r4` versus `small_l126_r5`

| metric | small_l126_r4 | small_l126_r5 | difference | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| DA | 50.7797 | 51.3305 | -0.5508 | [-1.0658, -0.0446] | small_l126_r5 higher |
| MW-DA | 50.5523 | 50.8970 | -0.3447 | [-0.9726, +0.2832] | insufficient evidence |
| RankIC | 0.0218 | 0.0253 | -0.0035 | [-0.0112, +0.0038] | insufficient evidence |
| HitRate@Top10 | 51.7857 | 52.6020 | -0.8163 | [-2.5000, +0.9184] | insufficient evidence |
| CRPS | 0.0261 | 0.0261 | +0.0000 | [-0.0000, +0.0001] | insufficient evidence |
| coverage | 0.4009 | 0.4021 | -0.0013 | [-0.0049, +0.0026] | insufficient evidence |
| interval_width | 0.0513 | 0.0512 | +0.0000 | [-0.0002, +0.0002] | insufficient evidence |

## Design Resolution

| metric | paired 95% CI half-width | smallest resolvable difference |
|---|---:|---|
| DA | 0.5997 | a true difference below 0.5997 cannot be separated from zero here |
| MW-DA | 0.6961 | a true difference below 0.6961 cannot be separated from zero here |
| RankIC | 0.0098 | a true difference below 0.0098 cannot be separated from zero here |
| HitRate@Top10 | 1.8367 | a true difference below 1.8367 cannot be separated from zero here |
| CRPS | 0.0001 | a true difference below 0.0001 cannot be separated from zero here |
| coverage | 0.0043 | a true difference below 0.0043 cannot be separated from zero here |
| interval_width | 0.0002 | a true difference below 0.0002 cannot be separated from zero here |

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
