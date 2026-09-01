# Milestone Map

## Foundation: Context And Skill Harness

Goal: preserve project context before new implementation.

Deliverables:

- Repo-local skill harness for project context.
- Frontend design adapter based on `design-taste-frontend`, adapted for finance dashboards.
- Pressure scenarios for future skill validation.

Verify:

- Skill folders pass `quick_validate.py`.
- `SKILL.md` files have triggering descriptions and no placeholder text.
- Future work follows the active milestone in `SPEC.md`, not speculative streaming.

## M0: Zero-Shot Reference

**Status:** Accepted as a reproducibility reference.

Deliverables:

- Kronos-base zero-shot final metrics and per-date artifacts.
- Data/model/config/command provenance.
- Fine-tuned v2 clearly marked noncanonical because its date coverage differs.

Verify:

- Zero-shot artifacts cover the recorded final dates.
- No mixed-coverage delta is presented as model improvement.
- `DA >= 52` is described as a utility floor, not significance.

## M1: Fixed VN150 Data Foundation

**Status:** Complete.

Goal: make the training population scientifically valid before retraining.

Deliverables:

- Fixed 150-symbol universe contract.
- Immutable raw symbol and index-calendar snapshot.
- Strict segmented data with no missing-value repair.
- Data-quality report for `L={63,126}`, `H=5`.
- Valid-window index that never crosses symbols or invalid gaps.

Verify:

- Snapshot and curated hashes reproduce.
- The fixed-universe survivorship limitation is explicit.
- No model window crosses a symbol or unavailable segment.
- The published manifest contains hashes for 153 raw and 154 curated artifacts.
- Raw sliding windows are not reported as independent sample size.

## M2: Research Evaluation Harness

**Status:** In progress. M2.1 common-origin registry and M2.2 naive references
are complete.

**Completed unit:** M2.1 froze 133,937 origins over 977 dates and 147 symbols
for 2022-2025. Every origin supports both `L={63,126}` at `H=5`; registry SHA256
is `dcd71d14c5016b721111172d6a2ff384122eb74d2cc9c27252d359857e6726c6`.
No 2026 target was opened.

**Completed unit:** M2.2 scored `persistence` and `recent_return_bootstrap` on
those origins with the locked point metrics, ensemble CRPS, and 80% interval
coverage/width. No model inference ran. Evidence is under
`reports/milestone_2_research_eval/naive_references/`.

**Completed unit:** M2.3 implemented the paired stationary date-block bootstrap
and measured design resolution: on 977 paired dates the 95% interval half-width
is 3.79 pp for DA, 6.69 pp for MW-DA, 0.0204 for RankIC. Evidence is under
`reports/milestone_2_research_eval/paired_inference/`.

**Next unit:** M2.4 adds the zero-shot Kronos runner on the same origins and
reuses the existing metric and inference layers. Do not fold training or LoRA
work into that package.

Goal: compare candidates without leakage or metric sprawl.

Deliverables:

- Nested expanding-window folds and final lockbox.
- Unseen-symbol groups.
- Paired identical-origin inference with fixed seeds.
- Date-block confidence intervals.
- Sequential lookback/horizon diagnostics.
- Zero-shot small/base and naive references.

Verify:

- Train targets do not touch validation intervals.
- Final lockbox is not used for tuning.
- Reports include date/symbol/origin counts and regime slices.
- Metric contract remains small and decision-oriented.

## M3: Kronos-Small Adaptation

Goal: determine whether and how Vietnam-domain fine-tuning adds value.

Deliverables:

- Frozen-tokenizer small-model baseline.
- Original CE versus forecast-tail masking/weighting experiment.
- Matched-budget LoRA ablation: Q/V, QKVO, MLP, all-linear.
- Successive-halving experiment ledger with compute usage.
- Full fine-tune challenger only if LoRA underfit gate passes.

Verify:

- Adapter arms have matched trainable-parameter budgets.
- Model comparisons share data, origins, seeds, and evaluation code.
- Improvement repeats across temporal folds and unseen symbols.
- No winner is forced when evidence is insufficient.

## M4: Kronos Path Viewer

Goal: make model evidence visible and honest.

Deliverables:

- Symbol/date selector.
- Actual path, sampled forecasts, median/mean, and interval band.
- Horizon-specific expected return and uncertainty.
- Data-quality, model-version, and freshness indicators.

Verify:

- Viewer reads versioned cached artifacts rather than per-request inference.
- Visuals do not imply certainty.
- Frontend passes the finance design pre-flight checklist.

## M5: Ranking And Risk Radar

Goal: compare the point-in-time eligible universe.

Deliverables:

- Ranked symbol table and filters.
- Expected-return, direction, downside, dispersion, liquidity, and quality decomposition.
- Historical date replay and watchlist.

Verify:

- Ranking can be reconstructed for any evaluation date.
- RankIC and HitRate@Top10 use point-in-time membership.
- UI avoids buy/sell advice language.

## M6: Daily Operations And Deployment

Goal: operate the daily research app reliably.

Deliverables:

- Idempotent scheduled ingestion and batch inference.
- Versioned cache with summary retention and bounded full paths.
- Freshness, retry, partial-failure, and provenance status.
- Deployment and rollback procedure.

Verify:

- User requests do not trigger GPU inference.
- Stale data and failed inference are explicit.
- Every displayed result maps to data/model/universe/config versions.

## Deferred

- Tick-level or intraday prediction.
- Learned ranking heads or learned meta-rankers.
- Brokerage execution and personalized advice.
- Commercialization work before research validity.
