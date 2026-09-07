# M2.11 Sampling Grid: Decision

Read against SPEC section 8.13, registered in commit `2d127c7` before any cell
was computed. One arm, `small_l126`, on the 98 M2.5 screen dates, 13,431 origins
per cell, 0.22 hours a cell and 0.87 in total against a registered budget of
0.87.

## The grid

| cell | temperature | top_p | CRPS | coverage | width | RankIC | DA | MW-DA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `t06_p90` (incumbent) | 0.6 | 0.9 | 0.025553 | 0.398407 | 0.051589 | **0.031551** | 50.867 | 49.640 |
| `t06_p100` | 0.6 | 1.0 | 0.025189 | 0.456705 | 0.060847 | 0.027569 | 51.232 | 49.636 |
| `t10_p90` | 1.0 | 0.9 | **0.024977** | 0.532127 | 0.074703 | 0.010767 | 51.061 | 48.926 |
| `t10_p100` | 1.0 | 1.0 | 0.025338 | **0.587224** | 0.089957 | -0.001369 | 50.339 | 47.031 |

Seed noise rescaled from M2.9 to 98 dates: `0.002615` on RankIC, `0.000017` on
CRPS, `0.004822` on coverage.

## The registered rule adopts nothing

Rule 1 picks the lowest CRPS: `t10_p90` at `0.024977`, better than the incumbent
by `0.000576`, which is 34 seed standard deviations and so not a tie under
rule 4.

Rule 3 then checks the guard. The best RankIC in the grid is the incumbent's
`0.031551`, so the floor is `0.026551`.

| cell | RankIC | drop from best | guard |
|---|---:|---:|---|
| `t06_p90` | 0.031551 | 0.000000 | pass |
| `t06_p100` | 0.027569 | 0.003982 | pass |
| `t10_p90` | 0.010767 | **0.020784** | **fail** |
| `t10_p100` | -0.001369 | **0.032920** | **fail** |

The CRPS winner drops RankIC by four times what the guard allows. Rule 3 says a
winner that fails the guard is reported and not adopted, so **the incumbent
stands and no sampling change is made.**

The rule as written stops there. It does not provide for falling to the
runner-up, and inventing that step now would be a procedure chosen after seeing
the numbers. `t06_p100` is therefore recorded below as an observation, not as a
decision.

## What the grid actually shows

### Both dials widen the distribution, and they are additive

Against the incumbent:

| effect | coverage | width | RankIC |
|---|---:|---:|---:|
| stop truncating (`top_p 0.9` to `1.0`) | +0.058 | +0.009 | -0.004 |
| raise temperature (`0.6` to `1.0`) | +0.134 | +0.023 | -0.021 |
| both | +0.189 | +0.038 | -0.033 |
| interaction | -0.003 | +0.006 | -0.008 |

The two levers barely interact on coverage, so they can be reasoned about
separately. Temperature is roughly twice the lever that truncation is.

### The sampler explains most of the calibration gap, but not all of it

Section 3.10 put the ceiling for a perfectly calibrated sampler at ten draws at
`0.66`. The incumbent sits at `0.398`, so the gap is `0.262`.

Opening both dials reaches `0.587`. That recovers **72%** of the gap and leaves
`0.073`.

This is the answer the study was registered to get, and it cuts both ways. Most
of what has been described in this project as Kronos being overconfident is two
configuration values inherited from the M0 baseline, not the model failing to
understand Vietnamese volatility. But `t10_p100` applies **no filtering at all**,
so it is the model's undistorted predictive distribution, and it still falls
`0.073` short of what a perfectly calibrated sampler would reach. That residual
belongs to the model.

### Opening the dials destroys the ranking signal

This is the finding that decides the outcome.

| cell | RankIC | in units of the 98-date seed noise |
|---|---:|---:|
| `t06_p90` | 0.031551 | 12.1 |
| `t06_p100` | 0.027569 | 10.5 |
| `t10_p90` | 0.010767 | 4.1 |
| `t10_p100` | -0.001369 | **-0.5** |

At the undistorted setting RankIC is `-0.001369`, indistinguishable from zero and
slightly negative. MW-DA falls to `47.03`, well below the 50 a coin flip gives.

The mechanism is the sample count, not the model. A ranking score depends on the
mean of the sampled paths for each symbol, and that mean is estimated from ten
draws. Widening the distribution widens the sampling error of that mean by the
same factor, so the cross-sectional ordering degrades even though the
distribution it came from is better calibrated. The narrow incumbent setting is
not producing a better model; it is producing a more stable estimate of the
centre from very few draws.

CRPS sees both sides at once, which is why its optimum is interior: `t10_p90` is
better than both the incumbent and the fully open corner.

## Observation, not a decision

`t06_p100`, keeping `temperature 0.6` and stopping the truncation, passes the
guard and improves on the incumbent on both readouts:

| | incumbent | `t06_p100` |
|---|---:|---:|
| CRPS | 0.025553 | **0.025189** |
| coverage | 0.398407 | **0.456705** |
| RankIC | 0.031551 | 0.027569 (drop 0.004, inside the 0.005 guard) |

That is a better calibrated forecast at a ranking cost the registered guard was
willing to pay. It is **not adopted here**, because rule 1 named a different
winner and the fallback was never registered. Adopting it needs its own
registration and a confirmatory run on dates disjoint from these 98, as section
8.13 already requires of any winner.

## What follows

The residual `0.073` is the honest measure of what a fine-tune has to fix on
calibration, and it is about a quarter of what this project has been quoting.
The larger question the grid raises is the sample count: ten draws are enough to
rank only because the distribution is kept artificially narrow, and a setting
that is both well calibrated and able to rank probably needs more draws rather
than different dials. Sample count is part of a locked measurement, so testing
that needs its own registration.
