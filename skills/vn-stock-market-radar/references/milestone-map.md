# Milestone Map

## Milestone 4: Context And Skill Harness

Goal: preserve project context before new implementation.

Deliverables:

- Repo-local skill harness for project context.
- Frontend design adapter based on `design-taste-frontend`, adapted for finance dashboards.
- Pressure scenarios for future skill validation.

Verify:

- Skill folders pass `quick_validate.py`.
- `SKILL.md` files have triggering descriptions and no placeholder text.
- Future plan starts from Milestone 0, not from speculative streaming.

## Milestone 0: Baseline Freeze

Goal: make the current baseline reproducible and named before changing behavior.

Deliverables:

- One baseline command or script that reproduces current evaluation outputs.
- A frozen baseline artifact containing data version, model checkpoint, command, metrics, and generated report paths.
- A short baseline report describing what is credible and what is weak.

Verify:

- Baseline command runs from a clean shell.
- Output files are deterministic enough to compare.
- Metrics use the small metric contract.
- `reports/milestone_0_baseline_freeze/baseline_freeze_report.md` records whether the run is canonical `final` or fallback `dev_sampled`.
- If only `dev_sampled` exists, do not mark Milestone 0 fully closed. Keep canonical final evaluation as the remaining gate.

## Milestone 1: Kronos Path Viewer

Goal: make model behavior visible.

Deliverables:

- Symbol/date selector.
- Actual price path plus Kronos sampled forecast paths.
- Mean or median forecast line.
- Confidence band or quantile band.
- Simple derived trend and risk explanation.

Verify:

- Viewer works for at least one known symbol and date.
- Chart does not imply certainty.
- Frontend passes the finance design pre-flight checklist.

## Milestone 2: Focused Evaluation Harness

Goal: evaluate forecast and ranking usefulness without metric sprawl.

Deliverables:

- Walk-forward or temporal evaluation command.
- Forecast metrics: `DA`, `MW-DA`.
- Ranking metrics: `RankIC`, `HitRate@Top10`.
- Optional portfolio sanity metrics only after ranking metrics are stable.

Verify:

- Windows do not cross symbol boundaries.
- No look-ahead leakage.
- Reports are generated from artifacts, not hand-edited values.

## Milestone 3: Ranking And Risk Radar

Goal: use forecast outputs to compare symbols.

Deliverables:

- Ranked symbol table.
- Signal decomposition: expected return, confidence, downside risk, liquidity/data quality flags.
- Watchlist and filters.

Verify:

- Ranking can be backtested by date.
- Top symbols are explainable from forecast path features.
- UI avoids buy/sell advice language.

## Later: Streaming And Deployment

Goal: turn the research app into an operational app.

Deliverables:

- Data ingestion scheduler or stream adapter.
- Symbol universe management.
- Cache invalidation and daily refresh status.
- Deployment plan.

Verify:

- Daily run succeeds without manual intervention.
- Failed data refreshes are visible in the UI.
- Live outputs are traceable to model and data versions.
