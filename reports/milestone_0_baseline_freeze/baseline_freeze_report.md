# Milestone 0 Baseline Freeze Report

Freeze id: `milestone_0_baseline_freeze`
Generated at UTC: `2026-07-26T04:47:18+00:00`

## Evaluation Contract

- Mode: `zero_shot_final`
- Status: `frozen`
- Data path: `data_cleaned`
- CSV count: `50`
- Lookback window: `126`
- Predict window: `5`
- Train end date: `2023-01-01`
- Validation end date: `2024-01-01`
- Metrics: `DA`, `MW-DA`, `RankIC`, `HitRate@Top10`
- Date coverage: `120` dates,
  `2024-01-08` to
  `2026-06-04`

## Commands

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation/inference_pipeline.py --config evaluation/configs/milestone0_baseline_zero_shot.yaml --mode final
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation/freeze_baseline.py --zero-shot-dir reports/milestone_0_baseline_freeze/zero_shot --out-dir reports/milestone_0_baseline_freeze --mode zero_shot_final
```

## Metric Snapshot

| Metric | Validation | Test |
|---|---:|---:|
| DA | 50.1423 | 51.6343 |
| MW-DA | 47.8501 | 49.0046 |
| RankIC | 0.0250 | -0.0026 |
| HitRate@Top10 | 56.8750 | 49.7500 |

## Interpretation

- Zero-shot DA utility floor: FAIL (`Test DA >= 52`)
- The baseline is a reproducibility anchor, not evidence of model usefulness.
- Fine-tuned v2 is excluded because its sampled date coverage is not comparable.
- Future models must use identical point-in-time origins and the M2 statistical protocol.
- This is a research baseline, not investment advice.

## Baseline Status

Milestone 0 status: **CLOSED**. The canonical baseline is Kronos-base zero-shot only.

## Next Phase

Milestone 1: Point-In-Time Data And Universe.
