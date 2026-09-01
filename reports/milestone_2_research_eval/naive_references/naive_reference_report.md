# M2.2 Naive Reference Report

## Decision

M2.2 evaluated two causal naive references on the frozen M2.1 common origins. No
Kronos inference, training, or model selection was performed. These numbers are
the floor that any future model must beat on identical origins.

## Evidence

- Dataset: `vn150_strict_v2`
- Registry SHA256: `dcd71d14c5016b721111172d6a2ff384122eb74d2cc9c27252d359857e6726c6`
- Origin rows per candidate: 133,937
- Evaluation dates: 977
- Symbols: 147
- Sample paths per origin: 20
- Sampling seed: 20260812
- Interval quantiles: [0.1, 0.9]

| candidate | scope | DA | MW-DA | RankIC | HitRate@Top10 | CRPS | coverage | width |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `persistence` | pooled | 50.8754 | 48.0411 | 0.0000 | 45.8444 | 0.029795 | 0.0332 | 0.000000 |
| `recent_return_bootstrap` | pooled | 49.5270 | 50.1075 | -0.0086 | 50.2968 | 0.024238 | 0.6868 | 0.115291 |

## Per-Fold Evidence

| candidate | fold | DA | MW-DA | RankIC | HitRate@Top10 | CRPS | coverage | width |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `persistence` | eval_2022 | 55.9615 | 57.0144 | 0.0000 | 41.5574 | 0.043185 | 0.0195 | 0.000000 |
| `persistence` | eval_2023 | 46.9773 | 41.0312 | 0.0000 | 52.8279 | 0.027328 | 0.0344 | 0.000000 |
| `persistence` | eval_2024 | 51.1829 | 45.1263 | 0.0000 | 44.7347 | 0.022056 | 0.0420 | 0.000000 |
| `persistence` | eval_2025 | 49.4811 | 43.3874 | 0.0000 | 44.2623 | 0.027198 | 0.0362 | 0.000000 |
| `recent_return_bootstrap` | eval_2022 | 47.9995 | 47.8513 | -0.0486 | 43.5656 | 0.035158 | 0.6458 | 0.157063 |
| `recent_return_bootstrap` | eval_2023 | 50.5007 | 51.4399 | 0.0102 | 54.1803 | 0.022112 | 0.7219 | 0.118664 |
| `recent_return_bootstrap` | eval_2024 | 49.5833 | 50.3157 | 0.0114 | 52.1224 | 0.017919 | 0.7015 | 0.087425 |
| `recent_return_bootstrap` | eval_2025 | 49.9855 | 52.1137 | -0.0073 | 51.3115 | 0.022235 | 0.6776 | 0.100368 |

## Reading These Numbers

- `persistence` predicts zero cumulative return, so `direction(0) = -1` makes it a
  permanent down call; its DA equals the share of non-positive realized returns.
- That trivial down call reaches DA 55.9615 in `eval_2022`,
  which is a direct warning about the `DA >= 52%` product utility floor: a falling
  market can lift DA above the floor without any forecasting skill. DA alone
  therefore cannot promote a model, and MW-DA plus RankIC carry the decision.
- `recent_return_bootstrap` resamples contiguous five-session blocks from the
  trailing 63 observed sessions, so it carries realistic
  dispersion without any cross-sectional signal.
- RankIC near zero is the expected result for both references. A model that fails
  to beat these values has produced no ranking information.
- CRPS, coverage, and width come from the sampled paths, not from a point
  forecast; `persistence` has zero width by construction.

## Guardrails

- Paired comparison is preserved: both candidates use identical origins, targets,
  sample counts, and per-origin seeds.
- No future observation reaches a forecast; both references read only closes up
  to the forecast origin.
- Confidence intervals are absent by design; paired date-block bootstrap arrives
  with M2.3.
- The fixed current VN150 population remains survivorship-biased.
- Provider price-adjustment semantics remain unverified.

## Next Step

M2.3 adds the zero-shot Kronos runner on these same origins, then paired
stationary date-block inference against these references.
