# M2.7 Confirmation Decision

Read against SPEC section 8.8, registered in commit `7431e6c` on 2026-09-02
before the run started. Machine records are `zero_shot_screen_report.md`,
`paired_inference/`, `metric_slices/`, and `slice_inference/` in this directory.

## Setup

Two arms, `small_l126` and `base_l126`, on 26,869 origins over the 196 dates at
positions `{2, 5} mod 10` of the frozen registry. The M2.5 screen used
`{0 mod 10}`; the two date sets share no date, so these arms were not confirmed
on the dates that selected them. Ten sample paths, `T=0.6`, `top_p=0.9`, seed
`20260901`, 49 dates in each of the four folds, minimum cross-section 128
symbols. Runtime 6.5 hours on one RTX 2050.

## Rule 1, primary: the non-inferiority margin does not pass

| quantity | value | registered bound | result |
|---|---:|---:|---|
| RankIC paired difference | `-0.0030` | — | — |
| RankIC 95% lower bound | `-0.0215` | `> -0.01` | **fails** |
| MW-DA paired difference | `+0.8619` | — | — |
| MW-DA 95% lower bound | `-1.1373` | `> -1.0` pp | **fails** |

Kronos-small does **not** survive the registered non-inferiority test.

This is not evidence that small is worse. The point estimate is `-0.0030`, a
third of the margin, and the interval is nearly symmetric around zero. The test
fails because the interval is too wide, not because the difference is large.

## The design still cannot resolve its own margin

The achieved 95% half-width on the primary contrast is `0.0186`, against a
registered margin of `0.0100`. The margin remains untestable.

The earlier estimate that about 210 dates would suffice was wrong, and the error
is worth recording. It came from scaling the M2.5 interval, whose half-width was
`0.0157` at 98 dates. That interval was too narrow: the per-date paired
difference has standard deviation `0.1059` on the screen dates against `0.1179`
here, and the two arms correlate `0.719` there against `0.581` here. Doubling
the dates produced a *wider* interval, so the screen's interval was an optimistic
draw rather than a stable measurement.

Sizing from this run instead:

| margin | paired dates needed | share of the registry | GPU hours, these two arms |
|---:|---:|---:|---:|
| `0.010` | ~681 | 70% | ~22.5 |
| `0.015` | ~303 | 31% | ~10.0 |
| `0.020` | ~170 | 17% | ~5.6 |

Certifying the registered `0.01` margin needs roughly 681 paired dates, not 210.
Either the run grows to most of the registry, or the margin is renegotiated
before the next run and the change is registered. It MUST NOT be renegotiated
after seeing a result it would flip.

## Rule 2, gate: both arms clear the naive reference

| contrast | RankIC difference | 95% interval | verdict |
|---|---:|---|---|
| `small_l126` vs `recent_return_bootstrap` | `+0.0446` | `[+0.0134, +0.0741]` | **excludes zero** |
| `base_l126` vs `recent_return_bootstrap` | `+0.0476` | `[+0.0104, +0.0831]` | **excludes zero** |

This is the first time in this project that zero-shot Kronos has beaten the
causal naive reference on the primary product metric with an interval excluding
zero. No arm managed it in the M2.5 screen.

One caveat belongs next to the claim. `recent_return_bootstrap` scores RankIC
`-0.0176` on these 196 dates against `-0.0086` over all 977, so the reference is
running below its own long-run average here and part of the gap is the
reference's bad patch rather than the model's skill. The arms' own RankIC,
`0.0270` and `0.0300`, is close to what the screen measured on disjoint dates,
which is the more reassuring half of the result.

## Rule 3, secondary and descriptive

- Both arms beat `persistence` on RankIC and HitRate@Top10 with intervals
  excluding zero. `persistence` carries no information, so this is a floor check.
- DA is `51.14` for small and `51.44` for base, both below the `52%` utility
  floor and both inside every naive comparison's interval. DA decides nothing.
- **Calibration remains broken.** Coverage is `0.398` for small and `0.359` for
  base inside a nominal `80%` band, confirmed now on a disjoint date set. Both
  arms have worse CRPS than the naive bootstrap. Kronos intervals MUST NOT be
  described as calibrated.
- CRPS and width compare a ten-path ensemble against the references' twenty-path
  ensembles, so those two rows are directional only, as registered.
- Per-fold primary differences are `-0.0136`, `+0.0208`, `-0.0125`, `-0.0067`
  for 2022 to 2025. Signs flip and every fold interval contains zero, so no
  regime carries the pooled result.

## Rule 4, slices: stable, with one product-relevant gradient

All eight registered slice contrasts of `small_l126` against `base_l126` return
insufficient evidence, ranging from `-0.0208` to `+0.0135` with every interval
containing zero. No slice carries the pooled result and none contradicts it.

The descriptive slice levels show a monotone gradient in liquidity for both arms:

| slice | `small_l126` RankIC | `base_l126` RankIC |
|---|---:|---:|
| `tier_0`, most liquid | 0.0162 | 0.0182 |
| `tier_1` | 0.0313 | 0.0361 |
| `tier_2`, least liquid | 0.0466 | 0.0440 |

The ranking signal is roughly three times stronger among the least liquid third
of the market than among the most liquid third. That is a product problem, not a
model win: a radar whose Top10 is drawn where the signal lives would select names
that are hardest to trade, and the `amount` column those tiers rank is the
`volume * OHLC4` proxy, not provider turnover.

This gradient is **descriptive only**. Testing it needs `small_l126` against
`recent_return_bootstrap` inside each tier, which is not registered and was
deliberately not computed. It is the obvious first entry in the next
registration.

## Standing

M2 does not close. Against the eight gaps recorded on 2026-09-02:

| gap | status |
|---|---|
| #1 date count | improved to 196 disjoint dates, but the margin needs ~681 |
| #2 single seed | open |
| #3 unseen-symbol groups | infrastructure done; not a holdout until training exists |
| #4 liquidity slices | **closed**, and it produced the liquidity gradient above |
| #5 registration gap | **closed**, registered and computed here |
| #6 single `T`/`top_p`, M0 comparability | open |
| #7 `L=40` arm | open |
| #8 `sample_count` 10 not 20 | open |

Dropping `small_l40`, `small_l63`, `small_l63_norm126`, and `base_l63` was a
budget decision taken before the run and MUST NOT be read as a finding about
those arms.

The next registration should decide the margin question first, because the
backbone choice gates M3 and the current answer is "the instrument is too coarse
to tell", not "the two are equal".
