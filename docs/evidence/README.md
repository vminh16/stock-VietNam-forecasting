# Evidence

Sections 3.1 to 3.10 of `SPEC.md`, one file per subsection. Each summarises at
project level what a run found, and points at the full reading under `reports/`.

## What belongs here, and what does not

| layer | holds |
|---|---|
| `docs/registrations/` | what was promised before the run |
| **`docs/evidence/`** | **the project-level reading: headline numbers, verdict, limits** |
| `reports/<milestone>/<run>/` | the run's own artifacts: manifest, metric tables, `decision.md` |

A file here should stay short enough to read in one sitting. When a reading needs
more room, the room is in `reports/`.

## Correcting a reading

Numbers here are corrected by **adding a later subsection**, not by editing an
earlier one in place. Section 3.10 is the worked example: it did not rewrite the
calibration figures in 3.3, 3.5, 3.8 and 3.9, it measured what the metric can
reach and stated how those figures should now be read. The earlier text stays
visible with its date, so a reader can see what was believed when.

Editing a number in place would erase that trail, and the trail is the reason a
reader can trust the rest.

## Index

| section | subject | registered by | full reading |
|---|---|---|---|
| [3.1](3.1-data-snapshot.md) | Data snapshot | — | `reports/milestone_1_data/` |
| [3.2](3.2-baseline-model-evidence.md) | Baseline model evidence | — | `reports/milestone_0_baseline/` |
| [3.3](3.3-m2-5-zero-shot-screen-evidence.md) | M2.5 zero-shot screen | [8.6](../registrations/8.6-pre-registered-m2-5-screen-rule.md) | `reports/milestone_2_research_eval/zero_shot_screen/` |
| [3.4](3.4-m2-6-slice-readiness-evidence.md) | M2.6 slice readiness | [8.7](../registrations/8.7-registered-evaluation-slices.md) | `reports/milestone_2_research_eval/metric_slices/` |
| [3.5](3.5-m2-7-confirmation-evidence.md) | M2.7 confirmation | [8.8](../registrations/8.8-pre-registered-m2-7-confirmation-rule.md) | `reports/milestone_2_research_eval/confirmation/` |
| [3.6](3.6-m2-8-cross-sectional-gate-evidence.md) | M2.8 cross-sectional gate | [8.10](../registrations/8.10-pre-registered-m2-8-cross-sectional-gate.md) | `reports/milestone_2_research_eval/cross_sectional_references/` |
| [3.7](3.7-baseline-interpretation.md) | Baseline interpretation | — | — |
| [3.8](3.8-m2-9-sampling-noise-evidence.md) | M2.9 sampling noise | [8.11](../registrations/8.11-pre-registered-m2-9-sampling-noise-budget.md) | `reports/milestone_2_research_eval/seed_variance/` |
| [3.9](3.9-m2-10-full-registry-evidence.md) | M2.10 full registry | [8.12](../registrations/8.12-pre-registered-m2-10-full-registry-confirmation.md) | `reports/milestone_2_research_eval/full_registry/` |
| [3.10](3.10-what-the-interval-metric-can-reach.md) | What the interval metric can reach | — | `tests/test_interval_ceiling.py` |
