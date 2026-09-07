# Is the sample mean the right ranking statistic, and would more samples help?

**Exploratory, not a registered test.** It runs on the 196 M2.9 dates, which are
already spent, and on artifacts that already exist, so it costs no GPU and
decides nothing on its own. Anything adopted from it needs its own registration
and a confirmatory run on disjoint dates.

The question came from M2.11. That grid showed the ranking signal collapsing as
the predictive distribution widened, and attributed it to the sample count rather
than to the model. Two things follow that were worth checking before spending
anything: whether averaging the sampled paths is even the right statistic, and
what raising `sample_count` would actually buy.

## Method

The five M2.9 replicates differ only in their RNG stream. So at one origin, the
spread of `predicted_return` across the five **is** the Monte Carlo noise, with
everything else held fixed. And their average is arithmetically a 50-sample
forecast, so its RankIC is what `sample_count = 50` would produce.

That makes both questions answerable from `data/evaluation/m2_9/*_per_origin_metrics.csv.gz`.

## How much of the forecast is Monte Carlo noise

| quantity | value |
|---|---:|
| signal standard deviation | 0.01652 |
| Monte Carlo standard deviation at 10 samples | 0.00930 |
| noise-to-signal ratio | **0.56** |

Attenuation of a rank correlation by estimation noise goes as
`sqrt(s / (s + m))` in variances, giving:

| sample_count | share of the noiseless RankIC |
|---:|---:|
| 10 | **87.1%** |
| 20 | 92.9% |
| 50 | 97.0% |
| 100 | 98.5% |
| 200 | 99.2% |

At the setting every run has used, Monte Carlo noise is costing about **13%** of
the ranking signal. Not nothing, and not the explanation for anything.

## What more samples actually buy, measured

| | RankIC |
|---|---:|
| the five 10-sample replicates | 0.0267, 0.0253, 0.0255, 0.0218, 0.0253 |
| their mean | 0.0249 |
| the 50-sample average | **0.0279** |
| gain | **+0.0030, or +12.2%** |

The measurement lands on the prediction: theory said 87.1% to 97.0%, a gain of
11.4%, and the data gives 12.2%. The noise model is right.

**Five times the compute buys twelve per cent.** The implied ceiling at infinite
samples is `0.0249 / 0.871 = 0.0286`.

That ceiling is the number that matters. On these dates `short_term_reversal`
scores `0.0210`. A Kronos with **no Monte Carlo noise at all** would beat it by
`0.0076`, against a bootstrap half-width near `0.030` at this sample size. The
gate is not close, and no amount of sampling closes it. Raising `sample_count`
is a real improvement to a quantity that would have to roughly triple.

## Is the mean the right statistic

Ranking by the conditional mean is optimal for rank correlation when the
predictive distributions differ only in location. When they differ in shape or
scale it is not, and a statistic that discounts uncertain names can do better.
`interval_width` is a per-origin dispersion, so that family is testable here.

| statistic | RankIC at 50 samples | RankIC at 10 |
|---|---:|---:|
| **mean (incumbent)** | **0.0279** | 0.0249 |
| mean / sqrt(width) | 0.0280 | 0.0251 |
| mean * width | 0.0270 | 0.0270 |
| mean / width | 0.0263 | 0.0241 |
| mean / width^2 | 0.0221 | 0.0215 |
| sign(mean) | 0.0147 | 0.0233 |
| width alone (control) | -0.0023 | |

**The mean is not beaten.** `mean / sqrt(width)` ties it at `0.0280` against
`0.0279`, a difference of `0.0001` against a seed standard deviation of `0.0018`.
`mean * width` looks better at ten samples, `0.0270` against `0.0249`, but worse
at fifty, and the gap is close to one seed standard deviation on 196 dates that
have already been used four times. That is a pattern to distrust, not a finding.

The control explains why. `interval_width` on its own carries a RankIC of
`-0.0023`, indistinguishable from zero, so it holds no directional information
and reweighting by it can only add noise. The location-shift approximation that
makes the mean optimal holds well enough here.

**Limitation.** The per-origin artifact stores the mean and the 10-90 range, not
the samples, so this could not test the median, other quantiles, or
`P(y > cross-sectional median)`. Those need the writer to persist per-sample
terminal returns. That is a cheap change to make before the next run rather than
a reason to delay one.

## What follows

1. **The ranking-statistic question is closed** for the family the data can
   reach. The mean stands. Reopening it needs per-sample output, not a new
   argument.
2. **`sample_count = 50` is not worth 5x compute as a standalone change.** It
   buys 12% of a quantity that needs to triple, and it changes no gate.
3. **Monte Carlo attenuation is close to common across arms** at a fixed
   sampler, so it barely biases a paired comparison; both sides are attenuated
   together. It is a reason to raise `sample_count` for a final confirmatory
   reading, where the 3% residual is paid once, and not for development runs.
4. The M2.11 reading stands but its mechanism is now quantified. Ten samples
   cost 13% of the signal at the incumbent setting; the collapse M2.11 saw at
   the open settings is that same effect at a much larger dispersion.
