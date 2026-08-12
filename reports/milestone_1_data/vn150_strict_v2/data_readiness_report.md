# VN150 Data Readiness

## Decision

**CONDITIONAL.** The dataset has no structural blocker only when the blocking list
below is empty. A conditional result permits evaluation-harness work, but not an
unqualified claim that provider prices are corporate-action adjusted.

## Dataset

- Dataset: `vn150_strict_v2` (`strict_v2`)
- Symbols: 150
- Valid rows: 278303
- Contiguous segments: 1594
- Large overnight jumps retained for review: 19
- Price adjustment status: `unverified_provider_history`
- Amount policy: `derived_ohlc4_compatibility_proxy`

## Structural Findings

- Blocking findings: none
- Conditional findings: unverified_provider_history, derived_ohlc4_compatibility_proxy

## Window Contract

- `L=63, H=5`: 247999 training windows; 248312 evaluation origins.
- `L=126, H=5`: 229734 training windows; 230008 evaluation origins.

Training uses `L+H+1` rows for next-token loss. Evaluation uses `L+H` rows.
Neither count is an effective sample size.

## Normalization Diagnostics

```text
 lookback  sampled_nonoverlap_windows  clipped_values  normalization_values  constant_feature_windows  clip_rate
       63                        4115            1038               1555470                         0   0.000667
      126                        1943            1383               1468908                         0   0.000942
```

Normalization is local Z-score using lookback rows only, with scale `1.0` for
near-constant features and clipping at `[-5.0, 5.0]`.

## Interpretation

- KBS `history()` exposes OHLCV in thousand-VND price units but does not attach
  a machine-readable adjusted-price guarantee in the retained payload.
- The pipeline preserves provider OHLC and records jumps above 17% for review.
  It does not split or rewrite observations without a point-in-time reference
  price or corporate-action factor.
- `amount` is a deterministic Kronos-compatibility proxy, not reported turnover.
- The fixed current VN150 population remains survivorship-biased by construction.

## Source Notes

- Vnstock 4.0.x KBS history implementation and price-unit behavior:
  https://github.com/thinh-vu/vnstock
- Vnstock release notes for KBS thousand-VND normalization:
  https://vnstocks.com/docs/tai-lieu/lich-su-phien-ban
- Official Kronos repository and six-feature K-line contract:
  https://github.com/shiyu-coder/Kronos
