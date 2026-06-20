# Walkthrough: Báo cáo Chi tiết Sửa lỗi Lượng hóa & Cấu trúc lại Hệ thống Đánh giá

Tài liệu này ghi lại các sửa đổi mã nguồn chi tiết và giải pháp kỹ thuật đã triển khai thành công nhằm khắc phục triệt để các lỗi logic lượng hóa trong hệ thống đánh giá của dự án **Stock-VN-Forecasting**.

---

## 1. Kết quả Đánh giá Tokenizer Reconstruction Quality (OOS 2023)

Chúng tôi đã chạy tập kiểm định tokenizer mới trên tập **Validation OOS (Năm 2023)** và thu được kết quả hoàn hảo. Các chỉ số được xuất tự động vào thư mục [reports/tokenizer_benchmarks/](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/tokenizer_benchmarks/):

*   **So sánh sai số phục dựng MAPE giữa các phiên bản (Close Price):**
    - **Pretrained:** `0.4992%`
    - **Tokenizer v1:** `0.4679%`
    - **Tokenizer v2 (Sạch rò rỉ):** `0.4470%` (Tốt nhất)
    - **Trạng thái Pass Criteria:** **PASSED** (Thỏa mãn điều kiện $v_2 < v_1 < \text{pretrained}$ và $\text{MAPE} < 2.0\%$).

*   **So sánh Median MAPE (MdAPE) cho Volume & Amount (Khử nhiễu chia 0):**
    - **Volume MdAPE (v2):** `3.1861%`
    - **Amount MdAPE (v2):** `3.2790%`
    - **Trạng thái Pass Criteria:** **PASSED** (Thỏa mãn điều kiện $\text{MdAPE} < 30\%$ để đảm bảo thông tin thanh khoản được giữ lại trọn vẹn).

---

## 2. Chi tiết các Thay đổi Mã nguồn đã Triển khai

### A. Tệp [benchmark_tokenizer.py](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/evaluation/benchmark_tokenizer.py)
*   **Sửa Bug #1B (Z-score clipping):** Đã thêm `np.clip(x_norm, -5.0, 5.0)` vào dòng 99 để chuẩn hóa đầu vào khớp tuyệt đối với khâu huấn luyện, ngăn sai số phục dựng bị thổi phồng giả tạo.
*   **Sửa Bug #5 & #3 (OOS validation split):** Bổ sung tham số `data_type` vào hàm `collect_windows` lọc theo mốc thời gian `train_end_date` (2023-01-01) và `val_end_date` (2024-01-01) để chỉ đánh giá trên dữ liệu OOS thực sự.
*   **Sửa Bug #4 (Relative Path):** Chuyển đổi thư mục xuất kết quả sang đường dẫn tương đối dự án: [reports/tokenizer_benchmarks/](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/reports/tokenizer_benchmarks/).

### B. Tệp [inference_pipeline.py](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/evaluation/inference_pipeline.py)
*   **Sửa Bug #9 (Outlier Filtering):** Giới hạn lợi suất dự phóng `pred_return_5d` trong khoảng thực tế `[-0.5, 0.5]` để tránh các sai số dự báo lớn phá hỏng RankIC và phân bổ danh mục.
*   **Sửa Bug #2 & B2 (Date-Aligned Non-overlapping Sampling):** 
    - Thuật toán lấy mẫu trong `get_evaluation_indices` được thiết kế lại để chọn các ngày ngẫu nhiên nhưng đảm bảo khoảng cách tối thiểu là **5 ngày giao dịch** (non-overlapping).
    - Tự động đồng bộ số lượng mẫu tối đa lên **2500** (`eval_samples_limit: 2500` tương đương ~50 ngày giao dịch $\times$ 50 cổ phiếu) để tăng kích thước mẫu, giúp các chỉ số Spearman RankIC có ý nghĩa thống kê cao.
*   **Sửa Bug #3 & #10 (Overlapping Backtest & Annualization):**
    - Trong chế độ đánh giá đầy đủ (`final`), hệ thống chỉ thực hiện rebalance và nắm giữ danh mục mỗi 5 ngày một lần (`dates_sorted[::5]`), loại bỏ hoàn toàn tự tương quan chồng lấp gây lạm phát Sharpe/Returns ảo.
*   **Sửa Bug #1, B3a & B3b (Magnitude-Weighted & Min Stocks):**
    - Thêm chiến lược **Magnitude-Weighted** (tỷ trọng theo độ lớn lợi suất dự báo) cho cả danh mục Long (chỉ dùng mã có dự báo dương) và Short (chỉ dùng mã có dự báo âm) kèm Equal-Weight mặc định.
    - Lọc nghiêm ngặt `MIN_STOCKS_PER_DATE = 45` để loại bỏ các ngày thiếu dữ liệu giao dịch làm lệch so sánh với Benchmark VN50 EW.
*   **Sửa Bug B5 & B6 (Paired T-test & Overlap Diagnostics):**
    - Hệ thống lưu trữ `per_date_metrics.csv` cho mỗi đợt chạy. Khi chạy mô hình Fine-tuned, nó sẽ tự động nạp dữ liệu Baseline, thực hiện **Paired t-test** (cho DA và RankIC) và in độ tương đồng Top-10 Long portfolio (Overlap ratio) trực tiếp lên console.

---

## 3. Cập nhật các Tệp cấu hình Tối giản
Đã tăng giới hạn mẫu đánh giá `eval_samples_limit` lên **2500** trong cả hai tệp cấu hình duy nhất:
1. [evaluation/configs/inference.yaml](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/evaluation/configs/inference.yaml) (Dành cho mô hình Baseline)
2. [evaluation/configs/inference_finetuned.yaml](file:///c:/Users/USER/Desktop/Stock-VN-forecashing/evaluation/configs/inference_finetuned.yaml) (Dành cho mô hình Fine-tuned)
