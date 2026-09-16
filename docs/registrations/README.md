# Registrations

Sections 8.6 to 8.14 of `SPEC.md`, one file per subsection. Each is a run plan
that was committed **before** its run started.

## The rule these files exist to enforce

A registration is **frozen** the moment it is committed. It MUST NOT be edited
afterwards: not to fix a threshold that turned out to be badly chosen, not to
add a metric that would have been useful, not to soften a bound the result
missed.

The asymmetry that governs a late addition is the same one `SPEC.md` section
8.10 states. **Raising** a bar after seeing a result is admissible, because it
cannot manufacture a pass. **Lowering** one is forbidden. A registration that
needs a different threshold is replaced by a new registration and a new run, and
the old one stays on the record with its result.

Two registrations here already carry the cost of that rule honestly.
Section 8.12 set an acceptance criterion, `worktree_dirty: false`, that no run
can satisfy; it is recorded as failed rather than reinterpreted. Section 8.8's
sizing was wrong by a factor of three and the corrected figure lives in the
evidence, not in the registration.

## Index

| section | subject | run | result |
|---|---|---|---|
| [8.6](8.6-pre-registered-m2-5-screen-rule.md) | M2.5 screen rule | zero-shot screen, 98 dates | [3.3](../evidence/3.3-m2-5-zero-shot-screen-evidence.md) |
| [8.7](8.7-registered-evaluation-slices.md) | Registered evaluation slices | M2.6 slice assignment | [3.4](../evidence/3.4-m2-6-slice-readiness-evidence.md) |
| [8.8](8.8-pre-registered-m2-7-confirmation-rule.md) | M2.7 confirmation rule | confirmation, 196 dates | [3.5](../evidence/3.5-m2-7-confirmation-evidence.md) |
| [8.9](8.9-multiple-comparisons.md) | Multiple comparisons | standing rule, no run | — |
| [8.10](8.10-pre-registered-m2-8-cross-sectional-gate.md) | M2.8 cross-sectional gate | ranking-capable references | [3.6](../evidence/3.6-m2-8-cross-sectional-gate-evidence.md) |
| [8.11](8.11-pre-registered-m2-9-sampling-noise-budget.md) | M2.9 sampling-noise budget | 5 replicates, 196 dates | [3.8](../evidence/3.8-m2-9-sampling-noise-evidence.md) |
| [8.12](8.12-pre-registered-m2-10-full-registry-confirmation.md) | M2.10 full-registry confirmation | 683 unused dates | [3.9](../evidence/3.9-m2-10-full-registry-evidence.md) |
| [8.13](8.13-pre-registered-m2-11-sampling-grid.md) | M2.11 sampling grid | 2x2 sampler factorial, 98 dates | [3.11](../evidence/3.11-m2-11-sampling-grid-evidence.md) |
| [8.14](8.14-pre-registered-m2-12-local-baseline.md) | M2.12 local baseline | one arm, 98 dates, host change | [3.12](../evidence/3.12-m2-12-local-baseline-evidence.md) |

## Adding one

Write the subsection, take the next section number, commit it, and only then
start the run. A registration written after its run is not a registration.

State in it: the data contract, the candidates, the budget, the reading rule
with every threshold, the acceptance criteria, and what the run cannot settle.
The last item matters most, because it is the one a reader is otherwise left to
discover after the fact.
