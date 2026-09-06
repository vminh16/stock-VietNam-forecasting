# M2.9 Sampling-Noise Budget: Decision

Read against SPEC section 8.11, registered in commit `c8d99a7` before any
replicate was computed. Five replicates of `small_l126` over the 196 M2.7
confirmation dates, `{2, 5 mod 10}`, 26,869 origins each. The replicates differ
only in their RNG stream: identical model, lookback, normalizer, sample count,
temperature, top-k and top-p, with the arm identifier mixed into the per-origin
seed and into nothing else. All five carry distinct cache keys and ran at 17.15
to 17.20 origins per second.

## Rule 4: sampling noise is immaterial

| metric | mean | sd across seeds | range | min | max |
|---|---:|---:|---:|---:|---:|
| **RankIC** | **0.024915** | **0.001849** | 0.004932 | 0.021781 | 0.026712 |
| DA | 51.090104 | 0.261367 | 0.554542 | 50.779709 | 51.334251 |
| MW-DA | 50.736991 | 0.284525 | 0.683510 | 50.474525 | 51.158035 |
| HitRate@Top10 | 52.244898 | 0.378377 | 0.867347 | 51.785714 | 52.653061 |
| CRPS | 0.026101 | 0.000012 | 0.000034 | 0.026082 | 0.026117 |
| coverage | 0.401079 | 0.003410 | 0.009044 | 0.395437 | 0.404481 |
| interval width | 0.051186 | 0.000176 | 0.000473 | 0.050923 | 0.051396 |

`sd_seed` on the primary metric is `0.001849` against the registered threshold
of `0.003763`. **Rule 4 applies.** Combining sampling noise with date-resampling
noise widens every reported interval by a factor of `1.0075`, that is 0.75%.
Single-seed runs stand, and M2.5, M2.7 and M2.8 keep their readings.

The distributional metrics are the steadiest of all. CRPS moves by 12 parts per
million of its own value and interval width by 0.3%, so the calibration finding,
80% intervals covering 0.395 to 0.404, is not a seed artifact in any degree.

## What the pooled number does not cover

Two qualifications follow from the same table, and neither is a gate.

**The margin over the reference is small relative to this noise.** On these dates
M2.8 measured `small_l126` above `short_term_reversal` by `+0.0060` RankIC. Seed
noise alone is `0.0018`, so the entire claimed advantage is 3.2 times a quantity
that carries no information. Recomputing the interval with both noise sources
moves it from `[-0.0234, +0.0356]` to `[-0.0237, +0.0357]`. The gate was already
not cleared and still is not; the point is that the point estimate itself is not
a stable number.

**The one surviving model advantage loses most of its margin.** M2.8 found
`small_l126` above `short_term_reversal` on MW-DA by `+2.85` points with
`[+0.12, +5.62]`, the single interval excluding zero. Seed noise on MW-DA is
`0.2845` points. The combined interval becomes `[+0.044, +5.656]`. It still
excludes zero, but its lower bound falls from `+0.12` to `+0.044`, roughly a
sixth of one seed standard deviation away from zero. That finding should be
treated as unreplicated rather than established.

## Fold-level noise is much larger, and this is the load-bearing result

The registered readout is pooled over 196 dates. Split by fold, at 49 dates
each:

| fold | dates | RankIC mean | sd across seeds | range | sd as share of mean |
|---|---:|---:|---:|---:|---:|
| eval_2022 | 49 | 0.036349 | 0.003880 | 0.009244 | 11% |
| eval_2023 | 49 | 0.027216 | 0.006575 | 0.016225 | 24% |
| eval_2024 | 49 | 0.025299 | 0.006759 | 0.015867 | 27% |
| eval_2025 | 49 | 0.010798 | 0.008930 | 0.021891 | **83%** |

In `eval_2025` the seed-to-seed spread is `0.0219`, twice the fold's own mean,
and the standard deviation is 83% of it. A single-seed RankIC for that fold
carries almost no information about that fold.

Quartering the dates raises `sd_seed` by 2.1 to 4.8 times against the 2.0 that
independent averaging predicts, so 2025 is not merely a smaller sample; its
per-date variance is genuinely higher.

Consequence, stated as a limit rather than a rule, since section 8.11 registered
no fold-level threshold: **any per-fold or per-slice RankIC read from one seed is
unreliable, and the smaller the partition the worse it gets.** That reaches
directly into the M2.6 liquidity-tier evidence of section 3.4 and the per-regime
readings in the M2.8 gate note, which were all computed from a single seed. It
does not overturn them; it says their precision has never been measured. Any
future claim resting on a partition of the evaluation set should either average
over seeds or carry an explicit statement that its precision is unknown.

## Readout 3: the bootstrap is calibrated for runs, not for models

Ten replicate-versus-replicate contrasts, seven metrics, under the section 8.5
paired stationary block bootstrap. Every one of these compares a sampler with
itself, so at 95% confidence roughly one interval in twenty should exclude zero.

| scope | dates | rows | exclude zero | rate |
|---|---:|---:|---:|---:|
| pooled | 196 | 70 | 7 | 10.0% |
| eval_2022 | 49 | 70 | 7 | 10.0% |
| eval_2023 | 49 | 70 | 13 | 18.6% |
| eval_2024 | 49 | 70 | 13 | 18.6% |
| eval_2025 | 49 | 70 | 12 | 17.1% |

The rows are not independent, since ten contrasts over five replicates share
replicates and seven metrics share the same draws, so the counts alone are not a
clean test. The mechanism is the stronger evidence, because it predicts exactly
which metrics fail.

Write `se_seed` for the seed standard error of a replicate difference,
`sd_seed * sqrt(2)`, and `se_date` for the median bootstrap standard error of
the same contrasts:

| metric | sd_seed | se_seed | se_date | se_seed / se_date | excludes zero |
|---|---:|---:|---:|---:|---:|
| interval_width | 0.000176 | 0.000250 | 0.000129 | **1.94** | 2/10 |
| coverage | 0.003410 | 0.004822 | 0.002552 | **1.89** | 3/10 |
| DA | 0.261367 | 0.369629 | 0.285631 | **1.29** | 2/10 |
| MW-DA | 0.284525 | 0.402379 | 0.451429 | 0.89 | 0/10 |
| HitRate@Top10 | 0.378377 | 0.535107 | 0.832986 | 0.64 | 0/10 |
| RankIC | 0.001849 | 0.002615 | 0.005201 | 0.50 | 0/10 |
| CRPS | 0.000012 | 0.000017 | 0.000037 | 0.46 | 0/10 |

The split is exact. Every metric whose seed noise exceeds the bootstrap's own
standard error produces false positives, and no metric below that line produces
any.

The cause is not a bug. The paired date bootstrap conditions on the sample paths
that were actually drawn. It answers "do these two realizations differ
consistently across dates", and answers it correctly. It does not answer "do
these two models differ", because it never resamples the draw. For a metric
where the seed component is comparable to the date component, those two
questions have different answers.

Operationally: `sd_seed` in the table above is the reusable quantity. For any
claim about a **model** rather than a **run**, add it in quadrature to whatever
`se_date` that contrast carries. The inflation is small when `se_date` is large,
which is why the M2.8 RankIC contrast moves by only 0.75%: its `se_date` is
`0.01505` against a model-side seed component of `0.001849`. It is not small when
`se_date` is itself tiny, which is the case for coverage and interval width.

This does not touch the calibration finding of section 3.5. Nominal 80%
intervals cover `0.395` to `0.404` across the five replicates, and the gap to
`0.80` is more than a hundred times `sd_seed` on that metric.

## Outstanding

All three readouts of section 8.11 are complete. The registered decision, rule
4, stands on the pooled RankIC number and is unaffected by readout 3, which
section 8.11 registered as diagnostic rather than as a gate.

What is still unmeasured is the seed component for `base_l126`, excluded from
this run by design, and the fold-level threshold that section 8.11 deliberately
did not register. Both are recorded above as limits rather than as open gates.
