# Runbook: benchmark a GPU host before running M2 inference

Run this on any new GPU host before committing hours of inference to it. It
answers three questions that change the plan:

1. **Is the host set up correctly?** Every input path is checked with its size.
2. **Is it running the same model as the host that ran M2.5 and M2.7?** The
   greedy fingerprint answers that. The sampled fingerprint will differ between
   any two hosts and is not an integrity check; section 5 explains why. Either
   way, results from two hosts MUST NOT be pooled into one paired comparison,
   and any arm reused across hosts has to be re-run.
3. **How fast is it, at which batch size?** Both hosts measured so far are
   fastest at `batch 2`, for different reasons. Treat that as a measurement to
   repeat, not an assumption to carry over.

The script computes no metric, writes nothing except the report at `--output`,
and touches only dates the M2.5 screen already evaluated, so it cannot leak
information about an unevaluated date.

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

A line like `CUDACachingAllocator.cpp:3933 memory allocation failed with OOM on
device 0` is a warning, not a failure. The allocator frees its cache and retries,
and the cell reports `ok` on the next line. On the L4 that happened at
`base_l126, 20 samples, batch 64`, which still finished at 2.13 origins per
second.

Useful variants:

```bash
# fast sanity pass, no throughput grid, about 2 minutes
PYTHONPATH=finetune_csv python evaluation/benchmark_device.py --skip-throughput

# narrow grid, if a large batch is destabilising the host
PYTHONPATH=finetune_csv python evaluation/benchmark_device.py   --arms small_l126 --batch-sizes 2 8 16 --sample-counts 10
```

Searching batches above 64 is not worth the time. Neither host measured so far
gained anything from a larger batch, and the L4 lost 19% between batch 2 and
batch 64 while using 8.60 GB of 22.03.

## 5. Reading the result

### Checks 3 and 4, correctness and fingerprint

All of these must hold before the host is used for anything:

- `shape_ok: true`
- `all_finite: true`
- `plausible_magnitude: true` (no five-day return above 200%)
- `repeatable_same_seed: true` and `max_repeat_delta: 0.0`

The report then carries two fingerprints over the same eight origins, and they
answer different questions.

`greedy_fingerprint` decodes with `top_k=1`, so filtering leaves one token, its
softmax probability is 1, and the multinomial draw is forced. It depends on the
checkpoint, the tokenizer and the inputs, and not on the RNG. **This is the one
that tests host integrity.** If two hosts disagree on it beyond float32
rounding, something is actually wrong: wrong checkpoint, wrong tokenizer, or a
truncated download.

| host | greedy sha256 | mean | std |
|---|---|---:|---:|
| reference | `1ae1ad8f8209e67901f42ead7d03e0e5f97db89785c386fdd28fa7fac62d8b69` | `0.0022560544` | `0.0261763182` |
| L4 | `19d4c4b30a099af7be5667e4870e8ea8a258867a00432b08e49545ff98d970c1` | `0.0022560600` | `0.0261763151` |

Those two agree to eight significant figures, about two float32 units in the
last place, while the sampled fingerprint on the same pair of hosts disagrees in
the mean by `1.7e-3`, some three hundred thousand times more. The hashes still
differ, because the last bits do. That is the whole point of keeping both
fingerprints: the greedy one says the hosts run the same model, and the sampled
one says their forecast paths are not interchangeable.

**Never compare a sha256 across hosts, greedy included.** Both fingerprints hash
the bytes of float64 values produced by float32 arithmetic, so a last-bit
difference changes the digest. No two hosts with different rounding can ever
match, and demanding it sets an impossible bar.

The acceptance test between hosts is numeric:

| greedy comparison | reading |
|---|---|
| `mean` and `std` agree to 7 significant figures or better | pass, same model |
| they agree to only 3 or 4 | investigate: a different dtype, autocast, or TF32 setting |
| they differ in the first or second figure | stop: wrong checkpoint, wrong tokenizer, or a truncated download |

Compare the digest only against the **same** host's earlier report, where it does
catch a swapped checkpoint or a corrupted re-download.

Verified on the reference host: identical output under seeds `20260901`, `1` and
`999999`, maximum difference exactly `0.0`, while the sampler moved a single
five-day return by `0.1024` between two of those seeds. The full record is
`reports/device_benchmarks/rtx2050_greedy.json`, a fingerprint-only pass;
`rtx2050.json` is the earlier full run and predates this check, so it carries no
`greedy_fingerprint` field; `l4_greedy.json` is the matching pass on the L4.

`fingerprint` decodes through the sampler the real runs use, at
`temperature 0.6, top_p 0.9`. It will **not** match across hosts and a mismatch
is not evidence of a fault. A float32 difference of order `1e-7` in the logits
flips a token at a top-p boundary, and every later step of that path is then a
different draw. Measured between the reference RTX 2050 and the L4:

| host | GPU | torch | sampled sha256 | mean | std |
|---|---|---|---|---:|---:|
| reference | RTX 2050, capability 8.6 | 2.5.1+cu121 | `d4b2e364de40dd7ae5544ef75330612b98261566fc0f17248ac92654e186b188` | `-0.0013160804` | `0.0332151021` |
| L4 | NVIDIA L4, capability 8.9 | 2.13.0+cu130 | `b5111bc69a62b88a848107ff7a7c981eb4b1b6cffa5122a755a578d94bc85705` | `+0.0003587479` | `0.0299944685` |

Those means differ by more than the earlier version of this runbook treated as
proof of a broken host, and the host was not broken. The evidence that settled
it, and the evidence to collect on any future host:

1. **`first_five`, element by element.** Two of the five entries were identical
   to the last bit and the other three agreed to about `5e-8`. Same checkpoint,
   same tokenizer, same code path, same RNG stream.
2. **`peak_vram_gb` per throughput cell.** All thirteen cells the two hosts share
   matched to two decimals. A different model or a different graph would not do
   that.
3. Roughly one to three of the eighty sampled paths diverged outright, which is
   enough to move a pooled mean by `0.0017` and a pooled max from `0.1419` to
   `0.0992` while leaving almost every individual number intact.

So: compare `greedy_fingerprint` to judge the host, and compare `first_five` and
`peak_vram_gb` to confirm. Do not read `mean` and `std` of the sampled
fingerprint as an integrity check.

Pooling is a separate question from integrity, and the answer is stricter.
Because the sampled paths differ, results from two hosts MUST NOT be pooled into
one paired comparison even when every check above passes. Run every arm of a
comparison on one host.

`tf32_matmul` and `tf32_cudnn` are recorded so a later mismatch is explainable.
Both hosts above ran `matmul False, cudnn True`, so TF32 explains none of the
difference between them. `requirements.txt` pins only `torch>=2.0.0`, which is
why the two hosts are three minor versions apart; the exact version is recorded
in the report rather than constrained.

### Check 5, throughput

Read `projections` in the JSON: the best batch size per arm and the projected
hours for a full 977-date run. Those hours drive the run plan directly.

Measured so far, batch size does not help and mildly hurts. On the L4 the best
cell was `batch 2` for all four arm-and-sample combinations, and throughput fell
monotonically to batch 64 (`small_l126` at 10 samples: 18.45 to 14.90 origins
per second, down 19%) while peak VRAM reached only 8.60 GB of 22.03. That is not
the 4 GB card's failure mode, where `base_l126` at 16 samples collapsed to 0.07
origins per second by paging; it is plain per-step overhead. Keep
`runtime.batch_size: 2` unless a host measures otherwise.

The L4 ran 3.1 to 3.3 times faster than the RTX 2050 across every matched cell.

Running several processes at once does not help either. Two concurrent
`small_l126` runs on the L4 held about 9 origins per second each, an aggregate of
18 against the 18.45 a single process reaches alone. The card is already
saturated by one process at batch 2, which is why neither a wider batch nor a
second process buys anything: `auto_regressive_inference` has no KV cache, so
each of the five prediction steps re-runs the transformer over the whole
context window and the work is about five times larger than the output implies.
Schedule runs serially and keep the runtime numbers clean.

## 6. Send back

The JSON file. It carries the environment, the fingerprint, every throughput
cell, and the projections, which is everything needed to size the next
registration.
