# M2.10 Full-Registry Confirmation: Decision

Read against SPEC section 8.12, registered in commit `7dd81ce` before the run
started. 683 dates in `{1, 3, 4, 6, 7, 8, 9 mod 10}`, 93,637 origins per arm,
disjoint from the 98 dates that selected these arms and the 196 that confirmed
them. This is the first reading of every gate in which both sides were computed
after registration.

## Acceptance criteria

| criterion | required | observed | |
|---|---|---|---|
| dates evaluated | 683 | 683, both arms | pass |
| origins per arm | 93,637 | 93,637, both arms | pass |
| registry hash | `dcd71d14...6726c6` | matches | pass |
| lockbox | closed | `lockbox_opened: false` | pass |
| worktree | `worktree_dirty: false` | `true` | **fail** |

The last criterion was specified badly and cannot be satisfied by any run. The
manifest is written after the run has already created output inside the
worktree, and the host also carries untracked weights and a virtual environment,
so `git status --porcelain` is never empty at that moment. It is recorded as
failed rather than reinterpreted, because SPEC forbids changing a registered
threshold after seeing a result.

What that criterion was meant to protect is provenance, and provenance is
established directly: the manifest records `code_revision`
`7dd81ce59cf2c60f019c0c35951d882fe3bcbfaf`, which is the registration commit
itself. A future registration should ask for no modified tracked file instead of
a clean worktree.

Runtime: `small_l126` 1.52 h at 17.14 origins per second, `base_l126` 5.96 h at
4.36, total 7.48 h against a registered budget of 7.24 h.

## The four primary readings

Intervals are 95% paired stationary block bootstrap, 5,000 replicates, mean
block 10 dates. The seed-corrected column adds the M2.9 `sd_seed` in quadrature
as SPEC 8.12 rule 4 requires; that correction is what the reading uses.

| # | contrast | metric | difference | raw interval | seed-corrected | verdict |
|---|---|---|---:|---|---|---|
| P1 | `small_l126` vs `short_term_reversal` | RankIC | `+0.0054` | `[-0.0153, +0.0270]` | `[-0.0161, +0.0268]` | **fails** |
| P2 | `base_l126` vs `short_term_reversal` | RankIC | `+0.0044` | `[-0.0159, +0.0266]` | `[-0.0172, +0.0260]` | **fails** |
| P3a | `small_l126` vs `recent_return_bootstrap` | RankIC | `+0.0287` | `[+0.0072, +0.0497]` | `[+0.0072, +0.0503]` | passes |
| P3b | `base_l126` vs `recent_return_bootstrap` | RankIC | `+0.0278` | `[+0.0040, +0.0523]` | `[+0.0033, +0.0522]` | passes, provisional |
| P4 | `small_l126` vs `base_l126` | RankIC | `+0.0010` | `[-0.0081, +0.0102]` | `[-0.0089, +0.0109]` | passes, provisional |
| P4 | `small_l126` vs `base_l126` | MW-DA | `+1.1711` | `[-0.1126, +2.5813]` | `[-0.2868, +2.6289]` | passes |

### The cross-sectional gate fails, and now it fails confirmatorily

Neither arm separates from `short_term_reversal` on RankIC. M2.8 reached the
same conclusion but had to label it provisional, because the arms had been
measured before the reference existed. On these 683 dates both sides were
computed after registration, so the conclusion is now confirmatory.

It is also robust to the choice of reference. Against `momentum_126_21`, the
weaker formula that section 8.10 deliberately did **not** make the gate, the
differences are `+0.0117` and `+0.0107` and both intervals still contain zero.
Kronos cannot separate from either cheap formula.

On these dates `short_term_reversal` scores RankIC `0.0154`, `small_l126`
`0.0208` and `base_l126` `0.0198`.

### The naive gate passes

Both arms beat `recent_return_bootstrap`, which scores RankIC `-0.0079` here.
Section 8.10 already fixed how to read that: necessary, not sufficient. It means
better than noise, not better than an alternative.

### Non-inferiority passes by a hair

Section 8.6 rule 4 asks for a RankIC lower bound above `-0.01` and an MW-DA
lower bound above `-1.0`. The seed-corrected bounds are `-0.0089` and `-0.2868`.
Both clear.

The RankIC bound clears by `0.0011`, which is 11% of the threshold. Read
literally the rule passes and Kronos-small survives as the development
candidate. Read honestly, this is a margin a different draw could erase.

### Two readings are provisional under the registered contingency

Section 8.12 registered that any `base_l126` primary interval ending within
three times the corresponding `small_l126` `sd_seed` of its decision boundary is
provisional, because `base_l126` has no measured seed component. That threshold
is `3 x 0.001849 = 0.005547` on RankIC.

| reading | nearest interval end to its boundary | status |
|---|---:|---|
| P2 | `0.0172` | final |
| P3b | `0.0033` | **provisional** |
| P4 RankIC | `0.0011` | **provisional** |

The contingency was written before any of these numbers existed and it fires on
exactly the two readings that are too close to call. Resolving them needs a seed
measurement for `base_l126`: five replicates over the 196 M2.7 dates at 1.71
hours each, 8.55 hours, or three replicates at 5.13 hours for a coarser estimate.

## A correction

After the point estimates were read but before the intervals existed, the MW-DA
advantage of `small_l126` over `short_term_reversal` was described as having
replicated out of sample. The point estimate did replicate, almost exactly:
`+2.85` on the 196 M2.8 dates against `+2.81` on these 683 disjoint dates. The
interval did not follow. Raw `[-0.0835, +5.7880]`, seed-corrected
`[-0.1810, +5.7956]`; both contain zero, where the M2.8 interval
`[+0.12, +5.62]` had excluded it.

The half-width **widened**, from `2.75` at 196 dates to `2.94` at 683, which
ordinary averaging cannot produce. MW-DA weights each directional call by the
size of the move it got right, so a handful of very large days dominates its
date-level distribution and 683 dates simply contain more of them. The correct
statement is that the effect replicates in size and is not distinguishable from
zero. There is now no metric on which either Kronos arm beats
`short_term_reversal` with an interval excluding zero.

## Secondary: the small model is the better model

Not a gate, but it excludes zero on three distributional metrics and it decides
which arm the project should carry.

| metric | `small_l126` minus `base_l126` | seed-corrected interval |
|---|---:|---|
| CRPS | `-0.0003` | `[-0.0005, -0.0001]` |
| coverage | `+0.0401` | `[+0.0308, +0.0493]` |
| interval width | `+0.0056` | `[+0.0049, +0.0064]` |

`small_l126` has lower CRPS, covers `0.393` of a nominal 80% band against
`0.353`, and produces wider intervals rather than narrower ones. The larger
backbone is more confident and more wrong, at four times the compute.
`base_l126` also scores MW-DA `49.40`, below the 50 a coin flip would give,
meaning its directional calls are wrong more often than right once weighted by
how much the price actually moved.

So the practical decision to carry Kronos-small forward does not rest on the
razor-thin non-inferiority margin. It rests on three distributional intervals
that exclude zero in Kronos-small's favour, plus a cost ratio of four.

## Calibration, confirmed a third time

Nominal 80% intervals cover `0.393` for `small_l126` and `0.353` for
`base_l126`. M2.9 measured seed noise on coverage at `0.0034`, so the distance
to `0.80` is more than a hundred times the noise in it. This is the most robust
finding the project has, and the largest single piece of evidence that a
fine-tune has something to fix.

## The most recent year has no ranking signal at all

| fold | dates | `small_l126` RankIC | `base_l126` RankIC |
|---|---:|---:|---:|
| eval_2022 | 170 | 0.0156 | 0.0241 |
| eval_2023 | 171 | 0.0175 | 0.0168 |
| eval_2024 | 171 | **0.0506** | 0.0340 |
| eval_2025 | 171 | **-0.0004** | 0.0044 |

Scaling the M2.9 measurement to 171 dates puts `sd_seed` near `0.0020`, so
`-0.0004` is indistinguishable from zero, and so is `+0.0044`. The pooled RankIC
of `0.0208` is carried by a single fold, 2024, and the fold nearest to
deployment carries nothing. Per SPEC 8.12 these fold numbers have unmeasured
precision beyond that scaling and MUST NOT be read as more than a pattern.
