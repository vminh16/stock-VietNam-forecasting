# M2.8 Cross-Sectional Gate Reading

Read against SPEC section 8.10, registered in commit `7eb785c` before either
reference was computed. **Provisional**, as that section requires: the M2.7 arms
were measured before the references existed, so only the reference side of this
comparison is prospective. The confirmatory reading happens inside the next
registered run.

## Which reference is the gate

Registered rule: the reference with the higher pooled RankIC over all 977 dates,
chosen from baseline data alone before any model number enters.

| reference | RankIC (977 dates) | DA | MW-DA | HitRate@Top10 |
|---|---:|---:|---:|---:|
| **`short_term_reversal`** | **0.0153** | 50.10 | 47.50 | 49.98 |
| `momentum_126_21` | 0.0088 | 50.53 | 50.55 | 50.69 |

`short_term_reversal` is the gate. Both references are far from zero, unlike the
M2.2 pair at `0.0000` and `-0.0086`, so a cheap formula does rank this market.

Neither reference is stable across regimes. `short_term_reversal` runs
`-0.0102 / +0.0290 / +0.0395 / +0.0027` across 2022 to 2025, and
`momentum_126_21` runs `-0.0143 / +0.0044 / +0.0523 / -0.0075`. Both are negative
in the falling 2022 fold. A reference that is itself unstable makes a demanding
but noisy gate, which is part of why the intervals below are wide.

## Rule 1: the gate does not pass

Paired stationary date-block bootstrap on the 196 M2.7 dates, 5,000 replicates.

| contrast | RankIC difference | 95% interval | gate |
|---|---:|---|---|
| `small_l126` vs `short_term_reversal` | `+0.0060` | `[-0.0234, +0.0356]` | **fails** |
| `base_l126` vs `short_term_reversal` | `+0.0090` | `[-0.0184, +0.0378]` | **fails** |

On these dates `short_term_reversal` scores RankIC `0.0210` against `0.0270` for
`small_l126` and `0.0300` for `base_l126`. Neither model separates from the
formula.

This changes how M2.7's headline must be read. Both arms cleared the M2.2 naive
gate with intervals excluding zero, and that remains true. It now reads as
"better than noise" rather than "better than a cheap alternative", which is the
claim a ranking product actually needs.

Against the weaker reference, `momentum_126_21`, the differences are larger,
`+0.0266` and `+0.0296`, but both intervals still contain zero. The registered
gate is the stronger reference, so this row changes nothing; it is recorded only
so the choice of gate is auditable.

## Rule 1 does not sweep everything away

`small_l126` beats `short_term_reversal` on MW-DA by `+2.85` percentage points
with interval `[+0.12, +5.62]`, which excludes zero. `base_l126` does not,
at `+1.99` with `[-1.20, +5.11]`.

MW-DA weights each directional call by the size of the move it got right, so
this says Kronos-small is better than reversal at being right when the move is
large, while being indistinguishable from it at ordering the cross-section. Those
are different questions and the ranking one is primary for this product, so this
does not lift the gate. It is the one place a model advantage survives contact
with a real reference, and it is a single marginal interval that has not been
replicated.

HitRate@Top10 favours both arms by `+1.94` points, both intervals containing
zero.

## What the references cannot be compared on

`short_term_reversal` and `momentum_126_21` emit point forecasts replicated
across samples. CRPS, interval coverage, and interval width are undefined for
them, are omitted from every table here, and MUST NOT be compared. The
calibration finding from M2.7 stands on its own evidence: both arms cover 0.36 to
0.40 inside a nominal 80% band.

## Consequence for the next run

The next registered run must carry these two references through unchanged, and
must read the gate prospectively on both sides. Three specific items follow:

1. The effect size the run is powered for should be set against
   `short_term_reversal`, not against `recent_return_bootstrap`. The M2.7 sizing
   of ~681 dates was computed for the small-versus-base contrast; the
   model-versus-reversal contrast has a half-width of `0.0295` at 196 dates and
   therefore needs its own sizing.
2. A probabilistic version of the reversal reference, an empirical dispersion
   centred on the signal, would let CRPS and coverage be compared against a
   ranking-capable baseline. It is not registered and MUST NOT be added without
   registration.
3. The liquidity gradient from M2.7 should be re-read against these references
   per tier, since short-term reversal is itself known to concentrate in less
   liquid names. If reversal explains the gradient, the M2.7 slice finding is
   about the effect, not about Kronos.
