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

## 0. If the host is a fresh Google Cloud instance

Skip this section on a host that already exists.

### Quota

An L4 needs `NVIDIA_L4_GPUS` quota in the target region, and it is often zero on
a new project. Check before creating anything, because a quota request can take
hours:

```bash
gcloud compute regions describe asia-southeast1 \
  --format="table(quotas.metric,quotas.limit,quotas.usage)" | grep -i l4
```

If the limit is 0, request an increase in IAM and Admin, Quotas, before going
further.

### Create the instance

L4s live in the G2 machine family, and the GPU comes with the machine type, so
there is no separate accelerator flag. `g2-standard-8` gives one L4 with 24 GB
of VRAM, 8 vCPU, and 32 GB of RAM, which is enough; the inference here is GPU
bound, not CPU bound.

Pick an image family that already carries a CUDA driver rather than installing
one by hand. List what is currently published instead of trusting a name from a
document, because these families are renamed over time:

```bash
gcloud compute images list --project deeplearning-platform-release \
  --filter="family~'cu12'" --format="value(family)" | sort -u
```

Then create, substituting the family you picked:

```bash
gcloud compute instances create kronos-l4 \
  --zone=asia-southeast1-b \
  --machine-type=g2-standard-8 \
  --image-project=deeplearning-platform-release \
  --image-family=<family from the list above> \
  --maintenance-policy=TERMINATE \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-balanced \
  --metadata="install-nvidia-driver=True"
```

`asia-southeast1` is the closest region to Vietnam; any region with L4 quota
works. 100 GB is for the image itself, not for this project's data, which is
under 600 MB including the model weights.

### Spot instances

`--provisioning-model=SPOT` cuts the price substantially and can be reclaimed at
any time. Whether that is acceptable depends on the arm:

- The screen runner resumes at **arm granularity**. A finished arm is cached and
  skipped on restart.
- A preemption **in the middle of** an arm loses that arm's work entirely. The
  longest single arm, `base_l126` over 977 dates, is several hours, so a spot
  preemption late in it is expensive in wall-clock terms even though the compute
  was cheap.

Spot is a good fit for the short benchmark and for the cheap `small_*` arms, and
a poor fit for a single long `base_l126` run unless you accept restarting it.

### First login

```bash
gcloud compute ssh kronos-l4 --zone=asia-southeast1-b
nvidia-smi     # must print an L4 with 24 GB before continuing
```

On the first boot a Deep Learning VM image may ask to install the driver; answer
yes and wait for it to finish. If `nvidia-smi` fails, nothing below will work.

### Cost control

Billing continues while the instance is RUNNING, whether or not anyone is
connected. Closing the SSH window does **not** stop it.

```bash
gcloud compute instances stop kronos-l4 --zone=asia-southeast1-b     # keeps the disk
gcloud compute instances delete kronos-l4 --zone=asia-southeast1-b   # removes everything
```

A stopped instance still bills for its disk, which is small. Check current L4
pricing on the Compute Engine pricing page rather than relying on a figure
quoted here.

## 1. Get the repository onto the host

```bash
git clone <this repo> stock-vn && cd stock-vn
```

That is the whole step. The frozen, hash-verified inputs are tracked:

| what | size | frozen by |
|---|---:|---|
| `data/curated/vn150_strict_v2/` | 27 MB | M1 |
| `data/raw/2026-08-09/` | 14 MB | the immutable crawl snapshot |
| `data/evaluation/m2_1/` | 6.6 MB | M2.1 |

Regenerable output under `data/evaluation/m2_2` and later stays untracked, so a
clone carries inputs only and each run recreates its own outputs.

`.gitattributes` marks everything under `data/` as `-text`, so git stores and
restores those bytes verbatim on every platform. Do not remove that rule. The
curated CSVs hold bare LF; with `core.autocrlf=true` on Windows a checkout would
rewrite them to CRLF, every `sha256_file` check against the manifests would
fail, and the failure would read as data corruption rather than a line-ending
conversion.

Verify after cloning, before anything else:

```bash
python - <<'CHECK'
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
from data_pipeline.crawl import sha256_file
m = json.loads(Path("reports/milestone_1_data/vn150_strict_v2/dataset_manifest.json").read_text(encoding="utf-8"))
base = Path("data/curated/vn150_strict_v2")
bad = [r for r, h in m["artifact_hashes"].items() if sha256_file(base / r) != h]
print("checked:", len(m["artifact_hashes"]), "mismatched:", len(bad))
CHECK
```

Expect 155 checked and 0 mismatched. A non-zero count means the checkout altered
the bytes; confirm `git check-attr text -- data/curated/vn150_strict_v2/symbols/FPT.csv`
reports `text: unset` before looking anywhere else.

Do not regenerate these inputs on the host. They are hash-verified against
manifests recorded in `reports/`, and a rebuilt file will not match.

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

`Kronos-base` and the tokenizer are also tracked through Git LFS, so a clone on
a host with LFS installed already has them; without LFS the clone leaves
134-byte pointer files, which the size check reports as 0.0 MB. `Kronos-small`
is not tracked either way. Downloading all three from Hugging Face is the one
path that works regardless, and it overwrites whatever the clone left behind.

## 4. Run it

Start a `tmux` session first. An SSH drop, a closed laptop, or a sleeping Wi-Fi
adapter kills a foreground process, and the real runs later are hours long:

```bash
tmux new -s bench          # detach with ctrl-b then d, reattach with: tmux attach -t bench
```

```bash
cd ~/stock-vn
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
