# M2.1 Common-Origin Registry Report

## Decision

M2.1 created evaluation metadata only. No model inference, metric calculation,
or training was performed. Every registry row is valid for both `L=63` and
`L=126` with `H=5`.

## Registry

- Dataset: `vn150_strict_v2`
- Origin rows: 133,937
- Eligible dates: 977
- Symbols: 147
- Registry SHA256: `dcd71d14c5016b721111172d6a2ff384122eb74d2cc9c27252d359857e6726c6`
- Lockbox start: `2026-01-01`
- Minimum symbols per date: 10

| fold_id | origin_count | symbol_count | eligible_dates |
|---|---:|---:|---:|
| eval_2022 | 32492 | 141 | 244 |
| eval_2023 | 32752 | 140 | 244 |
| eval_2024 | 34197 | 145 | 245 |
| eval_2025 | 34496 | 146 | 244 |

## Guardrails

- Origins require 126 contiguous history rows and five contiguous targets in
  one security and segment; the same rows also define the 63-session view.
- Dates below ten eligible symbols are absent.
- Source data may contain 2026 rows, but no origin or target from 2026 is
  registered.
- The fixed current VN150 population remains survivorship-biased.
- Provider price-adjustment semantics remain unverified.
- `amount` remains the derived OHLC4 compatibility proxy, not provider turnover.

## Next Step

M2.2 may derive deterministic smoke and screen views from this registry and add
two causal naive forecast references. Kronos inference remains out of scope.
