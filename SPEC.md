# SPEC - Vietnam Stock Market Radar with Kronos

> **Version:** 2.6
>
> **Date:** 2026-09-02
>
> **Status:** M2.6 slice harness complete; M2.5 screen cleared no naive gate
>
> **Authority:** Source of truth for product, data, model, evaluation, and delivery decisions

## 0. How To Read This Specification

This repository is an end-to-end research system, not only a model-training
script and not an investment-advice product. The specification separates four
decision states so that hypotheses are not silently promoted into facts.

| State | Meaning |
|---|---|
| **Invariant** | Must not change without explicit user approval and a spec revision |
| **Frozen baseline** | Reproducible historical reference; not necessarily a good model |
| **Research candidate** | Must be tested under the protocol in this document |
| **Deferred** | Intentionally outside the current milestone |

Normative language:

- **MUST** and **MUST NOT** define invariants.
- **SHOULD** defines the default unless evidence justifies an exception.
- **MAY** defines an allowed experiment, not required scope.

When this document conflicts with older project prose, this version supersedes
that prose. `AGENTS.md` remains the immutable behavioral rule for agents.

---

## 1. Product Thesis

### 1.1 Goal

Build a technically credible Vietnam Stock Market Radar powered by Kronos. The
system helps a research user:

1. inspect probabilistic future price paths for one symbol;
2. compare expected opportunity and uncertainty across a point-in-time stock
   universe;
3. rank symbols without hiding data quality, liquidity, or model uncertainty;
4. reproduce every displayed forecast from versioned data, model, and inference
   configuration.

The near-term goal is to demonstrate scientific and engineering validity. The
project is not currently optimized for commercialization.

### 1.2 Product Objective Versus Model Objective

The **application is ranking-oriented**, because a market radar compares many
symbols. The **model remains forecast-first**, because ranking must be derived
from credible forecast distributions rather than an unverified ranking head.

```text
Daily market data
  -> probabilistic Kronos paths
  -> expected return, direction, dispersion, downside, data-quality features
  -> cross-sectional ranking and research UI
```

The Path Viewer is the evidence surface for a symbol. The ranking table is the
navigation and comparison surface for the universe. Neither surface may present
the output as a buy/sell instruction.

### 1.3 Non-Goals

- Intraday or high-frequency trading.
- Guaranteed price targets or personalized investment advice.
- Modifying Kronos architecture before adaptation and data hypotheses are
  exhausted.
- Running model inference independently for every web request.
- Optimizing a large dashboard of metrics without decision purpose.

---

## 2. Immutable Project Invariants

1. **Daily bars only.** Historical intraday data is not sufficiently reliable
   for the current source and product horizon.
2. **Temporal validation only.** Random train/validation/test splits are
   forbidden.
3. **No cross-symbol windows.** A training or evaluation sequence belongs to
   exactly one security.
4. **Point-in-time preprocessing only.** Normalization and preprocessing must
   use information known at the forecast origin. M1 uses an explicitly
   conditional fixed-universe benchmark; it MUST NOT be presented as an
   unbiased historical whole-market backtest.
5. **Kronos architecture remains frozen.** Do not modify `model/kronos.py` or
   `model/module.py`, add neural output heads, or change model topology without
   explicit user approval and a new research design.
6. **Trend and risk remain derived logic.** They are computed from forecast
   paths, not dedicated model heads.
7. **Original token Cross-Entropy remains the loss family.** Position masking
   or weighting is an allowed research candidate only after an explicit
   experiment plan; adding a new loss family is forbidden by default.
8. **Every material output is traceable.** Data version, universe version,
   model checkpoint, configuration, code revision, forecast origin, and random
   seed must be recoverable.

---

## 3. Current Evidence And Baseline

### 3.1 Data Snapshot

The current baseline contains 50 CSV files and approximately 99,851 daily rows
from 2018-06-19 to 2026-06-17. Before 2023 it contains approximately 56,205
valid bars after basic validity checks.

Known quality findings:

- histories have been aligned to a common calendar even when listing histories
  differ;
- SSB contains a concentrated block of 692 missing or zero rows before valid
  history;
- at least one duplicate date exists in the current panel;
- aggregate missing-rate statistics hide symbol-local corruption.

The 50-symbol dataset is a frozen baseline, not the target universe. M1 expands
the development benchmark to a fixed set of 150 symbols selected on 2026-08-09.

### 3.2 Baseline Model Evidence

The canonical usable reference is the Kronos-base zero-shot final run:

| Metric | Test value |
|---|---:|
| DA | 51.6343 |
| MW-DA | 49.0046 |
| RankIC | -0.0026 |
| HitRate@Top10 | 49.7500 |

The former fine-tuned v2 output has different date coverage and is exploratory,
not a canonical comparison. It MUST NOT be used to claim improvement over the
zero-shot reference.

`DA >= 52%` is retained as an operational utility floor. It is not a hypothesis
test and does not replace a confidence interval.

M2.2 evidence sharpens this limitation. On the VN150 common origins, the
`persistence` reference is a permanent down call because `direction(0) = -1`,
and it still reaches `DA = 55.96%` in the falling 2022 fold while carrying zero
forecast information. A DA above the floor is therefore not evidence of skill by
itself; promotion requires MW-DA and RankIC evidence against these references on
identical origins.

M2.3 measured how small a difference this evaluation design can resolve. For two
weakly correlated candidates over 977 paired dates, the 95% paired date-block
interval has a half-width of `3.79` percentage points for DA, `6.69` for MW-DA,
`0.0204` for RankIC, and `2.36` for HitRate@Top10. Fold-level intervals are about
twice as wide. Two consequences are binding:

1. The `DA >= 52%` floor is not decidable against the frozen zero-shot reference
   at `DA = 51.63%`, because the gap is an order of magnitude below resolution.
2. A RankIC improvement smaller than roughly `0.02` cannot be separated from zero
   against a naive reference on this population, which is the same order as a
   realistic equity ranking signal. M3 must therefore pre-register the effect size
   it intends to detect; a smaller true effect requires a larger evaluation
   population or a variance-reduction design, not a louder claim.

Paired difference variance shrinks when candidates are correlated, so a
Kronos-small versus Kronos-base comparison resolves smaller differences than a
model versus naive comparison.

### 3.3 M2.5 Zero-Shot Screen Evidence

Five arms ran on 13,431 common origins over 98 strided dates, ten sample paths
each, `T=0.6`, `top_p=0.9`, seed `20260901`. Pooled results:

| Arm | RankIC | MW-DA | DA | CRPS | 80% coverage |
|---|---:|---:|---:|---:|---:|
| `small_l63` | 0.0013 | 48.23 | 49.89 | 0.02533 | 0.368 |
| `small_l126` | 0.0247 | 50.07 | 50.68 | 0.02555 | 0.400 |
| `small_l63_norm126` | 0.0224 | 49.53 | 50.69 | 0.02549 | 0.383 |
| `base_l63` | 0.0149 | 48.46 | 51.08 | 0.02561 | 0.331 |
| `base_l126` | 0.0267 | 49.18 | 51.87 | 0.02584 | 0.356 |
| `recent_return_bootstrap` | 0.0050 | 50.70 | 49.58 | 0.02387 | 0.689 |

Four findings are binding on later milestones.

1. **No arm cleared the naive gate.** The registered rule required a Kronos arm
   to beat `recent_return_bootstrap` on RankIC with an interval excluding zero.
   The best arm, `base_l126`, reached `+0.0217` with interval
   `[-0.0238, +0.0705]`, so the gate fails. `base_l126` does beat the
   zero-information `persistence` reference at `+0.0267` with interval
   `[+0.0081, +0.0460]`.
2. **The lookback advantage is mostly normalization, not context.** The
   confounded contrast `small_l63` versus `small_l126` gives RankIC `-0.0235`
   with interval `[-0.0461, -0.0016]`. Holding the rows at 63 sessions and only
   borrowing the 126-session normalizer recovers `-0.0211` of that gap, while the
   context-only contrast is `-0.0023` with interval `[-0.0143, +0.0099]`. Each
   component interval still contains zero at 98 dates, so the decomposition is a
   point-estimate result awaiting confirmation, not a proven mechanism.
3. **Small versus base is a dead heat at the incumbent lookback, but
   non-inferiority is not certifiable here.** At `L=126` the RankIC difference is
   `-0.0020` with interval `[-0.0184, +0.0129]`. The registered margin of `0.01`
   sits below the design's resolution at 98 dates, so the test cannot pass
   regardless of model quality. Certifying that margin needs roughly 210 paired
   dates.
4. **Zero-shot Kronos is badly overconfident.** Every arm covers 0.33 to 0.40 of
   realized outcomes inside its nominal 80% band, against 0.689 for the naive
   bootstrap, and every arm has worse CRPS than that naive reference. Probabilistic
   quality is currently a weakness of the model, not a strength.

Cost, measured on one RTX 2050: `base_l126` runs at 1.47 origins per second and
`small_l63` at 9.91, a 6.7x gap, with peak VRAM 0.54 GB against 0.16 GB.

### 3.4 M2.6 Slice Readiness Evidence

M2.6 labelled all 133,937 frozen origins with two pre-registered slice keys and
recomputed the locked metrics inside each slice. It ran no model. The slice table
SHA256 is `8e474264cfc8b16af3dd2b053d9e965cdee2608f625f46556c57cc6aa83bd61b`.

- `liquidity_tier` ranks each date's cross-section by the median traded `amount`
  over the trailing 63 sessions, into three balanced tiers. Median amount is
  133.8M, 36.3M, and 4.4M in tiers 0 to 2, a 30x span. Every tier keeps at least
  42 symbols on every date, so no date is dropped and HitRate@Top10 stays defined
  inside each tier.
- `symbol_group` is a salted-hash partition of `security_id` into five groups of
  30, 27, 24, 27, and 39 symbols. It reads no price, no return, and no result, so
  an unseen-symbol holdout drawn from it cannot be selected after seeing which
  symbols a candidate ranks well. Realized liquidity balance is uneven by chance:
  `group_2` holds 0.181 of its origins in the top tier and `group_1` holds 0.417,
  against 0.333 under a balanced split. A single-group holdout is therefore not a
  representative sample of the population.

One finding sharpens the existing DA warning. The zero-information `persistence`
reference reaches DA 52.87 inside the illiquid `tier_2` against 50.12 in the
liquid `tier_0`, so the `DA >= 52%` utility floor is cleared by a permanent down
call precisely where prices trend down hardest. A slice-level DA above the floor
is even weaker evidence of skill than a pooled one.

M2.5's five Kronos arms cannot be sliced: that run predates the per-origin metric
artifact and kept only per-date aggregates. Slice evidence for a model therefore
begins with the confirmation run.

### 3.5 Baseline Interpretation

- Zero-shot has not demonstrated actionable directional or ranking value.
- The existing fine-tuning procedure has not demonstrated improvement.
- The baseline remains valuable as a reproducibility anchor and falsification
  target.
- Future work must beat naive, zero-shot, and simple statistical baselines under
  identical forecast origins.

---

## 4. Data System Specification

### 4.1 Source And Frequency

The default source remains `vnstock`, with daily OHLCV and provider-reported
turnover when available. Raw provider payloads SHOULD be retained before
transformation. The M1 KBS snapshot has no turnover column, so `amount` is the
deterministic compatibility proxy `volume * mean(OHLC)`, explicitly marked
`derived_ohlc4`. It MUST NOT be described as provider-reported turnover or as
an independent liquidity feature.

Canonical model features are:

```text
open, high, low, close, volume, amount
```

Timestamps MUST map to the official exchange trading calendar. A fixed intraday
time may be attached for model compatibility, but it has no economic meaning.

KBS price values are retained in thousand-VND units. The retained provider
payload does not carry a machine-readable corporate-action adjustment guarantee.
The strict pipeline therefore MUST NOT guess adjustment factors or rewrite
historical OHLC. Transitions with absolute close-to-next-open return above 17%
are audit candidates only; they do not automatically split a segment.

### 4.2 Benchmark Identity

M1 uses a minimal committed mapping of `security_id`, `symbol`, `exchange`, and
`included_as_of`. `security_id` is `<exchange>_<symbol>`. Historical symbol and
exchange event graphs are deferred. Any ambiguous transfer or identity gap is
excluded from valid model windows rather than repaired.

### 4.3 Ragged Histories

Pre-listing time is absence of a security, not a zero-price observation. The M1
strict pipeline distinguishes:

```text
valid
unavailable
pre_history (implicit; no row is materialized)
```

`unavailable` includes missing exchange sessions, invalid OHLC, zero-trade
observations, conflicting duplicates, and gaps whose cause is unknown. Do not
zero-fill, forward-fill, or backward-fill them. Every unavailable observation
splits the contiguous sequence.

For valid contiguous segments of length `ell_is`, symbol `i` contributes:

\[
N_i(L,H)=\sum_s \max(0,\ell_{is}-L-H+1).
\]

### 4.4 Fixed VN150 Benchmark

M1 freezes exactly 150 symbols in `data_pipeline/universe_150.csv`: the current
VN100 constituents, current HNX30 constituents, and 20 reviewed UPCoM stocks as
returned by `vnstock 4.0.4` on 2026-08-09. The composition is a reproducible
development population, not a historical membership reconstruction.

This benchmark MAY support matched comparisons between models on identical
symbols and origins. It MUST NOT support claims that rely on survivorship-free
market membership. Dynamic point-in-time reconstruction, delisted securities,
and historical symbol changes are deferred until such claims are required.

### 4.5 Dataset Scale And Learning Curve

Raw sliding-window count is not sample size. For a date-level score process
`s_t`, temporal effective sample size is estimated by:

\[
N_{eff}\approx\frac{N}{1+2\sum_{k=1}^{K}\rho_s(k)}.
\]

At `L=126`, `H=5`, the baseline has 49,727 nominal train windows, but adjacent
windows overlap almost completely. Dividing by sequence length gives a
conservative non-overlap planning proxy near 377; it is not an ESS estimate.
Actual ESS MUST be estimated from score, loss, label, or gradient-proxy
autocorrelation and cross-sectional dependence.

M1 reports valid bars, contiguous segments, and available windows for the fixed
150-symbol benchmark. Raw window count remains a dependent-observation count,
not an effective sample size.

### 4.6 Sampling

Uniform sampling over all windows overweights long-lived symbols and periods
with many listed stocks. The default research sampler SHOULD choose:

```text
calendar block or regime -> liquidity tier -> eligible symbol -> forecast origin
```

The exact weights must be pre-registered. Sampling must not inspect future
returns or future universe membership.

---

## 5. Model Strategy

### 5.1 Backbone Roles

| Model | Role | Status |
|---|---|---|
| Kronos-base, 102.3M | Frozen zero-shot reference | Frozen baseline |
| Kronos-small, 24.7M | Development and deployment candidate on cost grounds | Research candidate, non-inferiority unproven |
| Full fine-tuned small | Performance-ceiling challenger | Gated candidate |
| Kronos-base fine-tuning | Expensive challenger only | Deferred by default |

Small is not assumed statistically superior because it has fewer parameters.
Pretraining can make a larger model more sample-efficient; the Kronos paper
states that performance improves with size but publishes no quantitative scaling
law, so this remains a hypothesis. Small is preferred operationally only if it
proves non-inferior under matched data, seeds, origins, and compute-aware
evaluation.

Kronos-small is currently a cost-driven choice, not an evidence-backed one. The
published per-size tables separate `Kronos_S`, `Kronos_B`, and `Kronos_L` but
carry no confidence interval, average over nine frequencies, and cannot be split
back to daily. Their price-series RankIC gap from small to base is `0.0254` to
`0.0258`; small beats base on the out-of-distribution XKLS exchange while the one
daily-only comparison favours base. Vietnam is absent from the pretraining
corpus, so VN150 is out-of-distribution at exchange level and no published number
transfers. See `docs/research/2026-09-01-kronos-small-and-window-selection.md`.

### 5.2 Tokenizer Policy

The pretrained `Kronos-Tokenizer-base` is frozen by default. Predictor adapters
must first be evaluated against stable token semantics.

Tokenizer fine-tuning may be reopened only when all conditions hold:

1. reconstruction or utilization diagnostics show a material Vietnam-domain
   mismatch;
2. a compatibility strategy for predictor embeddings and output heads is
   specified;
3. downstream gains, not reconstruction gains alone, repeat across temporal
   folds;
4. codebook utilization and token-distribution drift remain within pre-registered
   limits.

### 5.3 LoRA Mathematics And Candidate Modules

For a frozen weight matrix:

\[
W'=W+\Delta W,\qquad
\Delta W=\frac{\alpha}{r}BA,qquad
\operatorname{rank}(\Delta W)\le r.
\]

Attention is:

\[
Z=\frac{QK^T}{\sqrt d},\quad P=softmax(Z),\quad Y=PVW_O.
\]

Q and K change attention routing, V changes retrieved content, O changes head
mixing, and the SwiGLU MLP changes nonlinear feature transformation. Therefore
Q/V-only LoRA is a reasonable baseline but not a theorem or default winner.

The first controlled Kronos-small adapter ablation MUST match the trainable
parameter budget. Including eight self-attention blocks and the dependency-aware
attention layer, each arm below has approximately 147,456 parameters:

| Arm | Rank | Target modules |
|---|---:|---|
| A | 8 | Q, V |
| B | 4 | Q, K, V, O |
| C | 4 | MLP `w1`, `w2`, `w3` |
| D | 2 | Q, K, V, O and MLP |

Only after identifying whether failure comes from adapter rank or module coverage
may rank 4/8/16 be explored for the winning module family.

### 5.4 Full Fine-Tuning Gate

Full fine-tuning Kronos-small is not the first experiment. It is allowed only if:

- broad LoRA improves both train and validation performance when rank increases,
  indicating bias rather than variance;
- the gain persists across multiple walk-forward folds and seeds;
- optimizer settings are independently designed for full fine-tuning;
- the expected gain justifies compute and deployment cost.

If full fine-tuning lowers train loss but does not improve paired out-of-sample
metrics, LoRA is considered beneficial regularization.

---

## 6. Forecast Target, Lookback, And Horizon

### 6.1 Conditional Forecast

For symbol `i` and forecast origin `t`, the model approximates:

\[
p_\theta(z_{t+1:t+H}\mid z_{t-L+1:t})
=\prod_{h=1}^{H}p_\theta(z_{t+h}\mid z_{t-L+1:t+h-1}).
\]

`L=126`, `H=5` is the incumbent baseline, not an invariant and not a proven
optimum.

### 6.2 Candidate Grid

The next pre-registered comparison is:

```text
Lookback L: 63, 126
Horizon H: 5
```

`L=126` is the incumbent by history only. A primary-source review
(`docs/research/2026-09-01-kronos-small-and-window-selection.md`) found that every
daily-frequency lookback the Kronos authors published falls in 40-96 bars, which
leaves `L=126` outside their published range and `L=63` inside it. `L=63` is also
only about `2.05x` cheaper, not `4x`. Neither value is the selected winner until
both are evaluated on identical temporal folds, and the comparison carries the
normalization confound recorded in section 6.3.

### 6.3 Statistical Trade-Off

For cumulative log return:

\[
R_{t,h}=\sum_{j=1}^{h}r_{t+j}.
\]

Under independent innovations,
`Var(R_{t,h})=h sigma^2`, so uncertainty width grows approximately with
`sqrt(h)`. Serial correlation, regime changes, and recursive model error can
increase it further.

M2.4 measured the departure from that i.i.d. baseline on VN150. Per-symbol
variance ratios at `q=5` have fold medians of `1.145` for 2022, `0.951` for
2023, `0.946` for 2024, and `1.007` for 2025. The sign of the departure is
regime-linked rather than stable: 2022 is trending, where 32.4% of symbols reject
the random walk upward at `q=2`, while 2024 is mildly mean-reverting. Low-liquidity
symbols mean-revert more than high-liquidity symbols. The `sqrt(h)` rule is
therefore an acceptable average approximation with a regime-dependent error of
roughly 5% to 15% at `H=5`, not an invariant.

Longer lookback can reduce truncation bias when older observations contain
incremental information, but it also:

- reduces valid windows; measured on VN150 this is `-7.4%` (247,999 to 229,734)
  and exactly zero inside the M2.1 common-origin registry, not a linear cost;
- increases attention compute as `O(L^2)` asymptotically, but at `L <= 126` the
  quadratic term is a small share of total cost and `63 -> 126` measures near
  `2.05x`, not `4x`;
- mixes stale regimes with the current state;
- increases sensitivity to short listing histories;
- changes the normalization window, because `L` sets both the context and the
  point-in-time scaling (`data_pipeline/transforms.py`, `model/kronos.py`).

That last item is not a detail. M2.4 measured that moving the normalizer from 126
to 63 sessions rescales the price channels by a median factor of `1.364` and
shifts their window means by `0.572` long-window scale units, while volume
channels move only to `0.974`. An `L=63` versus `L=126` comparison therefore
measures `context + normalization`, concentrated in the channels the forecast
depends on. Any lookback conclusion MUST be reported with that compound label, or
the experiment MUST add a third arm that holds the normalizer fixed.

### 6.4 Selection Rule

Do not run the full Cartesian product through expensive training.

1. Define the product holding horizon and evaluation utility before opening the
   final holdout.
2. Use zero-shot or low-budget diagnostics to compare horizon prefixes.
3. Lock `H` on inner validation.
4. Select `L` for that `H` using the one-standard-error rule: choose the shortest
   context statistically indistinguishable from the best.
5. Keep the final holdout closed until adapter and data choices are fixed.

T+2 constrains feasible trading logic. It does not mathematically prove that
five sessions is the most predictable horizon.

---

## 7. Training Objective And Optimization

### 7.1 Objective Alignment Risk

The current predictor sequence contains `L+H+1` tokens and computes next-token
Cross-Entropy over `L+H` transitions. At `L=126`, `H=5`, only:

\[
\frac{5}{131}=3.82\%
\]

of loss positions correspond to the forecast tail used by downstream
evaluation. The remaining positions primarily reconstruct transitions inside
the observed history.

Before expensive adaptation, compare three uses of the same S1+S2 Cross-Entropy:

1. original all-position CE;
2. forecast-tail-only masked CE;
3. mixed CE with a pre-registered larger forecast-tail weight.

This experiment changes training behavior but does not add a new model head or
loss family. It requires its own implementation plan and tests before code is
changed.

### 7.2 Training Diagnostics

Every adaptation run records:

- train and validation token NLL;
- gradient norm and learning-rate history;
- selected adapter modules and exact trainable parameter count;
- wall-clock time, peak VRAM, optimizer steps, and examples processed;
- fixed-seed downstream validation metrics.

Early stopping MUST NOT use a small, repeatedly inspected DA sample. Prefer
validation token NLL for optimization stability and a date-aggregated downstream
metric with fixed origins for model selection.

### 7.3 Compute-Aware Search

Use conservative successive halving:

1. **Screen:** 10% optimizer budget, two predeclared temporal folds, two seeds.
2. **Promote:** 30% budget, at least three folds, three seeds.
3. **Confirm:** full budget for at most two finalists.
4. **Lockbox:** final untouched period, opened once.

Budget comparisons SHOULD report both fixed optimizer steps and convergence
behavior. A larger model must not be eliminated solely because it learns more
slowly during the first few steps.

---

## 8. Evaluation Contract

### 8.1 Validation Design

Use nested expanding-window validation. Initial outer folds are:

```text
Train through 2021 -> evaluate 2022
Train through 2022 -> evaluate 2023
Train through 2023 -> evaluate 2024
Train through 2024 -> evaluate 2025
Locked final period -> 2026 H1 or the latest untouched equivalent
```

Requirements:

- build windows after assigning temporal partitions;
- purge any train origin whose target interval touches validation;
- fit normalization and preprocessing on training information only;
- use identical dates, eligible symbols, Monte Carlo seeds, and sample counts
  for paired model comparisons;
- maintain a stratified unseen-symbol holdout across sector, exchange,
  liquidity, and listing age.

### 8.2 Locked Metric Definitions

Milestone 0 locks four deterministic point metrics. Their names and definitions
must not change silently between model runs.

For symbol `i`, forecast origin `t`, and selected horizon `H`, define realized
and predicted cumulative returns as `r_i,t,H` and `rhat_i,t,H`.
To preserve the frozen implementation, define
`direction(x)=+1` when `x>0` and `direction(x)=-1` otherwise. Zero return is
therefore treated as non-positive; changing this convention creates a new
metric version.

**Directional Accuracy**

\[
DA_H=\frac{1}{|\mathcal O_H|}
\sum_{(i,t)\in\mathcal O_H}
\mathbf 1[direction(\hat r_{i,t,H})=direction(r_{i,t,H})].
\]

**Magnitude-Weighted Directional Accuracy**

\[
MWDA_H=
\frac{\sum_{(i,t)}|r_{i,t,H}|
\mathbf 1[direction(\hat r)=direction(r)]}
{\sum_{(i,t)}|r_{i,t,H}|}.
\]

**Daily RankIC**

\[
RankIC_{t,H}=
\rho_{\text{Spearman},i}(\hat r_{i,t,H},r_{i,t,H}),
\qquad
\overline{RankIC}_H=\frac{1}{T}\sum_t RankIC_{t,H}.
\]

**HitRate@Top10**

\[
HitRate@Top10_H=
\frac{1}{10T}\sum_t\sum_{i\in Top10_t}
\mathbf 1[r_{i,t,H}>0].
\]

`Top10` always means ten symbols, not top 20 percent. A date is invalid for this
metric when fewer than ten eligible symbols remain after point-in-time filters.
Metric implementations must report their horizon, number of valid dates, number
of symbols, eligible-origin count, and aggregation unit.

### 8.3 Metric Maturity By Phase

The metric set is stable enough to freeze the historical baseline, but the
statistical harness is not yet complete.

| Level | Metrics and evidence | Purpose | Required by |
|---|---|---|---|
| Baseline core | DA, MW-DA, RankIC, HitRate@Top10, artifact hashes, date coverage | Reproduce and name M0 | Complete |
| Research comparison | Core metrics plus paired date-block confidence intervals, CRPS, interval coverage/width | Select data, horizon, backbone, and adaptation | M2 before model promotion |
| Product sanity | RankIC, HitRate@Top10, Sharpe, MaxDrawdown with frozen costs and turnover | Validate radar behavior | M5 |
| Operations | freshness, daily success rate, latency, cache hit rate, signal stability | Operate the app | M6 |

The current paired t-test output in `evaluation/inference_pipeline.py` is
diagnostic only. It is not canonical evidence because overlapping horizons and
market-wide dependence violate independent-date assumptions. M2.3 replaced it
with `evaluation/research/bootstrap.py`: a paired stationary date-block
bootstrap with an expected block of ten forecast dates, 5,000 replicates, and a
registered seed. Ratio metrics are recomputed from resampled numerator and
denominator sums inside each replicate, and both candidates share one resampled
date index.

### 8.4 Small Metric Contract

Metrics are grouped by the decision they support.

| Decision | Primary | Secondary |
|---|---|---|
| Forecast direction | MW-DA | DA |
| Cross-sectional ranking | RankIC | HitRate@Top10 |
| Probabilistic path | CRPS | interval coverage and width |
| Portfolio sanity, later | Sharpe | MaxDrawdown |

The app is ranking-oriented, so RankIC is the primary product metric. Model
acceptance remains forecast-gated: a ranking gain is not accepted if forecast
direction or calibration degrades beyond a pre-registered non-inferiority bound.

Portfolio metrics are not model-selection metrics until transaction costs,
turnover, universe policy, and benchmark are frozen.

### 8.5 Statistical Inference

Overlapping horizons and shared market factors invalidate independent-window
tests. Aggregate metrics by forecast date and compare models with paired moving
or stationary block bootstrap, retaining the entire cross-section in each date
block.

Report:

- point estimate;
- confidence interval for paired difference versus zero-shot and naive;
- performance by market regime and liquidity tier;
- seen-symbol and unseen-symbol results;
- number of dates, symbols, and valid forecast origins.

If the interval includes no meaningful improvement, the correct conclusion is
"insufficient evidence", not "the fine-tuned model wins".

### 8.6 Pre-Registered M2.5 Screen Rule

Registered on 2026-09-01, before any screen result existed. The screen ranks
candidates for a later confirmation run; it MUST NOT promote a model.

Arms: `small_l63`, `small_l126`, `small_l63_norm126`, `base_l63`, `base_l126`,
on 98 strided dates from the frozen common origins, ten sample paths per origin,
`T=0.6`, `top_p=0.9`, seed `20260901`.

Reading rule, applied to paired date-block intervals at 95%:

1. `small_l63` versus `small_l63_norm126` isolates the normalizer, because the
   two arms see identical rows and differ only in scaling.
2. `small_l63_norm126` versus `small_l126` isolates context length, because the
   two arms share a normalizer and differ only in how many sessions the model
   reads.
3. `small_l63` versus `small_l126` is the confounded contrast. If its interval
   disagrees in sign with rule 2, the lookback question is decided by
   normalization rather than by context, and SPEC section 6.2 must say so.
4. Backbone size is read from `small_l63` versus `base_l63` and `small_l126`
   versus `base_l126`. Kronos-small survives as the development candidate when
   the RankIC paired lower bound exceeds `-0.01` and the MW-DA paired lower bound
   exceeds `-1.0` percentage point at the same lookback.
5. Every Kronos arm must beat `recent_return_bootstrap` on RankIC with an
   interval excluding zero before any arm is called useful. Failing this is a
   valid and reportable outcome.

No threshold in this subsection may be changed after the screen is read. A
changed threshold requires a new registration and a new run.

### 8.7 Registered Evaluation Slices

Two slice keys are registered. Both are assigned by
`evaluation/run_origin_slices.py` from the frozen origin registry alone, before
any metric is computed, and both are recorded with a hash in the M2.6 manifest.

- `liquidity_tier`: three tiers, assigned inside each evaluation date by the
  median traded `amount` over the trailing 63 sessions, `tier_0` most liquid.
  Assignment is point-in-time and reads no session after the origin.
- `symbol_group`: five groups, a salted hash of `security_id` with salt
  `vn150-strict-v2-m2-holdout`. It MUST NOT depend on prices, returns, or
  results.

Rules:

1. Any evaluation that reports slice metrics MUST persist per-origin metrics.
   A run that keeps only per-date aggregates cannot be sliced afterwards and MUST
   NOT have slice claims attached to it later.
2. Slice metrics are recomputed from per-origin rows inside the slice. A slice
   `RankIC` is the cross-sectional correlation among that slice's symbols only,
   and a slice `HitRate@Top10` selects that slice's top ten, not the market's.
3. A date holding fewer than ten origins inside a slice is dropped from that
   slice only. Both sides of a paired comparison share origins, so they drop the
   same dates and stay paired.
4. Slicing multiplies comparisons. The slice list and the metric read from it
   MUST be registered before the run, and section 8.8 applies to the resulting
   family. Searching slices after seeing a pooled result is data snooping.
5. An unseen-symbol holdout MUST name its `symbol_group` values in the
   registration, and MUST report the group's realized liquidity composition from
   section 3.4, because the hash split is not liquidity-balanced.

### 8.8 Multiple Comparisons

The grid, primary metric, promotion rule, and non-inferiority bound must be
registered before evaluation. If many candidates are inspected, use a Model
Confidence Set, SPA, or an equivalent bootstrap correction. Do not select a
configuration by repeatedly viewing the final period.

---

## 9. Inference, Ranking, And Risk

### 9.1 Forecast Artifact

For each `(model_version, data_version, universe_version, symbol,
forecast_origin, L, H, sampling_config)`, the system produces a versioned
artifact containing:

- actual input path and normalization metadata;
- stochastic forecast paths or a reproducible reference to them;
- mean and median path;
- selected quantiles and interval coverage target;
- expected cumulative returns at supported horizons;
- data-quality and eligibility flags.

### 9.2 Ranking

Ranking is derived from forecast artifacts. The first ranking score SHOULD be a
simple, inspectable function of expected return and uncertainty. Do not add a
learned meta-ranker until the underlying forecast passes acceptance gates.

Every ranked row must expose enough components to explain its position:

```text
expected return, direction probability, downside quantile,
forecast dispersion, liquidity tier, data-quality status
```

### 9.3 Risk Semantics

Stochastic Kronos paths approximate conditional sampling uncertainty. They do
not automatically capture parameter uncertainty, model misspecification, or
regime shift. UI text must therefore use terms such as `forecast interval` or
`model dispersion`, not guaranteed confidence.

Trend and risk thresholds are business rules, versioned separately from model
checkpoints.

---

## 10. End-To-End Architecture

```text
Daily ingestion
  -> immutable raw snapshots
  -> point-in-time curated bars and security master
  -> eligible universe and valid-window index
  -> versioned training/evaluation datasets
  -> model registry and experiment artifacts
  -> scheduled batch inference
  -> forecast cache
  -> API
  -> Path Viewer and Market Radar
```

### 10.1 Streaming Meaning

For this daily product, "streaming" means a continuously operated event-driven
pipeline around daily market updates, not tick-level prediction. The pipeline
must be idempotent and expose freshness, partial failure, retry, and provenance.

### 10.2 Cache And Scaling

MVP serving is cache-first. User requests read immutable forecast artifacts;
they do not trigger GPU inference.

Cache keys MUST include model, data, universe, symbol, origin, horizon, and
sampling versions. To control storage:

- retain summary quantiles and path statistics for the whole universe;
- retain full sampled paths only for a bounded recent period or selected audit
  cases;
- deduplicate shared input metadata;
- expire artifacts by policy, never by ambiguous filename overwrite;
- invalidate by version change rather than mutating cached results.

### 10.3 Failure Visibility

The app must distinguish stale data, ineligible symbol, failed inference,
insufficient history, and valid low-confidence prediction. Silent fallback to an
older model or stale forecast is forbidden.

---

## 11. Long-Term Delivery Plan

The roadmap is dependency-driven, not a promise of calendar dates. A later
milestone may start only when its predecessor's exit gate is evidenced by
versioned artifacts. Research failure is a valid exit when it is documented.

### 11.1 Planning Horizons

| Horizon | Milestones | Objective |
|---|---|---|
| **Now: scientific foundation** | M0-M2 | Freeze the reference, repair the data population, and make comparisons statistically valid |
| **Next: model research** | M3 | Determine whether Kronos-small adaptation adds repeatable value |
| **Then: product validation** | M4-M5 | Expose forecast evidence and turn it into an explainable market radar |
| **Later: operations** | M6 | Run daily ingestion, inference, caching, monitoring, and deployment reliably |

### 11.2 Status And Dependency Map

| Milestone | Status | Depends on | Exit artifact |
|---|---|---|---|
| M0 Baseline Reference | **Complete** | Context harness | `manifest.json` and zero-shot freeze report |
| M1 Data And Universe Foundation | **Complete** | M0 | Fixed VN150 snapshot, strict curated data, manifest, data-quality report |
| M1.1 Data Readiness Closure | **Conditional complete** | M1 | `vn150_strict_v2` readiness report and preprocessing contract |
| M2 Research Evaluation Harness | **In progress (M2.1 complete)** | M1 | Versioned folds, common-origin evaluation, block-bootstrap report |
| M3 Small-Model Adaptation | Planned | M2 | Experiment ledger and promoted model or documented no-improvement result |
| M4 Kronos Path Viewer | Planned | Stable M2 artifact schema | Reproducible cached path visualization |
| M5 Ranking And Risk Radar | Planned | M3 decision and M4 | Point-in-time ranking replay and metric report |
| M6 Daily Operations And Deployment | Deferred | M4-M5 | Idempotent daily run, monitoring, cache lifecycle, deployment record |

### 11.3 Milestone Definitions

Each milestone is small, falsifiable, and produces a usable artifact.

### M0 - Baseline Reference

**Status:** Complete. Zero-shot reference is frozen; old fine-tuned v2 is
noncanonical.

Success: zero-shot metrics, commands, dates, configs, and artifacts are
traceable. No claim is made that the baseline is useful.

### M1 - Data And Universe Foundation

Build an immutable VN150 raw snapshot, index-derived exchange calendars, strict
segmented curated data, and a dataset audit. Preserve the legacy M0 loader and
artifacts separately.

Success: exactly 150 symbols are accounted for, no imputation or cross-segment
windows exist, a repeated build reproduces hashes, and reports cover `63/5` and
`126/5` before training.

### M1.1 - Data Readiness Closure

**Status:** Conditional complete. `vn150_strict_v2` has no structural blocker
for M2 evaluation: no duplicate symbol-session keys, non-finite features,
invalid curated OHLC, timestamp violations, or session gaps inside segments.
Normalization is a shared lookback-only transform. Nineteen returns above 17%
remain unchanged and are listed for review.

The conditions are material: provider price adjustment semantics are unverified,
and `amount` is a deterministic OHLC4 compatibility proxy. M2 zero-shot
evaluation may proceed. M3 adaptation MUST preserve these limitations and must
not claim corporate-action-adjusted training data without new source evidence.

### M2 - Research Evaluation Harness

**Status:** In progress. M2.1 froze 133,937 common symbol-origins over 977
dates and 147 symbols for 2022-2025. Every row supports both `L={63,126}` at
`H=5`; the 2026 lockbox remains unopened. M2.2 evaluated the two causal naive
references on those origins with locked point metrics, ensemble CRPS, and 80%
interval diagnostics; no model inference was performed. M2.3 replaced the
diagnostic paired t-test with the canonical paired stationary date-block
bootstrap and measured the design's resolution. M2.4 ran two training-free data
diagnostics: variance ratios on VN150 daily returns and a normalization-confound
measurement for the lookback grid. M2.5 screened five zero-shot arms on 98
strided dates; no arm cleared the registered naive gate. M2.6 registered the two
evaluation slice keys of section 8.7, made every runner persist per-origin
metrics, and recomputed the naive references inside each slice.

Remaining before M2 can close: a confirmation run on roughly 210 paired dates
with at least two seeds, an unseen-symbol holdout drawn from the registered
`symbol_group` values, and slice evidence for the Kronos arms, which the M2.5
run cannot supply because it kept no per-origin metrics.

Success: zero-shot small/base and naive baselines are comparable on identical
origins without opening the final lockbox.

### M3 - Small-Model Adaptation

Test forecast-aligned CE variants and matched-budget LoRA arms on Kronos-small.
Use successive halving; full fine-tuning remains gated.

Success: a candidate either demonstrates repeatable improvement or the project
records that fine-tuning is not yet justified.

### M4 - Kronos Path Viewer

Visualize actual history, sampled forecasts, median path, interval band, and
uncertainty/data-quality language from cached artifacts.

Success: the chart is reproducible, visually honest, responsive, and does not
imply certainty.

### M5 - Ranking And Risk Radar

Add point-in-time ranking, decomposition, liquidity/data flags, filters, and
watchlists.

Success: ranking is backtestable by date and explainable from forecast outputs.

### M6 - Daily Operations And Deployment

Add scheduled ingestion, batch inference, cache lifecycle, status monitoring,
and deployment hardening.

Success: daily runs are idempotent, failures are visible, and every served result
is traceable.

Commercialization, brokerage integration, and personalized advice remain
deferred.

### 11.4 Roadmap Governance

At the end of every milestone:

1. freeze the data, universe, model, config, code revision, command, metrics,
   and artifact hashes used for its decision;
2. update the milestone status and decision table in this specification;
3. record failed hypotheses as evidence rather than deleting them;
4. verify that no final lockbox was reused for tuning;
5. create the next milestone implementation plan only after the current exit
   gate is satisfied.

Changes to metric definitions, universe policy, horizon, or model acceptance
rules require a SPEC version increment. Regenerating an artifact without a
semantic change does not.

---

## 12. Decision Gates

| Decision | Required evidence |
|---|---|
| Accept VN150 data foundation | Complete snapshot, deterministic hashes, strict valid segments, and explicit survivorship limitation |
| Select small over base | Small is inside pre-registered non-inferiority bound and materially cheaper |
| Select LoRA module family | Matched-parameter ablation with paired date-block intervals |
| Increase LoRA rank | Train and validation both improve; not train loss alone |
| Fine-tune tokenizer | Reconstruction mismatch plus repeated downstream benefit and compatibility plan |
| Full fine-tune small | Broad LoRA remains demonstrably biased/underfit and full FT improves OOS |
| Keep `L=126` | It belongs to the confidence set and shorter contexts do not match it at lower cost |
| Keep `H=5` | It matches predeclared product utility and is not dominated by another feasible horizon |
| Promote a model | Beats zero-shot and naive within statistical and practical bounds; no severe regime or calibration failure |

No experiment is required to produce a winner. Keeping zero-shot or stopping
fine-tuning is a valid result.

---

## 13. Known Risks

1. **Survivorship bias:** current constituents backfilled through history create
   unrealistic training and evaluation.
2. **Dependence and pseudo-replication:** overlapping windows and market-wide
   factors make nominal sample counts misleading.
3. **Non-stationarity:** policy, market-access, liquidity, and participant mix
   change over time.
4. **Objective mismatch:** token NLL can improve without ranking or directional
   usefulness.
5. **Tokenizer semantic drift:** changing tokenization can invalidate predictor
   embeddings and output semantics.
6. **Monte Carlo noise:** small sample counts can make model comparisons unstable.
7. **Data snooping:** repeated tuning against the same recent period creates
   optimistic results.
8. **False uncertainty:** sampled paths omit important epistemic and distribution
   shift uncertainty.
9. **Operational staleness:** cached predictions can appear valid after failed
   ingestion unless freshness is explicit.

---

## 14. Primary Research References

- [Kronos paper](https://arxiv.org/abs/2508.02739) and
  [official repository](https://github.com/shiyu-coder/Kronos)
- [LoRA](https://arxiv.org/abs/2106.09685)
- [Intrinsic dimension of fine-tuning](https://arxiv.org/abs/2012.13255)
- [Scaling laws for transfer](https://arxiv.org/abs/2102.01293)
- [Time-series foundation model scaling and diversity](https://arxiv.org/abs/2410.12360)
- [Domain adaptation discrepancy bounds](https://arxiv.org/abs/0902.3430)
- [Hansen-Hodrick inference for overlapping forecasts](https://doi.org/10.1086/260910)
- [Stationary bootstrap](https://doi.org/10.1080/01621459.1994.10476870)
- [Proper probabilistic scoring rules](https://doi.org/10.1198/016214506000001437)
- [White Reality Check](https://doi.org/10.1111/1468-0262.00152) and
  [Hansen SPA](https://doi.org/10.1198/073500105000000063)

---

## 15. Definition Of Project Success

The project succeeds when it produces an end-to-end, reproducible research app
whose forecasts and rankings survive point-in-time, walk-forward, unseen-symbol,
and uncertainty-aware evaluation. Success does not require beating the market.
It requires knowing, with defensible evidence, what the model can and cannot do,
and serving that evidence without overstating certainty.
