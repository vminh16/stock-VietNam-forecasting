# Milestone 0 Baseline Freeze Report

Freeze id: `milestone_0_baseline_freeze`
Generated at UTC: `2026-07-08T03:35:54+00:00`

> Note: This report is a fallback snapshot from existing sampled/dev artifacts. It is not the canonical final freeze.


## Evaluation Contract

- Mode: `dev_sampled`
- Data path: `data_cleaned`
- CSV count: `50`
- Lookback window: `126`
- Predict window: `5`
- Train end date: `2023-01-01`
- Validation end date: `2024-01-01`
- Metrics: `DA`, `MW-DA`, `RankIC`, `HitRate`

## Commands

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation/inference_pipeline.py --config evaluation/configs/milestone0_baseline_zero_shot.yaml --mode final
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation/inference_pipeline.py --config evaluation/configs/milestone0_finetuned_v2.yaml --mode final
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation/freeze_baseline.py --zero-shot-dir reports/milestone_0_baseline_freeze/zero_shot --finetuned-dir reports/milestone_0_baseline_freeze/finetuned_v2 --out-dir reports/milestone_0_baseline_freeze --mode dev_sampled
```

## Metric Snapshot

| Metric | Zero-shot Validation | Fine-tuned Validation | Zero-shot Test | Fine-tuned Test |
|---|---:|---:|---:|---:|
| DA | 49.3750 | 51.9167 | 52.7600 | 51.2000 |
| MW-DA | 46.5714 | 50.7472 | 49.3795 | 50.1273 |
| RankIC | 0.0243 | 0.0501 | 0.0170 | 0.0333 |
| HitRate | 57.5000 | 58.1250 | 53.4000 | 51.0000 |

## Interpretation

- Zero-shot DA hard stop: PASS (`Test DA >= 52`)
- Fine-tuned v2 DA hard stop: FAIL (`Test DA >= 52`)
- Fine-tuned v2 does not beat zero-shot on Test DA.
- Fine-tuned v2 beats zero-shot on Test MW-DA.
- Treat fine-tuned v2 as a model improvement only if final `DA` and `MW-DA` beat zero-shot, or if a later report explains a deliberate tradeoff.
- This is a research baseline, not investment advice.

## Next Phase

Milestone 1 should build the Kronos Path Viewer: actual path, stochastic forecast paths, mean/median forecast line, confidence band, and clear uncertainty language.
