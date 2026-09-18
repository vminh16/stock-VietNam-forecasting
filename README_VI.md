# Stock-VN-Forecasting

[English](README.md) | [Tiếng Việt](README_VI.md)

Hệ thống nghiên cứu kiểm tra xem mô hình nền chuỗi thời gian Kronos có dự báo
được lợi suất 5 phiên cho rổ VN150 của thị trường chứng khoán Việt Nam hay
không, và việc tinh chỉnh nó cho thị trường này có đem lại gì hơn một công thức
đơn giản hay không.

Đây không phải sản phẩm đầu tư. Mọi kết quả đều không phải khuyến nghị đầu tư.

## Trạng thái

| milestone | trạng thái |
|---|---|
| M0 đóng băng baseline | xong |
| M1 nền dữ liệu VN150 | xong |
| M2 bộ đánh giá nghiên cứu | xong M2.1 đến M2.13; còn bước đóng milestone |
| M3 tinh chỉnh model nhỏ (fine-tune) | tiếp theo |

Kronos-small zero-shot không xếp hạng cổ phiếu tốt hơn công thức đảo chiều 5
phiên trên 683 ngày chưa từng dùng. Đó là lý do cần M3. Chi tiết trong `SPEC.md`.

## Đọc trước

1. [`AGENTS.md`](AGENTS.md): luật vận hành. Bất biến.
2. [`SPEC.md`](SPEC.md): hợp đồng dự án. Dữ liệu, metric, gate, milestone.
3. [`docs/experiments.md`](docs/experiments.md): mọi thí nghiệm kèm config,
   registration, evidence và report trong một bảng.

## Cái gì ở đâu

| đường dẫn | chứa |
|---|---|
| `model/` | code model Kronos. Không sửa khi chưa được duyệt |
| `data_pipeline/` | crawl, kiểm tra và build dataset VN150 |
| `evaluation/` | các runner (`run_*.py`), config, và bộ đánh giá trong `evaluation/research/` |
| `finetune_csv/` | code fine-tune từ M0. Sẽ viết lại trong M3 |
| `tests/` | bộ test |
| `data/raw/`, `data/curated/` | bản crawl đóng băng và dataset đã làm sạch, có kiểm hash |
| `data/evaluation/` | output per-origin và per-date của mọi run M2 |
| `reports/` | artifact đóng băng của từng run. Không bao giờ viết lại |
| `docs/registrations/` | kế hoạch run, commit **trước** khi chạy. Đóng băng |
| `docs/evidence/` | mỗi run cho thấy gì. Chỉ thêm, không sửa tại chỗ |
| `docs/research/` | ghi chú khám phá có ngày. Tự chúng không quyết định gì |
| `docs/runbooks/` | hướng dẫn vận hành, ví dụ benchmark một máy GPU |
| `docs/superpowers/plans/` | kế hoạch triển khai theo milestone |

## Cài đặt

```bash
conda create -n stock python=3.10
conda activate stock
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

`pretrained/Kronos-base` và `pretrained/Kronos-Tokenizer-base` có sẵn trong
repo. Kronos-small thì không; tải từ
[NeoQuasar/Kronos-small](https://huggingface.co/NeoQuasar/Kronos-small) vào
`pretrained/Kronos-small/`.

## Chạy

```bash
python -m pytest tests/ -q
python evaluation/run_zero_shot_screen.py --config evaluation/configs/m2_13_lookback_40.yaml
```

`tests/test_dataloader.py` lỗi import: nó test class dataset của M0 và sẽ được
thay cùng code fine-tune trong M3.

Mỗi run ghi một `manifest.json` gồm câu lệnh (đường dẫn interpreter trong đó cho
biết máy nào chạy), code revision và hash đầu vào. Không được ghép kết quả từ
hai máy khác nhau vào cùng một phép so sánh; xem
`docs/evidence/3.12-m2-12-local-baseline-evidence.md`.

## Các luật quan trọng nhất

- Không chạy train khi chưa commit registration: dữ liệu, fold, candidate,
  ngân sách, luật promote và tiêu chí chấp nhận.
- Được nâng ngưỡng đã đăng ký sau khi thấy kết quả, không bao giờ được hạ.
- Lockbox 2026 đóng cho tới lần đọc cuối cùng.
- Mọi output truy được về dữ liệu, universe, model, config, revision, origin và
  seed.

## Giấy phép

[MIT](LICENSE), kế thừa từ repository Kronos gốc.
