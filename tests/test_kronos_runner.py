import numpy as np
import pandas as pd
import pytest

from evaluation.research.kronos_runner import (
    CLOSE_INDEX,
    FEATURES,
    ArmSpec,
    build_batch,
    run_batch,
)


class FakePredictor:
    def __init__(self, max_context=512, clip=5.0):
        self.tokenizer = "tokenizer"
        self.model = "model"
        self.max_context = max_context
        self.clip = clip


@pytest.fixture
def frames():
    sessions = pd.bdate_range("2021-01-04", periods=400)
    generator = np.random.default_rng(1234)
    close = 30.0 * np.exp(np.cumsum(generator.normal(0.0004, 0.02, len(sessions))))
    frame = pd.DataFrame(
        {
            "timestamps": sessions + pd.Timedelta(hours=9),
            "open": close * 0.998,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": generator.lognormal(11.0, 0.3, len(sessions)),
            "amount": close * generator.lognormal(11.0, 0.3, len(sessions)),
        }
    )
    return {"AAA": frame}


@pytest.fixture
def rows():
    return pd.DataFrame(
        [
            {
                "origin_id": "origin_a",
                "symbol": "AAA",
                "row_origin": 200,
                "row_target_start": 201,
                "row_target_end": 205,
            },
            {
                "origin_id": "origin_b",
                "symbol": "AAA",
                "row_origin": 260,
                "row_target_start": 261,
                "row_target_end": 265,
            },
        ]
    )


def _fake_generate(shape_close):
    def generate(tokenizer, model, x, x_stamp, y_stamp, pred_len, max_context, clip,
                 temperature, top_k, top_p, sample_count, device):
        output = np.zeros((len(x), sample_count, pred_len, len(FEATURES)))
        output[:, :, :, CLOSE_INDEX] = shape_close
        return output

    return generate


def test_batch_shapes_follow_the_arm_lookback(frames, rows):
    short = build_batch(frames, rows, ArmSpec("small_l63", "path", 63, 63))
    long = build_batch(frames, rows, ArmSpec("small_l126", "path", 126, 126))

    assert short["x"].shape == (2, 63, 6)
    assert long["x"].shape == (2, 126, 6)
    assert short["x_stamp"].shape[1] == 63
    assert short["y_stamp"].shape[1] == 5
    assert short["actual_return"].shape == (2, 5)


def test_normalizer_lookback_changes_scaling_but_not_the_rows(frames, rows):
    plain = build_batch(frames, rows, ArmSpec("small_l63", "path", 63, 63))
    borrowed = build_batch(frames, rows, ArmSpec("small_l63_norm126", "path", 63, 126))

    assert plain["x"].shape == borrowed["x"].shape
    assert not np.allclose(plain["scale"], borrowed["scale"])
    np.testing.assert_allclose(plain["origin_close"], borrowed["origin_close"])
    np.testing.assert_allclose(plain["actual_return"], borrowed["actual_return"])


def test_actual_returns_are_measured_from_the_origin_close(frames, rows):
    batch = build_batch(frames, rows, ArmSpec("small_l63", "path", 63, 63))
    close = frames["AAA"]["close"].to_numpy()

    expected = close[201:206] / close[200] - 1.0
    np.testing.assert_allclose(batch["actual_return"][0], expected)


def test_arm_rejects_a_normalizer_shorter_than_the_lookback():
    with pytest.raises(ValueError, match="normalizer_lookback"):
        ArmSpec("bad", "path", 126, 63).validate()


def test_run_batch_denormalizes_into_cumulative_close_returns(frames, rows):
    arm = ArmSpec("small_l63", "path", 63, 63)
    batch = build_batch(frames, rows, arm)
    normalized_close = 0.5

    paths = run_batch(
        FakePredictor(),
        batch,
        horizon=5,
        sample_count=3,
        seed=7,
        temperature=1.0,
        top_k=0,
        top_p=0.9,
        device="cpu",
        generate=_fake_generate(normalized_close),
    )

    assert paths.shape == (2, 3, 5)
    expected_close = (
        normalized_close * (batch["scale"][:, CLOSE_INDEX] + 1e-5)
        + batch["mean"][:, CLOSE_INDEX]
    )
    expected = expected_close / batch["origin_close"] - 1.0
    np.testing.assert_allclose(paths[:, 0, 0], expected)


def test_run_batch_rejects_a_sampler_with_the_wrong_shape(frames, rows):
    batch = build_batch(frames, rows, ArmSpec("small_l63", "path", 63, 63))

    def wrong(*args, **kwargs):
        return np.zeros((2, 3, 4, 6))

    with pytest.raises(ValueError, match="expected"):
        run_batch(
            FakePredictor(),
            batch,
            horizon=5,
            sample_count=3,
            seed=7,
            temperature=1.0,
            top_k=0,
            top_p=0.9,
            device="cpu",
            generate=wrong,
        )
