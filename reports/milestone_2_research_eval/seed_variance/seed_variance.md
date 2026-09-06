# M2.9 Sampling-Noise Budget

Read against SPEC section 8.11, registered before any replicate was computed.
5 replicates of `small_l126` over
196 dates and 26,869 origins. The
replicates differ only in their RNG stream.

| metric | small_l126_r1 | small_l126_r2 | small_l126_r3 | small_l126_r4 | small_l126_r5 | sd |
|---|---|---|---|---|---|---|
| `DA` | 51.1519 | 51.3343 | 50.8541 | 50.7797 | 51.3305 | 0.261367 |
| `MW-DA` | 50.4745 | 50.6031 | 51.1580 | 50.5523 | 50.8970 | 0.284525 |
| `RankIC` | 0.0267 | 0.0253 | 0.0255 | 0.0218 | 0.0253 | 0.001849 |
| `HitRate@Top10` | 52.6531 | 52.1939 | 51.9898 | 51.7857 | 52.6020 | 0.378377 |
| `CRPS` | 0.0261 | 0.0261 | 0.0261 | 0.0261 | 0.0261 | 0.000012 |
| `coverage` | 0.4045 | 0.4025 | 0.3954 | 0.4009 | 0.4021 | 0.003410 |
| `interval_width` | 0.0514 | 0.0511 | 0.0509 | 0.0513 | 0.0512 | 0.000176 |

## Decision

`sd_seed` on RankIC is `0.001849` against a
registered threshold of `0.003763`
(`0.25 * sigma_date`, `sigma_date = 0.015051`).

Sampling noise is **immaterial, SPEC 8.11 rule 4 applies**. Combining it with date-resampling noise widens
every reported interval by a factor of
`1.0075`.
