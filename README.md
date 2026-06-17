# Stock-VN-Forecasting

Dự báo chứng khoán Việt Nam sử dụng mô hình Foundation **Kronos** — fine-tuned trên 50 cổ phiếu lớn nhất thị trường VN.

> Dự án nghiên cứu khả năng transfer learning của Kronos (pre-trained trên 12 tỷ+ nến từ 45 sàn quốc tế) sang thị trường Việt Nam — một thị trường Frontier/Emerging có đặc thù riêng biệt (biên độ ±7%, T+2, retail-dominated).

## Tổng quan

| Hạng mục | Giá trị |
|---|---|
| Mô hình gốc | [Kronos](https://github.com/shiyu-coder/Kronos) (AAAI 2026, arXiv:2508.02739) |
| Mục tiêu | Dự báo nến OHLCV 5 ngày tiếp theo cho 50 mã cổ phiếu VN |
| Dữ liệu | Daily (1D), 50 mã VN50, ~10 năm lịch sử via `vnstock` |
| Kiến trúc | Giữ nguyên 100% Kronos gốc — không thêm head, không sửa loss |
| Trend/Risk/XAI | Business logic trên output (không phải neural heads) |

## Kiến trúc Kronos

```
Nến OHLCVA → Tokenizer (BSQ) → S1 tokens (thô) + S2 tokens (tinh)
  → GPT Decoder (Auto-regressive) → DualHead → Cross-Entropy Loss
  → Decoded nến dự báo OHLCVA
```

- **BSQ (Binary Spherical Quantization):** Mã hóa nến liên tục thành 20-bit binary code, chia thành S1 (xu hướng, 1024 classes) và S2 (chi tiết, 1024 classes).
- **Predictor:** Decoder-only Transformer, sinh S1 trước → S2 sau (conditioned on S1).
- **DualHead:** 1 lớp output duy nhất, loss = Cross-Entropy trung bình trên S1 + S2.

## Pipeline

```
Phase 1: Thu thập dữ liệu
  vnstock → 50 CSV riêng biệt (1 mã/file)

Phase 2: Fine-tune Tokenizer (5-10 epochs, LR=5e-5)
  Adapt BSQ encoder/decoder vào phân phối VN

Phase 3: Fine-tune Predictor (20-30 epochs, LR=1e-6)
  Adapt next-token prediction cho VN tokens

Phase 4: Inference + Business Logic
  Kronos sinh nến × 50-100 samples
  → mean(samples)           = Predicted candle
  → std(samples)            = Volatility
  → percentile(samples, 5%) = VaR
  → sign(Δclose)            = Trend

Phase 5: Walk-forward Backtest
  Train [Year 1→M] → Test [Year M+1]
```

## Cài đặt

```shell
# Clone repo
git clone <repo-url>
cd Stock-VN-forecashing

# Cài đặt dependencies
pip install -r requirements.txt

# Cài thêm vnstock để lấy dữ liệu
pip install vnstock
```

## Cấu hình chính

| Tham số | Giá trị | Lý do |
|---|---|---|
| `lookback_window` | 126 | ≈ 6 tháng — sweet spot cho market regimes |
| `predict_window` | 5 | 1 tuần giao dịch, phù hợp T+2 |
| `tokenizer_lr` | 5e-5 | Micro-adjust, tránh codebook collapse |
| `predictor_lr` | 1e-6 | Tránh catastrophic forgetting |
| `sample_count` | 50-100 | Đủ mịn cho risk estimation |

## Tài liệu

- **[SPEC.md](./SPEC.md)** — Đặc tả kỹ thuật đầy đủ: quyết định thiết kế, lý do, lỗ hổng đã biết.
- **[GEMINI.md](./GEMINI.md)** — Hướng dẫn cho AI coding agent làm việc trên dự án này.

## Model Zoo (Kronos gốc)

| Model | Tokenizer | Context | Params |
|---|---|---|---|
| Kronos-mini | [Kronos-Tokenizer-2k](https://huggingface.co/NeoQuasar/Kronos-Tokenizer-2k) | 2048 | 4.1M |
| Kronos-small | [Kronos-Tokenizer-base](https://huggingface.co/NeoQuasar/Kronos-Tokenizer-base) | 512 | 24.7M |
| Kronos-base | [Kronos-Tokenizer-base](https://huggingface.co/NeoQuasar/Kronos-Tokenizer-base) | 512 | 102.3M |

## Hạn chế đã biết

1. **Overfitting:** 50 chuỗi độc lập rất ít cho Deep Learning. Walk-forward OOS là kiểm tra duy nhất đáng tin.
2. **Error Accumulation:** Nến thứ 5 kém chính xác hơn nến thứ 1 do sinh auto-regressive.
3. **Distribution Shift:** Thị trường VN đang chuyển đổi Frontier → Emerging, cấu trúc thay đổi liên tục.

## Trích dẫn

Dự án này dựa trên mô hình Kronos:

```bibtex
@misc{shi2025kronos,
      title={Kronos: A Foundation Model for the Language of Financial Markets}, 
      author={Yu Shi and Zongliang Fu and Shuo Chen and Bohan Zhao and Wei Xu and Changshui Zhang and Jian Li},
      year={2025},
      eprint={2508.02739},
      archivePrefix={arXiv},
      primaryClass={q-fin.ST},
      url={https://arxiv.org/abs/2508.02739}, 
}
```

## License

MIT License — xem [LICENSE](./LICENSE).
