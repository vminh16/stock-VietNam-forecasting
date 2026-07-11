---
name: vn-stock-market-radar
description: Use when working in the Stock-VN-Forecasting repo on Kronos model, evaluation, baseline freeze, streaming data, path visualization, ranking, risk radar, or web app tasks that must preserve Vietnam stock-market context, temporal validation, and project invariants.
---

# VN Stock Market Radar

## Overview

This is the repo context harness for turning the current Kronos fine-tuning baseline into a serious Vietnam stock-market research app. It keeps future work anchored to the same product goal, model constraints, metrics, and milestone order.

## First-Read Contract

Before edits, read these files in order:

1. `AGENTS.md`
2. `GEMINI.md`
3. `SPEC.md`
4. Task-relevant docs under `README.md`, `README_VI.md`, `finetune_csv/README.md`, and `reports/`
5. Task-relevant source files

If the task touches frontend design, also use `vn-finance-frontend-taste` and the installed `design-taste-frontend` skill.

## Operating Contract

- Treat the current repo as a baseline first, not a blank slate.
- Do not change Kronos architecture, add prediction heads, or add new losses unless explicitly requested.
- Keep Trend and Risk as business logic over forecast outputs, not as model heads.
- Preserve daily-data assumptions: lookback 126, prediction window 5, temporal split, no random split.
- For multi-stock data, keep one CSV per symbol or equivalent grouping. Never let training windows cross stock boundaries.
- Prefer small milestones with clear success criteria and a verification command.

## Metric Contract

Use a small, stable metric set:

- Forecast quality: `DA`, `MW-DA`
- Ranking quality: `RankIC`, `HitRate@Top10`
- Portfolio sanity: `Sharpe`, `MaxDrawdown`, `ReturnVsBenchmark`
- App operations later: daily success rate, latency, signal stability

Do not expand metric dashboards by default. Add a metric only when it changes a decision.

## Milestone Order

Current preferred order:

1. Milestone 4: repo memory, skill harness, design adapter, context preservation.
2. Milestone 0: freeze and verify baseline.
3. Milestone 1: Kronos Path Viewer for intuitive forecast paths and uncertainty.
4. Milestone 2: focused evaluation harness using the metric contract.
5. Milestone 3: ranking and risk radar over more symbols.
6. Later: streaming, automation, deployment, and end-to-end app hardening.

## References

- Read `references/project-context.md` when starting a new feature, model change, evaluation change, or roadmap discussion.
- Read `references/milestone-map.md` when sequencing work or deciding whether to push back on scope.
- Read `references/pressure-scenarios.md` before revising this skill or validating whether future agents will preserve context.

## Stop Signals

Stop and ask or restate assumptions when a request could mean:

- forecasting exact prices versus ranking relative opportunities,
- investment advice versus research visualization,
- all-market streaming versus a reproducible offline baseline,
- improving the model versus changing the app presentation.
