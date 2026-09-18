# Experiment Map

One row per experiment, joining the pieces that live in different directories.
Nothing here is a source of truth: the registration says what was promised, the
evidence file says what it showed, and `SPEC.md` holds the contract. This page
only tells you where to look.

The pieces stay where they are rather than being grouped into one directory per
experiment. Frozen reports, manifests and registrations cite these exact paths,
and `reports/**` must not be rewritten, so moving a file would break the record
it belongs to.

## How the pieces fit

| piece | where | lifecycle |
|---|---|---|
| config | `evaluation/configs/<phase>_*.yaml` | frozen once a run has used it |
| registration | `docs/registrations/8.x-*.md` | frozen on commit, written **before** the run |
| run outputs | `data/evaluation/<phase>/` | per-origin and per-date metrics, tracked |
| run report | `reports/milestone_2_research_eval/<run>/` | manifest, metric tables, `decision.md`; frozen |
| reading | `docs/evidence/3.x-*.md` | appended; corrected only by a later section |

To re-run a phase: `python evaluation/run_<runner>.py --config <config>`. The
runner for each is named in the report's `manifest.json` under `command`, which
also records the host the run executed on.

## Milestone 2

| phase | question | config | registration | evidence | report | host |
|---|---|---|---|---|---|---|
| M2.1 | freeze common origins | `m2_1_origins` | — | — | `origin_registry/` | local |
| M2.2 | naive references | `m2_2_naive` | — | — | `naive_references/` | local |
| M2.3 | paired block bootstrap | `m2_3_paired_inference` | — | — | `paired_inference/` | local |
| M2.4 | variance ratios, normalization confound | `m2_4_data_diagnostics` | — | — | `data_diagnostics/` | local |
| M2.5 | zero-shot screen, 5 arms, 98 dates | `m2_5_zero_shot_screen`, `m2_5_paired_inference` | [8.6](registrations/8.6-pre-registered-m2-5-screen-rule.md) | [3.3](evidence/3.3-m2-5-zero-shot-screen-evidence.md) | `zero_shot_screen/` | local |
| M2.6 | evaluation slices | `m2_6_origin_slices`, `m2_6_metric_slices` | [8.7](registrations/8.7-registered-evaluation-slices.md) | [3.4](evidence/3.4-m2-6-slice-readiness-evidence.md) | `origin_slices/`, `metric_slices/` | local |
| M2.7 | confirmation, 196 dates | `m2_7_confirmation`, `m2_7_metric_slices`, `m2_7_paired_inference`, `m2_7_slice_inference` | [8.8](registrations/8.8-pre-registered-m2-7-confirmation-rule.md) | [3.5](evidence/3.5-m2-7-confirmation-evidence.md) | `confirmation/` | local |
| M2.8 | cross-sectional gate | `m2_8_cross_sectional`, `m2_8_paired_inference` | [8.10](registrations/8.10-pre-registered-m2-8-cross-sectional-gate.md) | [3.6](evidence/3.6-m2-8-cross-sectional-gate-evidence.md) | `cross_sectional_references/` | local |
| M2.9 | sampling noise, 5 seeds | `m2_9_seed_variance`, `m2_9_paired_inference` | [8.11](registrations/8.11-pre-registered-m2-9-sampling-noise-budget.md) | [3.8](evidence/3.8-m2-9-sampling-noise-evidence.md) | `seed_variance/` | L4 |
| M2.10 | full registry, 683 unused dates | `m2_10_full_registry`, `m2_10_paired_inference` | [8.12](registrations/8.12-pre-registered-m2-10-full-registry-confirmation.md) | [3.9](evidence/3.9-m2-10-full-registry-evidence.md) | `full_registry/` | L4 |
| M2.11 | sampler 2x2 grid | `m2_11_sampling_{t06,t10}_{p90,p100}` | [8.13](registrations/8.13-pre-registered-m2-11-sampling-grid.md) | [3.11](evidence/3.11-m2-11-sampling-grid-evidence.md) | `sampling_grid/<cell>/` | L4 |
| M2.12 | same-host reproducibility | `m2_12_local_baseline` | [8.14](registrations/8.14-pre-registered-m2-12-local-baseline.md) | [3.12](evidence/3.12-m2-12-local-baseline-evidence.md) | `local_baseline/` | local |
| M2.13 | `L=40` context | `m2_13_lookback_40` | [8.15](registrations/8.15-pre-registered-m2-13-lookback-40.md) | [3.13](evidence/3.13-m2-13-lookback-40-evidence.md) | `lookback_40/` | local |
| closeout | M2 decision ledger, hashes, lockbox check | — | — | — | `closeout/` | local |

Report paths are relative to `reports/milestone_2_research_eval/`. Outputs are in
`data/evaluation/m2_<n>/`. Paired-inference reports sit in a `paired_inference/`
subdirectory of their run. A result computed on the L4 must never be paired with
one computed locally; see [3.12](evidence/3.12-m2-12-local-baseline-evidence.md).

Not tied to a run: [8.9](registrations/8.9-multiple-comparisons.md) multiple
comparisons, [3.7](evidence/3.7-baseline-interpretation.md) baseline
interpretation, [3.10](evidence/3.10-what-the-interval-metric-can-reach.md) the
interval ceiling.

## Milestones 0 and 1

| milestone | what | where |
|---|---|---|
| M0 | zero-shot and fine-tuned baseline freeze | `reports/milestone_0_baseline_freeze/`, configs `milestone0_baseline_zero_shot`, `milestone0_finetuned_v2` |
| M0 | earlier evaluation and tokenizer runs | `reports/baseline_model_evaluation/`, `reports/finetuned_model_evaluation/`, `reports/tokenizer_benchmarks/`, `reports/walkthrough_*.md` |
| M1 | VN150 data foundation | `reports/milestone_1_data/`, data in `data/raw/2026-08-09/` and `data/curated/vn150_strict_v2/` |
| — | GPU host benchmarks | `reports/device_benchmarks/`, runbook `docs/runbooks/gpu-host-benchmark.md` |

M0 numbers are historical record only. Section 11.3 of `SPEC.md` withdrew
comparability with M0 on 2026-09-16: it used a different dataset, backbone and
sampler.

## Research notes

`docs/research/` holds dated exploratory notes. They decide nothing on their own
and anything adopted from them needs a registration.
