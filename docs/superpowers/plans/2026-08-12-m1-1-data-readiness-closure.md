# M1.1 Data Readiness Closure

**Goal:** Decide whether the fixed VN150 snapshot is safe to use for model research, without running Kronos or building the M2 evaluation harness.

## Scope

1. Centralize the canonical feature and preprocessing contracts.
2. Split valid sequences at implausible overnight price discontinuities; never invent adjusted prices.
3. Audit schema, amount provenance, continuity, normalization, and window availability.
4. Build `vn150_strict_v2` from the immutable M1 raw snapshot and publish a readiness report.

## Success Criteria

- Tests prove gaps, invalid rows, and continuity breaks cannot be crossed by model windows.
- Normalization uses lookback rows only and reports clipping/constant-feature diagnostics.
- The report distinguishes verified facts from unknown provider adjustment semantics.
- The outcome is exactly one of `PASS`, `CONDITIONAL`, or `BLOCKED`.
- No model inference, training, fold registry, or frontend code is changed.

## Checkpoints

1. **Contract tests** -> verify failing tests for continuity and readiness findings.
2. **Minimal implementation** -> verify focused data tests pass.
3. **VN150 build and audit** -> verify hashes, counts, and report evidence.
4. **Regression** -> run the complete repository test suite.
