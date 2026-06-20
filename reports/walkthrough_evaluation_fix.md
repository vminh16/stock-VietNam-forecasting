# Walkthrough: Sửa lỗi Suy biến Danh mục & Lưu trữ Artifacts

Tài liệu này ghi lại các thay đổi và giải pháp kỹ thuật nhằm khắc phục hiện tượng suy biến danh mục (portfolio degeneracy) trong quá trình đánh giá ở chế độ phát triển (`dev`), đồng thời lưu trữ các báo cáo so sánh (artifacts) vào các thư mục tương ứng trong không gian làm việc của người dùng.

---

## 1. Lưu trữ & Tổ chức lại Thư mục Báo cáo (Reports)

Các artifacts benchmark sinh ra trong quá trình kiểm định được tổ chức lại gọn gàng trong các thư mục gợi nhớ như sau:

- **Đánh giá tái cấu trúc Tokenizer (Reconstruction Error):** [reports/tokenizer_benchmarks/](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/tokenizer_benchmarks/)
  - [tokenizer_benchmark.csv](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/tokenizer_benchmarks/tokenizer_benchmark.csv)
  - [tokenizer_benchmark_mae.csv](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/tokenizer_benchmarks/tokenizer_benchmark_mae.csv)
  - [tokenizer_benchmark_mape.csv](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/tokenizer_benchmarks/tokenizer_benchmark_mape.csv)
  - [tokenizer_benchmark_mdape.csv](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/tokenizer_benchmarks/tokenizer_benchmark_mdape.csv)

- **Đánh giá Mô hình Baseline:** [reports/baseline_model_evaluation/](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/baseline_model_evaluation/)
  - Báo cáo số liệu: [baseline_metrics.csv](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/baseline_model_evaluation/baseline_metrics.csv)
  - Đồ thị backtest: [backtest_performance.png](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/baseline_model_evaluation/backtest_performance.png)

- **Đánh giá Mô hình Fine-tuned:** [reports/finetuned_model_evaluation/](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/finetuned_model_evaluation/)
  - Báo cáo số liệu: [finetuned_metrics.csv](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/finetuned_model_evaluation/finetuned_metrics.csv)
  - Đồ thị backtest: [finetuned_backtest_performance.png](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/finetuned_model_evaluation/finetuned_backtest_performance.png)

---

## 2. Phân tích lỗi Suy biến Danh mục (Portfolio Degeneracy)

### Hiện tượng
Trong chế độ `dev` (`limit = 500`), các chỉ số hiệu quả danh mục Long-Only, Long-Short và Benchmark (VN50 EW) trùng khớp hoặc tương đương một cách đáng ngờ. Sharpe của danh mục Long-Short giảm cực sâu ($\approx -300$ đến $-400$) trong khi tỷ suất sinh lợi xấp xỉ $-15.0\%$.

### Nguyên nhân gốc rễ
1. Hàm lấy chỉ số `get_evaluation_indices` cũ sử dụng phương pháp **Stratified Sampling độc lập theo cổ phiếu**. Với `limit = 500` và 50 mã cổ phiếu, hệ thống lấy ngẫu nhiên 10 cửa sổ (windows) cho mỗi mã trên toàn bộ khoảng thời gian 250 ngày giao dịch (OOS).
2. Do việc lấy mẫu độc lập, tại một ngày dự báo $t$, số lượng cổ phiếu có cửa sổ mẫu cực kỳ ít (thường chỉ từ 1 đến 2 mã, tối đa dưới 10 mã).
3. Khi tính toán danh mục Top/Bottom 20%:
   - Hàm `nlargest(10, 'pred_return_5d')` và `nsmallest(10, 'pred_return_5d')` đều chọn toàn bộ số cổ phiếu ít ỏi hiện có trên ngày $t$ đó.
   - Danh mục Long (Top 10) và danh mục Short (Bottom 10) trở nên **hoàn toàn trùng khớp** về mặt thành phần cổ phiếu.
4. Hệ quả toán học:
   - Tỷ suất sinh lợi Long-Short thô: $R_{Long} - R_{Short} = 0$.
   - Tỷ suất sinh lợi Long-Short ròng: $- (\text{fees}_{Long} + \text{fees}_{Short}) \approx -2 \times 0.15\% \times \text{turnover} \approx -15.0\%$ (tính theo năm do quay vòng danh mục liên tục).
   - Độ lệch chuẩn (standard deviation) của tỷ suất sinh lợi cực kỳ nhỏ (chỉ có nhiễu số học), dẫn đến Sharpe ratio đạt mức âm khổng lồ.

---

## 3. Giải pháp: Date-Aligned Sampling

Chúng tôi đã sửa đổi hàm `get_evaluation_indices` trong tệp [evaluation/inference_pipeline.py](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/evaluation/inference_pipeline.py#L166-L198) để chuyển sang cơ chế **Date-Aligned Sampling** khi chạy ở chế độ giới hạn mẫu (`limit > 0`):

1. **Gom nhóm theo ngày dự báo:** Hệ thống nhóm toàn bộ các cửa sổ dữ liệu của tất cả cổ phiếu theo ngày kết thúc lookback ($t$).
2. **Lấy mẫu theo cụm ngày:** Xáo trộn danh sách ngày ngẫu nhiên và chọn toàn bộ cổ phiếu thuộc các ngày đó cho đến khi tổng số lượng cửa sổ đạt hoặc vượt quá mức `limit`.
3. **Kết quả:** Trên mỗi ngày dự báo được chọn, hệ thống giữ lại đầy đủ thông tin của toàn bộ 50 cổ phiếu (hoặc tất cả các mã có dữ liệu tại thời điểm đó). Điều này đảm bảo:
   - Danh mục `nlargest(10)` và `nsmallest(10)` là hoàn toàn phân biệt (disjoint).
   - Các chỉ số Sharpe, MDD, returns phản ánh đúng sức mạnh thực tế của mô hình chứ không bị suy biến do thiếu mã cổ phiếu.

---

## 4. Quản lý cấu hình tối giản

Theo đúng yêu cầu của bạn để tránh phát sinh quá nhiều cấu hình rác, chúng tôi chỉ sử dụng duy nhất **2 tệp cấu hình** cho toàn bộ quá trình eval và inference:
1. [evaluation/configs/inference.yaml](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/evaluation/configs/inference.yaml): Dành cho mô hình **Baseline** (sử dụng tokenizer pre-trained gốc và mô hình base, xuất kết quả ra `reports/baseline_model_evaluation/`).
2. [evaluation/configs/inference_finetuned.yaml](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/evaluation/configs/inference_finetuned.yaml): Dành cho mô hình **Fine-tuned** (sử dụng checkpoint tokenizer_v2 và basemodel_v2, xuất kết quả ra `reports/finetuned_model_evaluation/`).
