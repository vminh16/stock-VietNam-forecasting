# M2.6 Metric Slice Report

## Decision

This unit recomputes the locked metrics inside pre-registered slices of the
frozen origins. It runs no model: every number comes from per-origin metric
files a previous unit already wrote. It names no winner; paired date-block
intervals over these slice files carry any comparison.

## Registered Setup

- Slice table SHA256: `8e474264cfc8b16af3dd2b053d9e965cdee2608f625f46556c57cc6aa83bd61b`
- Candidates: `persistence`, `recent_return_bootstrap`
- Slice keys: `liquidity_tier`, `symbol_group`
- Minimum cross-section per date inside a slice: 10
- Dates dropped for a thin cross-section, summed over slices: 0

## Pooled Metrics By Slice

| candidate | slice | DA | MW-DA | RankIC | HitRate@Top10 | CRPS | coverage | dates | origins |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `persistence` | `liquidity_tier=tier_0` | 50.1199 | 49.4605 | 0.0000 | 49.8772 | 0.031599 | 0.0231 | 977 | 45,042 |
| `persistence` | `liquidity_tier=tier_1` | 49.6511 | 47.4451 | 0.0000 | 49.5906 | 0.029988 | 0.0242 | 977 | 44,571 |
| `persistence` | `liquidity_tier=tier_2` | 52.8743 | 47.0561 | 0.0000 | 45.8956 | 0.027769 | 0.0525 | 977 | 44,324 |
| `persistence` | `symbol_group=group_0` | 50.4985 | 47.8999 | 0.0000 | 50.4094 | 0.030281 | 0.0281 | 977 | 28,284 |
| `persistence` | `symbol_group=group_1` | 50.7223 | 49.0400 | 0.0000 | 47.6868 | 0.030067 | 0.0332 | 977 | 24,575 |
| `persistence` | `symbol_group=group_2` | 51.0204 | 47.2660 | 0.0000 | 49.0686 | 0.029431 | 0.0340 | 977 | 21,805 |
| `persistence` | `symbol_group=group_3` | 51.3350 | 49.0041 | 0.0000 | 48.4340 | 0.031929 | 0.0287 | 977 | 24,307 |
| `persistence` | `symbol_group=group_4` | 50.8780 | 47.1521 | 0.0000 | 49.0379 | 0.027955 | 0.0399 | 977 | 34,966 |
| `recent_return_bootstrap` | `liquidity_tier=tier_0` | 49.3739 | 49.9419 | -0.0075 | 49.8874 | 0.025554 | 0.6926 | 977 | 45,042 |
| `recent_return_bootstrap` | `liquidity_tier=tier_1` | 49.6893 | 50.0665 | -0.0028 | 50.7369 | 0.024267 | 0.6891 | 977 | 44,571 |
| `recent_return_bootstrap` | `liquidity_tier=tier_2` | 49.5194 | 50.3415 | -0.0105 | 47.9734 | 0.022871 | 0.6787 | 977 | 44,324 |
| `recent_return_bootstrap` | `symbol_group=group_0` | 49.4378 | 50.2895 | -0.0048 | 49.9591 | 0.024673 | 0.6843 | 977 | 28,284 |
| `recent_return_bootstrap` | `symbol_group=group_1` | 49.0580 | 49.1791 | -0.0175 | 48.8639 | 0.024413 | 0.6877 | 977 | 24,575 |
| `recent_return_bootstrap` | `symbol_group=group_2` | 50.3646 | 50.8222 | -0.0096 | 49.4166 | 0.023971 | 0.6837 | 977 | 21,805 |
| `recent_return_bootstrap` | `symbol_group=group_3` | 49.3027 | 49.7010 | -0.0075 | 48.6387 | 0.026029 | 0.6877 | 977 | 24,307 |
| `recent_return_bootstrap` | `symbol_group=group_4` | 49.5624 | 50.5025 | -0.0082 | 50.0102 | 0.022685 | 0.6894 | 977 | 34,966 |

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
  slice keys and section 8.8 requires a multiplicity correction before any slice
  result is read as evidence; an unregistered slice search is data snooping.
- The 2026 lockbox remains closed.
