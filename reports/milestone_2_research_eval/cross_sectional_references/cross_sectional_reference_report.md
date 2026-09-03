# M2.8 Cross-Sectional Reference Report

## Decision

M2.2 established that Kronos beats references carrying no ranking information.
This unit adds references that do carry ranking information, so a model can be
asked the harder question: does it beat a cheap, well-known effect computed from
the same closes? No model ran here and no promotion follows from this report.

## Registered Setup

- Registry SHA256: `dcd71d14c5016b721111172d6a2ff384122eb74d2cc9c27252d359857e6726c6`
- Origin rows per candidate: 133,937
- Evaluation dates: 977
- Symbols: 147
- Horizon: 5
- Sample paths per origin: 20, identical by construction
- Seeds: none. Both references are deterministic.

`short_term_reversal` predicts the negative of the trailing
5-session return, the horizon this project forecasts.
`momentum_126_21` predicts continuation of the 126-session
formation return that skips the most recent 21 sessions, rescaled
to the forecast horizon by simple proportion. Both fit inside the registered
`L=126` history, so they add no data requirement.

## Ranking Metrics

| candidate | DA | MW-DA | RankIC | HitRate@Top10 |
|---|---:|---:|---:|---:|
| `short_term_reversal` | 50.1034 | 47.5034 | 0.0153 | 49.9795 |
| `momentum_126_21` | 50.5305 | 50.5514 | 0.0088 | 50.6858 |

## Per-Fold Ranking Metrics

| candidate | fold | RankIC | HitRate@Top10 |
|---|---|---:|---:|
| `momentum_126_21` | eval_2022 | -0.0143 | 44.0984 |
| `momentum_126_21` | eval_2023 | 0.0044 | 54.4262 |
| `momentum_126_21` | eval_2024 | 0.0523 | 54.2041 |
| `momentum_126_21` | eval_2025 | -0.0075 | 50.0000 |
| `short_term_reversal` | eval_2022 | -0.0102 | 43.8934 |
| `short_term_reversal` | eval_2023 | 0.0290 | 53.5246 |
| `short_term_reversal` | eval_2024 | 0.0395 | 52.4082 |
| `short_term_reversal` | eval_2025 | 0.0027 | 50.0820 |

## Reading These Numbers

- These are **point forecasts replicated across samples**. CRPS, interval
  coverage, and interval width are meaningless for them and are omitted from the
  tables above on purpose. A probabilistic comparison against these references
  would need a dispersion model that is not registered.
- The horizon rescaling is unit conversion, not a fitted coefficient. RankIC is
  invariant to it, so the ranking comparison is unaffected by that choice; DA and
  MW-DA depend only on sign, which the rescaling preserves.
- A reference whose pooled RankIC is far from zero means a cheap formula already
  ranks this market. Any model claim must then clear that formula, not just the
  M2.2 noise references.
- Both references read only closes up to the forecast origin.

## Guardrails

- Identical origins, targets, and horizon as every other M2 candidate, so paired
  date-block inference applies without restriction.
- The fixed VN150 population remains survivorship-conditional.
- Provider price-adjustment semantics remain unverified, and a corporate action
  that the provider did not adjust will contaminate both a reversal and a
  momentum signal more than it contaminates a naive reference.
- The 2026 lockbox remains closed.
