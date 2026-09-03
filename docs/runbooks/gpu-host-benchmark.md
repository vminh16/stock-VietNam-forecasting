# Runbook: benchmark a GPU host before running M2 inference

Run this on any new GPU host before committing hours of inference to it. It
answers three questions that change the plan:

1. **Is the host set up correctly?** Every input path is checked with its size.
2. **Does it produce the same numbers as the host that ran M2.5 and M2.7?** A new
   GPU architecture can change floating-point results. If the numbers differ,
   results from the two hosts MUST NOT be pooled into one paired comparison, and
   any arm reused across hosts has to be re-run.
3. **How fast is it, at which batch size?** On the 4 GB RTX 2050 larger batches
   were *slower* because they paged through system RAM. A 24 GB card should not
   behave that way, but that is a measurement, not an assumption.

The script computes no metric, writes nothing under `data/evaluation/` or
`reports/`, and touches only dates the M2.5 screen already evaluated, so it
cannot leak information about an unevaluated date.

## 1. Get the repository and its inputs onto the host

```bash
git clone <this repo> stock-vn && cd stock-vn
```

`data/` is gitignored, so two directories must be copied separately. They are
small:

| what | size | why it is needed |
|---|---:|---|
| `data/curated/vn150_strict_v2/` | ~26 MB | the frozen M1 price data |
| `data/evaluation/m2_1/` | ~7 MB | the frozen common-origin registry |

```bash
# from the machine that already has them, e.g.
rsync -av data/curated/vn150_strict_v2/ USER@HOST:~/stock-vn/data/curated/vn150_strict_v2/
rsync -av data/evaluation/m2_1/        USER@HOST:~/stock-vn/data/evaluation/m2_1/
```

Do **not** regenerate them on the host. The registry is hash-verified against
its manifest, and a regenerated file will not match.

## 2. Environment

```bash
conda create -n kronos python=3.10 -y && conda activate kronos
pip install -r requirements.txt
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

`vnstock` and `peft` are only needed for crawling and fine-tuning; the benchmark
does not import them, but installing the full file keeps one environment.

## 3. Model weights

```bash
python - <<'PY'
from huggingface_hub import snapshot_download
for repo in ("NeoQuasar/Kronos-Tokenizer-base", "NeoQuasar/Kronos-small", "NeoQuasar/Kronos-base"):
    local = "pretrained/" + repo.split("/")[1]
    snapshot_download(repo_id=repo, local_dir=local)
    print("ok", local)
PY
```

About 500 MB total. The benchmark prints each file's size, so a truncated
download is visible immediately.

## 4. Run it

```bash
PYTHONPATH=finetune_csv python evaluation/benchmark_device.py --output device_benchmark_l4.json
```

Default grid: arms `small_l126` and `base_l126`, batch sizes 2/8/16/32/64,
sample counts 10 and 20, 48 origins per cell after 2 warmup batches. Expect
roughly 15-30 minutes. An out-of-memory cell is recorded as failed and the run
continues, which is the point of including batch 64.

Useful variants:

```bash
# fast sanity pass, no throughput grid
PYTHONPATH=finetune_csv python evaluation/benchmark_device.py --skip-throughput

# wider batch search on a large card
PYTHONPATH=finetune_csv python evaluation/benchmark_device.py --batch-sizes 16 32 64 128 256
```

## 5. Reading the result

### Checks 3 and 4, correctness and fingerprint

All of these must hold before the host is used for anything:

- `shape_ok: true`
- `all_finite: true`
- `plausible_magnitude: true` (no five-day return above 200%)
- `repeatable_same_seed: true` and `max_repeat_delta: 0.0`

Then compare the fingerprint against the host that produced the committed M2.5
and M2.7 results:

| host | GPU | fingerprint sha256 | mean | std |
|---|---|---|---:|---:|
| reference | RTX 2050, capability 8.6, torch 2.9.1 | `d4b2e364de40dd7ae5544ef75330612b98261566fc0f17248ac92654e186b188` | `-0.0013160804` | `0.0332151021` |

- **Hash matches** - the two hosts are numerically identical. Results can be
  pooled, and an arm already run on the reference host does not need re-running.
- **Hash differs, mean and std agree to about four decimals** - the same model,
  different floating-point accumulation, most likely TF32. Results MUST NOT be
  pooled into one paired comparison. Either re-run every arm on the new host, or
  disable TF32 and re-check:

  ```python
  torch.backends.cuda.matmul.allow_tf32 = False
  torch.backends.cudnn.allow_tf32 = False
  ```

- **Mean and std differ materially** - not a precision issue. Stop and
  investigate: wrong checkpoint, wrong tokenizer, or a truncated download.

The `tf32_matmul` and `tf32_cudnn` flags in the environment block record what the
host had enabled, so a later mismatch is explainable.

### Check 5, throughput

Read `projections` in the JSON: the best batch size per arm and the projected
hours for a full 977-date run. Those hours drive the run plan directly.

Watch for the batch-size curve shape. If throughput keeps rising to batch 64 or
128, the earlier 4 GB result does not transfer and the planned run configs should
raise `runtime.batch_size` from its current value of 2.

## 6. Send back

The JSON file. It carries the environment, the fingerprint, every throughput
cell, and the projections, which is everything needed to size the next
registration.
