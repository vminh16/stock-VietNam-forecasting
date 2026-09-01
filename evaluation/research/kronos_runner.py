from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

import model.kronos as kronos_module
from evaluation.inference_pipeline import generate_raw
from model import Kronos, KronosPredictor, KronosTokenizer


# Zero-shot adapter around the frozen M0 sampling path. Nothing here modifies
# model code; `generate_raw` is imported from the frozen pipeline so sampling
# semantics stay identical to the baseline.
#
# An arm carries both a lookback and a normalizer lookback because `L` sets the
# context and the point-in-time scaling at once. Holding `normalizer_lookback`
# at the long value while shortening `lookback` isolates the context effect that
# the M2.4 diagnostics showed is otherwise confounded.
FEATURES = ("open", "high", "low", "close", "volume", "amount")
CLOSE_INDEX = FEATURES.index("close")


@dataclass(frozen=True)
class ArmSpec:
    arm_id: str
    model_path: Path
    lookback: int
    normalizer_lookback: int

    def validate(self):
        if self.lookback < 1:
            raise ValueError(f"{self.arm_id}: lookback must be positive")
        if self.normalizer_lookback < self.lookback:
            raise ValueError(
                f"{self.arm_id}: normalizer_lookback must cover the lookback"
            )


def load_predictor(tokenizer_path, model_path, device, max_context=512, clip=5.0):
    tokenizer = KronosTokenizer.from_pretrained(str(tokenizer_path))
    predictor_model = Kronos.from_pretrained(str(model_path))
    predictor = KronosPredictor(
        predictor_model,
        tokenizer,
        device=device,
        max_context=max_context,
        clip=clip,
    )
    predictor.model.eval()
    predictor.tokenizer.eval()
    return predictor


def build_batch(frames, rows, arm, clip=5.0):
    arm.validate()
    inputs = []
    stamps = []
    target_stamps = []
    means = []
    scales = []
    origin_close = []
    actual_returns = []

    for row in rows.itertuples(index=False):
        frame = frames[row.symbol]
        values = frame[list(FEATURES)].to_numpy(dtype=np.float64)
        start = row.row_origin - arm.normalizer_lookback + 1
        if start < 0:
            raise ValueError(f"Origin {row.origin_id} lacks normalizer history")
        window = values[start : row.row_origin + 1]
        if window.shape[0] != arm.normalizer_lookback:
            raise ValueError(f"Origin {row.origin_id} has a truncated window")

        mean = window.mean(axis=0)
        raw_scale = window.std(axis=0)
        scale = np.where(raw_scale < 1e-6, 1.0, raw_scale)
        context = values[row.row_origin - arm.lookback + 1 : row.row_origin + 1]
        normalized = np.clip((context - mean) / (scale + 1e-5), -clip, clip)

        timestamps = frame["timestamps"]
        inputs.append(normalized.astype(np.float32))
        stamps.append(
            kronos_module.calc_time_stamps(
                timestamps.iloc[row.row_origin - arm.lookback + 1 : row.row_origin + 1]
            ).values.astype(np.float32)
        )
        target_stamps.append(
            kronos_module.calc_time_stamps(
                timestamps.iloc[row.row_target_start : row.row_target_end + 1]
            ).values.astype(np.float32)
        )
        means.append(mean)
        scales.append(scale)

        close = values[:, CLOSE_INDEX]
        base_close = close[row.row_origin]
        if base_close <= 0:
            raise ValueError(f"Origin {row.origin_id} has a non-positive close")
        origin_close.append(base_close)
        actual_returns.append(
            close[row.row_target_start : row.row_target_end + 1] / base_close - 1.0
        )

    return {
        "x": np.stack(inputs).astype(np.float32),
        "x_stamp": np.stack(stamps).astype(np.float32),
        "y_stamp": np.stack(target_stamps).astype(np.float32),
        "mean": np.stack(means),
        "scale": np.stack(scales),
        "origin_close": np.asarray(origin_close, dtype=np.float64),
        "actual_return": np.stack(actual_returns),
    }


def run_batch(
    predictor,
    batch,
    horizon,
    sample_count,
    seed,
    temperature,
    top_k,
    top_p,
    device,
    generate=generate_raw,
):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    predictions = generate(
        predictor.tokenizer,
        predictor.model,
        batch["x"],
        batch["x_stamp"],
        batch["y_stamp"],
        horizon,
        predictor.max_context,
        predictor.clip,
        temperature,
        top_k,
        top_p,
        sample_count,
        device,
    )
    predictions = np.asarray(predictions, dtype=np.float64)
    expected = (len(batch["x"]), sample_count, horizon, len(FEATURES))
    if predictions.shape != expected:
        raise ValueError(
            f"Sampler returned {predictions.shape}, expected {expected}"
        )

    close_mean = batch["mean"][:, CLOSE_INDEX][:, None, None]
    close_scale = batch["scale"][:, CLOSE_INDEX][:, None, None]
    close = predictions[:, :, :, CLOSE_INDEX] * (close_scale + 1e-5) + close_mean
    return close / batch["origin_close"][:, None, None] - 1.0
