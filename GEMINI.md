# GEMINI.md - Agent Instructions for Stock-VN-Forecasting

> This file is the operational companion to `SPEC.md`. Read `AGENTS.md` first,
> then this file, then `SPEC.md`, as required by the repository first-read rule.
> `SPEC.md` is the source of truth for product, data, model, evaluation, and
> milestone decisions.

## Project Identity

Stock-VN-Forecasting is an end-to-end Vietnam Stock Market Radar built around
Kronos. The model generates probabilistic daily paths; the application derives
interpretable ranking and risk features from those paths.

The project is research-first. It does not provide investment advice and is not
currently optimized for commercialization.

## Decision States

Do not treat every number in the repository as fixed.

- **Invariant:** requires explicit user approval and a spec revision.
- **Frozen baseline:** reproducible historical reference, not a quality claim.
- **Research candidate:** must pass the protocol in `SPEC.md`.
- **Deferred:** outside the current milestone.

Current incumbents `lookback=126`, `horizon=5`, Kronos-base, 50 symbols, and
Q/V LoRA rank 8 are baselines or candidates. They are not proven optima.

## Technical Stack

- Python 3.10+
- PyTorch
- Daily data from `vnstock`
- pandas, numpy, scipy, PyYAML, huggingface_hub
- Single GPU or `torchrun` multi-GPU

## Invariants

1. Use daily bars only.
2. Use temporal or nested walk-forward validation; never random time-series
   splits.
3. Keep windows inside one security.
4. Use point-in-time universe and preprocessing information.
5. Do not modify `model/kronos.py` or `model/module.py` unless explicitly
   instructed.
6. Do not add prediction heads or new loss families by default.
7. Derive Trend, ranking, and Risk from forecast outputs and business logic.
8. Keep every output traceable to data, universe, model, config, code revision,
   origin, and seed.

The original S1+S2 Cross-Entropy remains the loss family. Forecast-position
masking or weighting is a research candidate, not permission to implement it
without a reviewed experiment plan.

## Current Research Direction

- Kronos-base is the frozen zero-shot reference.
- Kronos-small is the primary adaptation and deployment candidate.
- Freeze the pretrained tokenizer for the first small-model experiments.
- Compare LoRA target modules at equal trainable-parameter budget.
- Gate full fine-tuning behind evidence that broad LoRA is underfitting.
- Expand data through dynamic point-in-time universes at 50, 150, and 300
  symbols; do not backfill today's constituents through history.
- Treat `L in {40, 63, 126, 252}` and `H in {3, 5, 10, 20}` as a sequential
  research grid, not a full expensive Cartesian sweep.

## Data Contract

Each security must remain separately grouped, preferably one CSV per symbol.
Canonical columns are:

```csv
timestamps,open,close,high,low,volume,amount
2024/01/02 9:00,30500,31000,31200,30200,1500000,46500000000
```

Model feature order is `[open, high, low, close, volume, amount]`.

Do not zero-fill or forward-fill pre-listing history. Distinguish pre-listing,
provider missing, no-trade, suspended/restricted, and valid sessions. Preserve
delisted and transferred securities to control survivorship bias.

## Evaluation Contract

Use a small metric set tied to decisions:

- Forecast direction: `MW-DA`, `DA`
- Ranking: `RankIC`, `HitRate@Top10`
- Probabilistic path: `CRPS`, interval coverage/width
- Portfolio sanity later: `Sharpe`, `MaxDrawdown`

The app is ranking-oriented, so `RankIC` is the primary product metric. A model
must still pass forecast and calibration guardrails. `DA >= 52%` is a utility
floor, not statistical significance.

Compare models on identical dates, symbols, origins, sample counts, and seeds.
Use paired date-block inference because overlapping horizons and common market
factors invalidate independent-window tests.

M0 locks the four point metrics and provenance only. Before promoting a new
model, M2 must add paired date-block confidence intervals plus CRPS and interval
coverage/width. The current paired t-test output is diagnostic, not canonical.

## Baseline Status

- M0 is closed with zero-shot Kronos-base final as the accepted reference.
- The former fine-tuned v2 result has mismatched date coverage and is
  noncanonical.
- Do not claim fine-tuning improvement from the mixed-coverage report.
- M1 data/universe foundation is active, followed by the research
  evaluation harness and small-model adaptation.

## Commands

```powershell
# Unit tests
$env:PYTHONPATH='finetune_csv'; python -m pytest tests -q

# Frozen zero-shot evaluation
python evaluation/inference_pipeline.py --config evaluation/configs/milestone0_baseline_zero_shot.yaml --mode final

# Current predictor training entry point; config remains an incumbent baseline
python finetune_csv/finetune_base_model.py --config finetune_csv/configs/vn50.yaml
```

Do not run expensive training until the experiment has a pre-registered data
version, folds, candidates, budget, promotion rule, and acceptance criterion.

## Coding Discipline

- Follow `AGENTS.md` without exception.
- Make the smallest change that satisfies the active milestone.
- Do not refactor adjacent code or remove pre-existing dead code.
- Use tests before implementation for behavior changes.
- Preserve user changes in a dirty worktree.
- State assumptions and stop when requirements are genuinely ambiguous.

## First-Read References

- `SPEC.md`
- `.codex/skills/vn-stock-market-radar/references/project-context.md`
- `.codex/skills/vn-stock-market-radar/references/milestone-map.md`
- `reports/milestone_0_baseline_freeze/baseline_freeze_report.md`
- `finetune_csv/README.md`
