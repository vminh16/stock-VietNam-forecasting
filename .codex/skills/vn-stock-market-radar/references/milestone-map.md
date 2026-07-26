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

## M1: Point-In-Time Data And Universe

**Status:** Active.

Goal: make the training population scientifically valid before retraining.

Deliverables:

- Stable security identity and listing/status intervals.
- Ragged-history handling with no pre-listing fills.
- Dynamic monthly universe builder.
- Data-quality and scale reports for 50, 150, and 300 symbols.
- Valid-window index that never crosses symbols or invalid gaps.

Verify:

- Historical membership is reproducible at any cutoff.
- Delisted/transferred securities are retained.
- Training origins use only information known at that date.
- Raw sliding windows are not reported as independent sample size.

## M2: Research Evaluation Harness

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
