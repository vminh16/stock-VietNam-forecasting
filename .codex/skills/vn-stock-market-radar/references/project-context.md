# Project Context

## Product Goal

The app should become a Kronos-powered Vietnam Stock Market Radar. The model is the forecasting engine; the app should help a research user inspect forecast paths, uncertainty, ranking, and risk signals across Vietnamese stocks.

The near-term goal is not commercialization. The priority is proving model strength and building an end-to-end app that is technically credible.

## Current Baseline Shape

The current app is naive: it loads a dataset, runs or reads evaluation, caches results, and renders the web UI. Treat this as a baseline to freeze before broader changes.

Milestone 0 freeze target:

- Canonical final artifacts should live under `reports/milestone_0_baseline_freeze/`.
- `reports/milestone_0_baseline_freeze/baseline_freeze_report.md` and `manifest.json` are the first places to check.
- If the report mode is `dev_sampled`, it is a fallback snapshot from existing sampled artifacts, not the canonical final freeze.
- Do not treat fine-tuned v2 as a model improvement unless final `DA` and final `MW-DA` beat zero-shot, or a later report explicitly justifies the tradeoff.

Known technical context from the repo docs:

- Kronos is used for time-series tokenization and forecasting.
- Daily OHLCV-style data is the default operating mode.
- Lookback is 126 trading days.
- Prediction window is 5 trading days.
- Temporal split is required. Random split is invalid for this project.
- Multi-stock training must preserve stock boundaries.

## Repo Anchors

Read these before major changes:

- `README.md` and `README_VI.md` for project framing.
- `SPEC.md` for non-negotiable technical constraints.
- `GEMINI.md` for project-specific operational rules.
- `finetune_csv/README.md` for fine-tuning data format and workflow.
- `reports/walkthrough_finetuning.md` for model training context.
- `reports/walkthrough_evaluation_fix.md` for evaluation caveats and fixes.

## Non-Negotiables

- Do not modify `model/kronos.py` or `model/module.py` unless explicitly requested.
- Do not add Trend or Risk prediction heads.
- Do not add losses for app-facing Trend or Risk labels.
- Derive Trend and Risk from forecast outputs and business logic.
- Do not present output as investment advice.
- Do not optimize for many metrics before the small metric contract is stable.

## Model Objective

The app currently feels ranking-oriented because a market radar naturally compares symbols. The model objective should still be forecast-first:

1. Generate credible short-horizon probabilistic paths.
2. Convert paths into interpretable expected return, trend, and uncertainty features.
3. Use those features for ranking and risk surfaces.

Ranking is the application layer, not proof that the forecast model is good by itself.

The next product phase after baseline freeze is the Kronos Path Viewer: show actual price, stochastic forecast paths, mean/median forecast, confidence band, and uncertainty language before expanding ranking UX.

## Metric Contract

Forecast metrics:

- `DA`: direction accuracy over the forecast horizon.
- `MW-DA`: market-wide direction accuracy aggregated across symbols and dates.

Ranking metrics:

- `RankIC`: correlation between predicted rank signal and realized return rank.
- `HitRate@Top10`: share of top ranked symbols that beat the chosen benchmark or positive-return threshold.

Portfolio sanity metrics:

- `Sharpe`
- `MaxDrawdown`
- `ReturnVsBenchmark`

Only add more metrics when they answer a new decision.
