# Stock-VN-Forecasting

[English](README.md) | [Tiếng Việt](README_VI.md)

A research system that tests whether the Kronos time-series foundation model can
forecast five-session returns for the VN150 universe of Vietnamese stocks, and
whether adapting it to this market adds anything a simple formula does not.

It is not an investment product and nothing it produces is investment advice.

## Status

| milestone | state |
|---|---|
| M0 baseline freeze | complete |
| M1 VN150 data foundation | complete |
| M2 research evaluation harness | M2.1 to M2.13 complete; closure steps pending |
| M3 small-model adaptation (fine-tuning) | next |

Zero-shot Kronos-small does not beat a five-session reversal formula at ranking
stocks on 683 unused dates. That is the case for M3. Full detail in `SPEC.md`.

## Read first

1. [`AGENTS.md`](AGENTS.md): the operating rules. Immutable.
2. [`SPEC.md`](SPEC.md): the contract. Data, metrics, gates, milestones.
3. [`docs/experiments.md`](docs/experiments.md): every experiment with its
   config, registration, evidence and report in one table.

## Where things are

| path | holds |
|---|---|
| `model/` | Kronos model code. Do not modify without approval |
| `data_pipeline/` | crawl, audit and build of the VN150 dataset |
| `evaluation/` | runners (`run_*.py`), configs, and the research harness in `evaluation/research/` |
| `finetune_csv/` | fine-tuning code from M0. To be rewritten in M3 |
| `tests/` | test suite |
| `data/raw/`, `data/curated/` | the frozen crawl and the curated dataset, hash-verified |
| `data/evaluation/` | per-origin and per-date outputs of every M2 run |
| `reports/` | frozen run artifacts. Never rewritten |
| `docs/registrations/` | run plans, committed **before** each run. Frozen |
| `docs/evidence/` | what each run showed. Appended, never edited in place |
| `docs/research/` | dated exploratory notes. Decide nothing on their own |
| `docs/runbooks/` | operational guides, such as benchmarking a GPU host |
| `docs/superpowers/plans/` | implementation plans per milestone |

## Setup

```bash
conda create -n stock python=3.10
conda activate stock
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

`pretrained/Kronos-base` and `pretrained/Kronos-Tokenizer-base` are in the
repository. Kronos-small is not; download it from
[NeoQuasar/Kronos-small](https://huggingface.co/NeoQuasar/Kronos-small) into
`pretrained/Kronos-small/`.

## Run

```bash
python -m pytest tests/ -q
python evaluation/run_zero_shot_screen.py --config evaluation/configs/m2_13_lookback_40.yaml
```

`tests/test_dataloader.py` fails to import: it tests the M0 dataset class and is
due to be replaced with the fine-tuning code in M3.

Every run writes a `manifest.json` recording its command, whose interpreter
path identifies the host, along with the code revision and input hashes.
Results from different hosts must not be paired in one comparison; see
`docs/evidence/3.12-m2-12-local-baseline-evidence.md`.

## Rules that matter most

- No training run without a registration committed first: data, folds,
  candidates, budget, promotion rule and acceptance criteria.
- A registered threshold may be raised after a result is seen, never lowered.
- The 2026 lockbox stays closed until the final reading.
- Every output traces to data, universe, model, config, revision, origin and
  seed.

## License

[MIT](LICENSE), inherited from the upstream Kronos repository.
