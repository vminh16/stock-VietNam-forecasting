# VN150 Strict Data Quality Report

Dataset: `vn150_strict_v1`

## Coverage

- Symbols: 150
- Raw rows: 279973
- Valid rows: 278303
- Contiguous segments: 1594
- Symbols below 252 valid sessions: 3
- Short-history symbols: TCX, VCK, VPX
- First valid bar: 2018-08-09 09:00:00
- Last valid bar: 2026-08-07 09:00:00

## Amount Provenance

```json
{
  "derived_ohlc4": 278303
}
```

## Calendar Coverage

- HNX: 1997 sessions, 2018-08-09 to 2026-08-07
- HOSE: 1997 sessions, 2018-08-09 to 2026-08-07
- UPCOM: 1997 sessions, 2018-08-09 to 2026-08-07

## Exchange Summary

```text
          symbols  raw_rows  valid_rows  segments
exchange
HNX            30     58100       56702       773
HOSE          100    184593      184448       381
UPCOM          20     37280       37153       440
```

## Window Availability

- `L=63, H=5`: 247999 windows
- `L=126, H=5`: 229734 windows

These are dependent observations from overlapping windows, not an effective
sample size.

## Exclusions

```json
{
  "duplicate_identical": 2,
  "invalid_ohlc": 243,
  "missing_session": 3209,
  "outside_calendar_coverage": 1425
}
```
