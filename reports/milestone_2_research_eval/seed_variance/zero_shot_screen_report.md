# M2.5 Zero-Shot Kronos Screen Report

## Decision

This is a screening run on a strided subsample of the frozen common origins. It ranks candidates for a later confirmation run; it is not a promotion decision.
No model was trained. The 2026 lockbox remains closed.

## Registered Setup

- Registry SHA256: `dcd71d14c5016b721111172d6a2ff384122eb74d2cc9c27252d359857e6726c6`
- Origins per arm: 26,869
- Evaluation dates: 196
- Symbols: 147
- Date stride: 10, residues [2, 5]
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
| `small_l126_r1` | 126 | 126 | 51.1519 | 50.4745 | 0.0267 | 52.6531 | 0.026103 | 0.4045 | 0.051396 |
| `small_l126_r2` | 126 | 126 | 51.3343 | 50.6031 | 0.0253 | 52.1939 | 0.026101 | 0.4025 | 0.051123 |
| `small_l126_r3` | 126 | 126 | 50.8541 | 51.1580 | 0.0255 | 51.9898 | 0.026103 | 0.3954 | 0.050923 |
| `small_l126_r4` | 126 | 126 | 50.7797 | 50.5523 | 0.0218 | 51.7857 | 0.026117 | 0.4009 | 0.051260 |
| `small_l126_r5` | 126 | 126 | 51.3305 | 50.8970 | 0.0253 | 52.6020 | 0.026082 | 0.4021 | 0.051229 |

## Runtime

| arm | origins | seconds | origins/s | peak VRAM GB |
|---|---:|---:|---:|---:|
| `small_l126_r1` | 26,869 | 1561.7 | 17.20 | 0.20 |
| `small_l126_r2` | 26,869 | 1565.0 | 17.17 | 0.20 |
| `small_l126_r3` | 26,869 | 1566.6 | 17.15 | 0.20 |
| `small_l126_r4` | 26,869 | 1564.6 | 17.17 | 0.20 |
| `small_l126_r5` | 26,869 | 1564.0 | 17.18 | 0.20 |

## How To Read The Arms

- `small_l63` versus `small_l126` mixes context length with the normalization
  scale, because `L` sets both.
- `small_l63_norm126` holds the 126-session rows but borrows
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
