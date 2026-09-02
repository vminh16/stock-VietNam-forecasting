# M2.6 Origin Slice Assignment Report

## Decision

This unit assigns two slice labels to every frozen M2.1 origin. It runs no model
and reads no evaluation result, so both partitions are usable as pre-registered
slices. No metric is computed here.

## Registered Setup

- Registry SHA256: `dcd71d14c5016b721111172d6a2ff384122eb74d2cc9c27252d359857e6726c6`
- Origins labelled: 133,937
- Evaluation dates: 977
- Symbols: 147
- Liquidity lookback: 63 sessions, median traded amount
- Liquidity tiers: 3, assigned inside each evaluation date
- Symbol groups: 5, salted hash `vn150-strict-v2-m2-holdout`

## Symbol Groups

| symbol_group | symbols | origins | share of origins in tier_0 |
|---|---:|---:|---:|
| `group_0` | 30 | 28,284 | 0.352 |
| `group_1` | 27 | 24,575 | 0.417 |
| `group_2` | 24 | 21,805 | 0.181 |
| `group_3` | 27 | 24,307 | 0.351 |
| `group_4` | 39 | 34,966 | 0.353 |

The group label is a salted hash of `security_id` alone. It reads no price, no
return, and no model output, so an unseen-symbol holdout picked from this table
cannot have been chosen after seeing which symbols a candidate ranks well. The
tier-0 share column is a diagnostic only: a group whose share is far from
0.333 is liquidity-skewed by chance, and a holdout built
from it will not represent the whole population.

## Liquidity Tiers

| liquidity_tier | origins | symbols seen | median amount | min symbols on a date |
|---|---:|---:|---:|---:|
| `tier_0` | 45,042 | 87 | 133,791,158 | 43 |
| `tier_1` | 44,571 | 112 | 36,277,412 | 43 |
| `tier_2` | 44,324 | 85 | 4,399,852 | 42 |

Every tier keeps at least ten symbols on every date, so HitRate@Top10 is defined inside each tier.

Tiers are assigned inside each date, so a symbol moves between tiers as its
liquidity changes and each tier holds a stable share of the cross-section. A
fixed absolute threshold would instead drift with market growth and would make a
2022 tier incomparable to a 2025 tier.

## Limitations

- `amount` is the `volume * OHLC4` compatibility proxy recorded by M1, not
  provider-reported turnover, so tiers rank a proxy for traded value.
- The fixed VN150 population remains survivorship-conditional; tiers rank inside
  it and say nothing about symbols the universe excludes.
- Group balance is left to the hash. The report shows the realized skew rather
  than correcting it, because stratifying on liquidity would make the partition
  depend on the data it is meant to hold out.

## Next Step

`evaluation/run_metric_slices.py` recomputes per-date metrics inside each slice
from the per-origin metric files, and the existing paired date-block bootstrap
consumes those files unchanged.
