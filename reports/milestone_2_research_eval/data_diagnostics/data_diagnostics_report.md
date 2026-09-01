# M2.4 Data Diagnostics Report

## Decision

Two training-free diagnostics run before any GPU is spent on a lookback
comparison. E0 measures how far VN150 daily returns depart from the random walk
that the `sqrt(h)` uncertainty argument assumes. E1 measures how much of an
`L=63` versus `L=126` difference would come from the normalization window rather
than from context length, because `L` sets both.

## E0 Variance Ratio

`VR(q) = Var(R_q) / (q * Var(r))` with overlapping q-period returns and the
Lo-MacKinlay heteroskedasticity-consistent statistic. `VR = 1` is the random
walk; below one is mean reversion, above one is trending. A series is counted as
mean-reverting or trending when `|z*| > 1.96`.

| fold | q | series | median VR | IQR | share mean-reverting | share trending |
|---|---:|---:|---:|---|---:|---:|
| eval_2022 | 2 | 145 | 1.1101 | [1.0149, 1.1894] | 0.021 | 0.324 |
| eval_2022 | 5 | 145 | 1.1450 | [0.9343, 1.3175] | 0.021 | 0.228 |
| eval_2022 | 10 | 145 | 1.1652 | [0.9037, 1.4013] | 0.000 | 0.172 |
| eval_2023 | 2 | 146 | 1.0032 | [0.9520, 1.0552] | 0.048 | 0.027 |
| eval_2023 | 5 | 146 | 0.9510 | [0.8645, 1.0451] | 0.027 | 0.021 |
| eval_2023 | 10 | 146 | 0.9202 | [0.7923, 1.0500] | 0.000 | 0.007 |
| eval_2024 | 2 | 151 | 0.9580 | [0.8974, 1.0303] | 0.113 | 0.033 |
| eval_2024 | 5 | 151 | 0.9463 | [0.8483, 1.0672] | 0.026 | 0.033 |
| eval_2024 | 10 | 151 | 0.9583 | [0.8331, 1.0873] | 0.007 | 0.033 |
| eval_2025 | 2 | 149 | 1.0726 | [1.0181, 1.1373] | 0.007 | 0.060 |
| eval_2025 | 5 | 149 | 1.0074 | [0.9013, 1.1452] | 0.020 | 0.040 |
| eval_2025 | 10 | 149 | 0.9614 | [0.7717, 1.1435] | 0.013 | 0.027 |

| liquidity tier | q | series | median VR | IQR | share mean-reverting | share trending |
|---|---:|---:|---:|---|---:|---:|
| high | 2 | 199 | 1.0331 | [0.9517, 1.1003] | 0.045 | 0.111 |
| high | 5 | 199 | 1.0023 | [0.8877, 1.1300] | 0.005 | 0.065 |
| high | 10 | 199 | 0.9840 | [0.8343, 1.1661] | 0.000 | 0.065 |
| low | 2 | 197 | 1.0195 | [0.9105, 1.0999] | 0.071 | 0.076 |
| low | 5 | 197 | 0.9643 | [0.7977, 1.1606] | 0.051 | 0.071 |
| low | 10 | 197 | 0.9479 | [0.7521, 1.1565] | 0.015 | 0.041 |
| mid | 2 | 195 | 1.0460 | [0.9690, 1.1297] | 0.026 | 0.144 |
| mid | 5 | 195 | 0.9965 | [0.9005, 1.1610] | 0.015 | 0.103 |
| mid | 10 | 195 | 0.9886 | [0.8508, 1.1625] | 0.000 | 0.072 |

Liquidity tiers are in-fold descriptive terciles of median `close * volume`, not
point-in-time tiers; they classify data, never a forecast.

## E1 Normalization Confound

Each sampled origin is normalized three ways over the same rows: `short` uses
the trailing 63 sessions with their own moments, `long`
uses 126 sessions with their own moments, and
`short_scaled_by_long` keeps the 63 short rows but borrows
the 126-session mean and scale. `short` versus
`short_scaled_by_long` isolates the normalizer, since the rows are identical.

- Sampled windows: 13,431
- Mean clip rate at `|z| >= 5`: short
  0.00061, long
  0.00086, short scaled by long
  0.00090
- Mean `|z|`: short 0.7959, long
  0.7916, short scaled by long
  0.7814

| feature | median scale ratio | 10-90% scale ratio | median abs mean shift |
|---|---:|---|---:|
| amount | 0.9759 | [0.5268, 1.1888] | 0.2900 |
| close | 0.7320 | [0.3751, 1.1231] | 0.5736 |
| high | 0.7318 | [0.3780, 1.1234] | 0.5729 |
| low | 0.7344 | [0.3761, 1.1236] | 0.5705 |
| open | 0.7369 | [0.3824, 1.1230] | 0.5689 |
| volume | 0.9725 | [0.5789, 1.1781] | 0.2644 |

`scale_ratio` is the short-window scale divided by the long-window scale, and
`mean_shift` is the difference in window means expressed in long-window scale
units. Values away from one and zero mean the two lookbacks hand the tokenizer
differently scaled inputs for the same sessions.

The price channels are rescaled by a median factor of
1.364 when the normalizer moves from 126 to
63 sessions, and their window means sit
0.572 long-window scale units apart, while the volume channels move
only to 0.9742. An `L=63` versus
`L=126` result therefore mixes context length with a
substantially different price scaling, and the mixture is concentrated in exactly
the channels the forecast depends on. Report any lookback conclusion as
`context + normalization`, or add a third arm that holds the normalizer fixed.

## Guardrails

- Both diagnostics describe data only. No model ran and no forecast was scored.
- Variance ratios are computed inside one segment at a time; no return crosses a
  segment or a fold boundary.
- The 2026 lockbox remains closed.

## Next Step

E2 remains the deciding experiment: a zero-shot screen of `{small, base}` by
`{63, 126}` on the frozen common origins. These diagnostics only tell that
screen how to phrase its conclusion.
