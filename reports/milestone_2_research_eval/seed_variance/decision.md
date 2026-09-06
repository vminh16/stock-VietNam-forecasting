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

## Outstanding

Readout 3 of section 8.11, the ten replicate-versus-replicate paired contrasts
under the section 8.5 bootstrap, has not been run. It is the calibration check
on the bootstrap itself: these contrasts compare a sampler with itself, so at
95% confidence roughly one in twenty may exclude zero and materially more would
indict the interval machinery rather than the model. It needs no GPU.

The numbers above were computed from the pooled rows of `metric_summary.csv`,
which are `summarize_metrics` applied to each replicate's per-date file, the
same function and the same inputs `run_seed_variance.py` uses. That script has
not been run because `data/evaluation/m2_9` is untracked and did not travel with
the report directory.
