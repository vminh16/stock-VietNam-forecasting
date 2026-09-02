# M2.6 Metric Slice Report

## Decision

This unit recomputes the locked metrics inside pre-registered slices of the
frozen origins. It runs no model: every number comes from per-origin metric
files a previous unit already wrote. It names no winner; paired date-block
intervals over these slice files carry any comparison.

## Registered Setup

- Slice table SHA256: `8e474264cfc8b16af3dd2b053d9e965cdee2608f625f46556c57cc6aa83bd61b`
- Candidates: `small_l126`, `base_l126`, `recent_return_bootstrap`, `persistence`
- Slice keys: `liquidity_tier`, `symbol_group`
- Minimum cross-section per date inside a slice: 10
- Dates dropped for a thin cross-section, summed over slices: 0

## Pooled Metrics By Slice

| candidate | slice | DA | MW-DA | RankIC | HitRate@Top10 | CRPS | coverage | dates | origins |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `small_l126` | `liquidity_tier=tier_0` | 50.2435 | 50.0216 | 0.0162 | 50.7143 | 0.027716 | 0.3993 | 196 | 9,036 |
| `small_l126` | `liquidity_tier=tier_1` | 51.1742 | 50.5576 | 0.0313 | 52.0408 | 0.026228 | 0.3996 | 196 | 8,942 |
| `small_l126` | `liquidity_tier=tier_2` | 52.0189 | 52.0158 | 0.0466 | 49.0816 | 0.024402 | 0.3950 | 196 | 8,891 |
| `small_l126` | `symbol_group=group_0` | 51.7010 | 51.0329 | 0.0181 | 50.8163 | 0.026397 | 0.3947 | 196 | 5,673 |
| `small_l126` | `symbol_group=group_1` | 51.5822 | 51.7274 | 0.0336 | 49.0816 | 0.026087 | 0.4043 | 196 | 4,930 |
| `small_l126` | `symbol_group=group_2` | 50.6401 | 50.4391 | 0.0195 | 49.6429 | 0.026361 | 0.3898 | 196 | 4,374 |
| `small_l126` | `symbol_group=group_3` | 50.7279 | 50.1389 | 0.0281 | 50.5612 | 0.028216 | 0.3986 | 196 | 4,877 |
| `small_l126` | `symbol_group=group_4` | 50.9765 | 50.7306 | 0.0303 | 51.0714 | 0.024328 | 0.4009 | 196 | 7,015 |
| `base_l126` | `liquidity_tier=tier_0` | 50.8411 | 49.5055 | 0.0182 | 49.7959 | 0.027999 | 0.3587 | 196 | 9,036 |
| `base_l126` | `liquidity_tier=tier_1` | 51.1631 | 49.9785 | 0.0361 | 52.8571 | 0.026444 | 0.3646 | 196 | 8,942 |
| `base_l126` | `liquidity_tier=tier_2` | 52.3338 | 50.4512 | 0.0440 | 48.8265 | 0.024669 | 0.3528 | 196 | 8,891 |
| `base_l126` | `symbol_group=group_0` | 51.2075 | 49.6383 | 0.0259 | 49.3367 | 0.026527 | 0.3534 | 196 | 5,673 |
| `base_l126` | `symbol_group=group_1` | 52.1907 | 52.2249 | 0.0396 | 49.3367 | 0.026237 | 0.3596 | 196 | 4,930 |
| `base_l126` | `symbol_group=group_2` | 50.7773 | 48.3048 | 0.0402 | 49.5918 | 0.026655 | 0.3532 | 196 | 4,374 |
| `base_l126` | `symbol_group=group_3` | 51.5686 | 50.3678 | 0.0146 | 49.3367 | 0.028578 | 0.3617 | 196 | 4,877 |
| `base_l126` | `symbol_group=group_4` | 51.4326 | 49.2791 | 0.0204 | 50.7143 | 0.024660 | 0.3636 | 196 | 7,015 |
| `recent_return_bootstrap` | `liquidity_tier=tier_0` | 49.3739 | 49.9419 | -0.0075 | 49.8874 | 0.025554 | 0.6926 | 977 | 45,042 |
| `recent_return_bootstrap` | `liquidity_tier=tier_1` | 49.6893 | 50.0665 | -0.0028 | 50.7369 | 0.024267 | 0.6891 | 977 | 44,571 |
| `recent_return_bootstrap` | `liquidity_tier=tier_2` | 49.5194 | 50.3415 | -0.0105 | 47.9734 | 0.022871 | 0.6787 | 977 | 44,324 |
| `recent_return_bootstrap` | `symbol_group=group_0` | 49.4378 | 50.2895 | -0.0048 | 49.9591 | 0.024673 | 0.6843 | 977 | 28,284 |
| `recent_return_bootstrap` | `symbol_group=group_1` | 49.0580 | 49.1791 | -0.0175 | 48.8639 | 0.024413 | 0.6877 | 977 | 24,575 |
| `recent_return_bootstrap` | `symbol_group=group_2` | 50.3646 | 50.8222 | -0.0096 | 49.4166 | 0.023971 | 0.6837 | 977 | 21,805 |
| `recent_return_bootstrap` | `symbol_group=group_3` | 49.3027 | 49.7010 | -0.0075 | 48.6387 | 0.026029 | 0.6877 | 977 | 24,307 |
| `recent_return_bootstrap` | `symbol_group=group_4` | 49.5624 | 50.5025 | -0.0082 | 50.0102 | 0.022685 | 0.6894 | 977 | 34,966 |
| `persistence` | `liquidity_tier=tier_0` | 50.1199 | 49.4605 | 0.0000 | 49.8772 | 0.031599 | 0.0231 | 977 | 45,042 |
| `persistence` | `liquidity_tier=tier_1` | 49.6511 | 47.4451 | 0.0000 | 49.5906 | 0.029988 | 0.0242 | 977 | 44,571 |
| `persistence` | `liquidity_tier=tier_2` | 52.8743 | 47.0561 | 0.0000 | 45.8956 | 0.027769 | 0.0525 | 977 | 44,324 |
| `persistence` | `symbol_group=group_0` | 50.4985 | 47.8999 | 0.0000 | 50.4094 | 0.030281 | 0.0281 | 977 | 28,284 |
| `persistence` | `symbol_group=group_1` | 50.7223 | 49.0400 | 0.0000 | 47.6868 | 0.030067 | 0.0332 | 977 | 24,575 |
| `persistence` | `symbol_group=group_2` | 51.0204 | 47.2660 | 0.0000 | 49.0686 | 0.029431 | 0.0340 | 977 | 21,805 |
| `persistence` | `symbol_group=group_3` | 51.3350 | 49.0041 | 0.0000 | 48.4340 | 0.031929 | 0.0287 | 977 | 24,307 |
| `persistence` | `symbol_group=group_4` | 50.8780 | 47.1521 | 0.0000 | 49.0379 | 0.027955 | 0.0399 | 977 | 34,966 |

## Reading These Slices

- `RankIC` inside a slice is the cross-sectional correlation among that slice's
  symbols only. A model can rank the liquid tier well and the illiquid tier
  badly while its whole-market `RankIC` looks flat, so the slice rows answer a
  different question from the pooled report and neither replaces the other.
- `HitRate@Top10` inside a slice selects the top ten symbols of that slice, not
  the top ten of the market.
- A date whose slice holds fewer than 10 origins is
  dropped from that slice only, so slices can carry different date counts. A
  paired comparison between two candidates on the same slice stays valid because
  both candidates share the same origins and therefore the same dropped dates.
- Slice labels were fixed by `evaluation/run_origin_slices.py` before any metric
  here was computed, and the symbol groups read no price or result at all.

## Guardrails

- Per-date files are written under the same
  `{candidate}_per_date_metrics.csv.gz` convention, so
  `evaluation/run_paired_comparison.py` consumes them unchanged.
- Slicing multiplies the number of comparisons. SPEC section 8.7 registers the
  slice keys and section 8.9 requires a multiplicity correction before any slice
  result is read as evidence; an unregistered slice search is data snooping.
- The 2026 lockbox remains closed.
