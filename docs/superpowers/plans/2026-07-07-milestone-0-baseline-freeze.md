# Milestone 0 Baseline Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the current Stock-VN-Forecasting baseline on `main` using final evaluation artifacts for both Kronos zero-shot and current fine-tuned v2.

**Architecture:** Keep model and evaluation behavior unchanged. Add separate Milestone 0 configs so canonical final evaluation writes into a freeze directory, then add a small report CLI that summarizes existing artifacts into a manifest and Markdown report.

**Tech Stack:** Python 3.10, pandas, PyYAML, pytest, existing Kronos evaluation pipeline.

## Global Constraints

- Do not modify Kronos architecture in `model/kronos.py` or `model/module.py`.
- Do not add Trend/Risk heads or losses.
- Preserve daily data, lookback 126, predict window 5, temporal split, no random split.
- Use final evaluation for canonical freeze.
- Commit all dirty state on `main` after verification, per user request.

---

### Task 1: Baseline Freeze Tests

**Files:**
- Create: `tests/test_baseline_freeze.py`

**Interfaces:**
- Consumes: planned `evaluation.freeze_baseline`
- Produces: tests for metric extraction, manifest hashing, report interpretation

- [ ] Write tests for `load_metric_contract`, `sha256_file`, and `freeze_baseline`.
- [ ] Run `pytest tests/test_baseline_freeze.py -q` and verify RED fails because `evaluation.freeze_baseline` does not exist.

### Task 2: Freeze CLI And Configs

**Files:**
- Create: `evaluation/freeze_baseline.py`
- Create: `evaluation/configs/milestone0_baseline_zero_shot.yaml`
- Create: `evaluation/configs/milestone0_finetuned_v2.yaml`
- Modify: `requirements.txt`

**Interfaces:**
- CLI inputs: `--zero-shot-dir`, `--finetuned-dir`, `--out-dir`
- CLI outputs: `manifest.json`, `baseline_freeze_report.md`

- [ ] Implement minimal metric extraction for `DA`, `MW-DA`, `RankIC`, and `HitRate`.
- [ ] Implement artifact SHA256 manifest generation.
- [ ] Implement Markdown report generation with hard-stop and zero-shot versus fine-tuned interpretation.
- [ ] Add `PyYAML` and `scipy` to dependencies.

### Task 3: Canonical Final Evaluation

**Files:**
- Output: `reports/milestone_0_baseline_freeze/zero_shot/*`
- Output: `reports/milestone_0_baseline_freeze/finetuned_v2/*`
- Output: `reports/milestone_0_baseline_freeze/manifest.json`
- Output: `reports/milestone_0_baseline_freeze/baseline_freeze_report.md`

**Commands:**

```powershell
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation/inference_pipeline.py --config evaluation/configs/milestone0_baseline_zero_shot.yaml --mode final
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation/inference_pipeline.py --config evaluation/configs/milestone0_finetuned_v2.yaml --mode final
C:\Users\USER\anaconda3\envs\stock\python.exe evaluation/freeze_baseline.py --zero-shot-dir reports/milestone_0_baseline_freeze/zero_shot --finetuned-dir reports/milestone_0_baseline_freeze/finetuned_v2 --out-dir reports/milestone_0_baseline_freeze
```

- [ ] If CUDA/WDDM paging is too slow or OOM occurs, reduce only `eval_batch_size` from 8 to 4.
- [ ] Do not change `sample_count` or `--mode final`.

### Task 4: Context Update And Commit

**Files:**
- Modify: `skills/vn-stock-market-radar/references/project-context.md`
- Modify: `skills/vn-stock-market-radar/references/milestone-map.md`

- [ ] Record the Milestone 0 report and manifest paths.
- [ ] Set Milestone 1 as Kronos Path Viewer.
- [ ] State that fine-tuned v2 is a model improvement only if final `DA` and `MW-DA` beat zero-shot or a tradeoff is explicitly justified.
- [ ] Run unit tests and skill validation.
- [ ] Review `git diff --stat` and `git status --short`.
- [ ] Stage all changes and commit with `chore: freeze milestone 0 baseline`.
