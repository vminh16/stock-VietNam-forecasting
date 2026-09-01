# M2.5 Zero-Shot Kronos Screen Report

## Decision

This is a screening run on a strided subsample of the frozen common origins. It ranks candidates for a later confirmation run; it is not a promotion decision.
No model was trained. The 2026 lockbox remains closed.

## Registered Setup

- Registry SHA256: `dcd71d14c5016b721111172d6a2ff384122eb74d2cc9c27252d359857e6726c6`
- Origins per arm: 13,431
- Evaluation dates: 98
- Symbols: 147
- Date stride: 10
- Sample paths per origin: 10
- Sampling: `T=0.6`, `top_p=0.9`, `top_k=0`,
  seed 20260901
- Batch size: 2 origins, effective
  20 sampled sequences

Sampling temperature follows the Kronos authors' published price-series setting
rather than the `T=0.7` used by the frozen M0 baseline, so these numbers compare
arms against each other and not against the M0 report.

## Metrics

| arm | L | normalizer | DA | MW-DA | RankIC | HitRate@Top10 | CRPS | coverage | width |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `small_l63` | 63 | 63 | 49.8920 | 48.2319 | 0.0013 | 53.2653 | 0.025326 | 0.3677 | 0.046968 |
| `small_l126` | 126 | 126 | 50.6813 | 50.0655 | 0.0247 | 53.9796 | 0.025549 | 0.4003 | 0.051297 |
| `small_l63_norm126` | 63 | 126 | 50.6887 | 49.5272 | 0.0224 | 53.9796 | 0.025487 | 0.3829 | 0.049262 |
| `base_l63` | 63 | 63 | 51.0833 | 48.4624 | 0.0149 | 54.6939 | 0.025609 | 0.3313 | 0.041893 |
| `base_l126` | 126 | 126 | 51.8725 | 49.1754 | 0.0267 | 54.7959 | 0.025838 | 0.3563 | 0.045890 |

## Runtime

| arm | origins | seconds | origins/s | peak VRAM GB |
|---|---:|---:|---:|---:|
| `small_l63` | 13,431 | 1354.6 | 9.91 | 0.16 |
| `small_l126` | 13,431 | 2429.2 | 5.53 | 0.20 |
| `small_l63_norm126` | 13,431 | 1367.6 | 9.82 | 0.16 |
| `base_l63` | 13,431 | 4318.6 | 3.11 | 0.48 |
| `base_l126` | 13,431 | 9140.6 | 1.47 | 0.54 |

## How To Read The Arms

- `small_l63` versus `small_l126` mixes context length with the normalization
  scale, because `L` sets both.
- `small_l63_norm126` holds the 63-session rows but borrows
  the 126-session mean and scale, so `small_l63` versus `small_l63_norm126`
  isolates the normalizer and `small_l63_norm126` versus `small_l126` isolates
  context length.
- `base_*` arms answer whether the 102.3M backbone earns its cost over the 24.7M
  one on this population.
- Point estimates alone decide nothing. Paired date-block intervals come from
  `evaluation/run_paired_comparison.py` over the same per-date metric files.

## Guardrails

- Every arm runs on identical origins, identical targets, and a per-date seed
  shared by construction across arms.
- Normalization is lookback-only; no future observation enters an input window.
- Kronos code is unmodified; sampling reuses the frozen `generate_raw` path.
