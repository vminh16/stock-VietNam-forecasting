import locale
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.inference_pipeline import format_low_vram_warning


def test_low_vram_warning_is_console_encoding_safe():
    message = format_low_vram_warning(
        total_vram_mb=4096,
        eval_batch_size=8,
        sample_count=20,
        config_path="evaluation/configs/milestone0_baseline_zero_shot.yaml",
    )

    message.encode(locale.getpreferredencoding(False))
    assert "CANH BAO" in message
    assert "eval_batch_size = 8" in message
    assert "sample_count = 20" in message
