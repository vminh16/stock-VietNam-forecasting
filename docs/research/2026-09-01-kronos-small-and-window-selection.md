# Nghiên cứu primary-source: Kronos-small vs Kronos-base, lựa chọn lookback L và horizon H

> **Ngày:** 2026-09-01
> **Loại tài liệu:** research note (primary-source review), KHÔNG phải spec, KHÔNG phải evidence artifact.
> **Trạng thái:** tham khảo. Không sửa `SPEC.md`, không thay đổi bất kỳ file nào khác trong repo.

## Quy ước thư mục (chọn trong tài liệu này)

Repo hiện có hai nơi chứa văn bản:

- `docs/superpowers/plans/` — implementation plan theo milestone;
- `reports/` — evidence artifact sinh ra từ code, có hash và provenance.

Research note KHÔNG thuộc cả hai loại đó: nó không phải kế hoạch thực thi và cũng không phải
artifact tái tạo được từ pipeline. Vì vậy tài liệu này mở thư mục mới `docs/research/`, dùng cho
các ghi chú khảo sát tài liệu gốc (primary literature) và đọc mã nguồn. Quy tắc đề xuất cho thư
mục này: mỗi file đặt tên `YYYY-MM-DD-<chủ-đề>.md`, mọi claim load-bearing phải có URL hoặc
`file:line`, và mọi suy luận của người viết phải được dán nhãn rõ ràng.

---

## 0. Tóm tắt: cái gì đã được xác lập và cái gì thì không

### 0.1 Được xác lập bởi primary sources

| # | Kết luận | Nguồn |
|---|---|---|
| 1 | Kronos pre-train **đúng ba** kích thước: small 24.7M (8 layers, d_model 512), base 102.3M (12 layers, d_model 832), large 499.2M (18 layers, d_model 1664). Vocab `2^20` cho cả ba. | Paper Table 1 |
| 2 | Context length pre-training bị giới hạn cứng ở **512 tokens** cho small/base/large ("we limit the maximum context length to 512 tokens"). | Paper §"Model Training"; HF model card; GitHub README |
| 3 | **Có** benchmark per-size công bố: Tables 14/16/18 (forecasting) và Table 10 (investment simulation) đều tách riêng `Kronos_S`, `Kronos_B`, `Kronos_L`. | Paper Appendix F |
| 4 | Trên metric chính (price-series RankIC, trung bình 11 nhóm tài sản), khoảng cách small→base là **rất nhỏ**: 0.0254 → 0.0258 (+1.6% tương đối). IC: 0.0431 → 0.0435 (+0.9%). | Paper Table 14 |
| 5 | Thứ hạng small vs base **không ổn định** theo thị trường. Trên XKLS (Malaysia, out-of-distribution), **small thắng base**: RankIC 0.0215 vs 0.0149. | Paper Table 14 |
| 6 | Tác giả có tuyên bố scaling: "as the model size scales up, performance on these tasks consistently improves". Nhưng tuyên bố này đúng nhất ở mức **large**, không phải ở bước small→base. | Paper §4.2 |
| 7 | Mọi setting **daily-frequency** mà tác giả từng công bố dùng lookback trong khoảng **40–96 bars**: forecasting 40, investment simulation 90, generation 96, official finetune config 90. | Paper Table 8, Appendix D; `finetune/config.py` |
| 8 | Mọi setting daily-frequency mà tác giả từng công bố dùng horizon **10–35 bars**: forecasting 12, investment simulation 10, generation 35. | như trên |
| 9 | Official finetune script của tác giả mặc định fine-tune **Kronos-small** (không phải base). | `finetune/config.py:102` |
| 10 | Corpus pre-training gồm 45 sàn, ~12.11B K-line records, **KHÔNG có Việt Nam** (không có HOSE/HNX/UPCoM; chuỗi "Vietnam"/"Viet"/"HOSE"/"HNX" xuất hiện 0 lần trong toàn bộ paper). | Paper Table 13 |
| 11 | Với Transformer time-series nói chung, tăng lookback **không** tự động cải thiện. Và trên dataset tài chính (Exchange-Rate), lookback dài **không** cải thiện, tác giả quy cho "low information-to-noise ratio in such financial data". | Zeng et al. 2023, §5.2 và Appendix |
| 12 | One-standard-error rule có nguồn gốc primary rõ ràng: Breiman et al. (1984) §3.4.3; được định nghĩa lại trong ESL (Hastie et al.). | xem §5 |

### 0.2 KHÔNG có bằng chứng công bố (open empirical question)

Đây là phần quan trọng nhất. Những mục dưới đây **không tồn tại** trong tài liệu gốc; bất kỳ con
số nào được đưa ra ở đây sẽ là bịa đặt.

| # | Không tồn tại | Hệ quả |
|---|---|---|
| A | **Không có lookback-length ablation** trong paper Kronos. Ablation của họ chỉ gồm: modeling paradigm (Q1), vocabulary size (Q2), tokenizer architecture (Appendix E), và inference hyperparameters T/top-p/N. | Không có bất kỳ bằng chứng công bố nào ủng hộ hay bác bỏ L=63 vs L=126. |
| B | **Không có horizon ablation** trong paper Kronos. Horizon được cố định theo tần suất (Table 8), không quét. | Không có bằng chứng công bố về suy giảm chất lượng theo H cho Kronos. |
| C | **Không có confidence interval, standard error, hay significance test nào** cho khoảng cách small vs base. Tables 14/16/18/10 là point estimate trần. | Chênh lệch RankIC 0.0004 không thể coi là "base tốt hơn". Cũng không thể coi là "small non-inferior". |
| D | **Không có benchmark nào cho `Kronos-mini`** (4.1M, context 2048, Tokenizer-2k). Chuỗi "mini" xuất hiện 0 lần trong paper; Table 1 chỉ có small/base/large. | Biến thể duy nhất có context 2048 (đủ chỗ cho L rất dài) hoàn toàn chưa được đánh giá. |
| E | **Không có kết quả nào cho thị trường Việt Nam**, và VN không nằm trong corpus pre-training. | Toàn bộ use case này là out-of-distribution ở cấp sàn giao dịch. Không có transfer evidence nào để mượn. |
| F | **Không có kết quả tách riêng theo tần suất.** Table 14 ghi rõ kết quả mỗi asset đã "averaged over all tested frequencies" (9 tần suất từ 5min đến Daily). | Không thể trích xuất "Kronos-small ở daily frequency tốt thế nào" từ paper. Con số +1.6% ở mục 0.1(4) bị pha loãng bởi 8 tần suất intraday. |
| G | **Không có scaling law định lượng** (không có fit L(N), không có compute-optimal frontier). Câu §4.2 chỉ là quan sát định tính trên 3 điểm. | "Pretraining có thể làm mô hình lớn hơn sample-efficient hơn" (`SPEC.md:275`) vẫn là giả thuyết chưa kiểm chứng cho Kronos. |
| H | **Không có literature primary source nào cho câu "H=5 daily là horizon dễ dự báo nhất"** — vì đó không phải một mệnh đề có thể có nguồn; nó phụ thuộc thị trường và mô hình. | H=5 phải được biện minh bằng utility sản phẩm, không bằng literature. |

### 0.3 Phát hiện đáng chú ý (breakthrough, nếu có)

Có ba phát hiện thực sự làm thay đổi cách đọc các con số hiện tại:

1. **Không setting daily nào của tác giả dùng lookback ≥ 126.** Toàn bộ dải là 40–96. `L=126`
   nằm **ngoài** mọi cấu hình daily đã công bố; `L=63` nằm **bên trong** dải đó. Đây là đảo ngược
   trực giác hiện tại của repo, nơi 126 là "incumbent" và 63 là "cheaper candidate".
2. **Trên sàn out-of-distribution gần VN nhất về mặt cấu trúc (XKLS, Malaysia), Kronos-small
   đánh bại Kronos-base trên cả IC lẫn RankIC.** Đây là bằng chứng công bố mạnh nhất ủng hộ
   lựa chọn small — nhưng nó cũng cho thấy thứ hạng small/base không ổn định, tức là không thể
   suy ra thứ hạng cho VN.
3. **`L` trong repo không phải chỉ là context length — nó đồng thời là normalization window.**
   `data_pipeline/transforms.py:11-15` tính mean/std trên đúng `lookback_length` hàng đầu tiên;
   `model/kronos.py:544` tính mean/std trên toàn bộ input window. Do đó so sánh L=63 vs L=126
   **không** là so sánh thuần context — nó thay đổi cả thang z-score point-in-time. Điều này chưa
   được ghi nhận ở `SPEC.md:383-388`.

---

## 1. RQ1 — Kronos-small có phải candidate hợp lệ cho development/deployment không?

### 1.1 Những gì tác giả Kronos thực sự công bố về model family

**Kích thước và kiến trúc** (Paper Table 1, https://arxiv.org/html/2508.02739v1):

| Model | Layers | d_model | d_ff | Heads | Vocab (2^k) | Params |
|---|---:|---:|---:|---:|---:|---:|
| Kronos small | 8 | 512 | 1024 | 8 | 20 | 24.7M |
| Kronos base | 12 | 832 | 2048 | 16 | 20 | 102.3M |
| Kronos large | 18 | 1664 | 3072 | 32 | 20 | 499.2M |

Đối chiếu với repo: `pretrained/Kronos-base/config.json` khai báo `d_model 832`, `n_layers 12`,
`n_heads 16`, `ff_dim 2048`, `s1_bits 10`, `s2_bits 10` (→ vocab hiệu dụng `2^20` chia thành hai
sub-vocab `2^10`). **Trùng khớp hoàn toàn với Table 1.** Cấu hình local là thật, không phải phỏng đoán.

**Corpus pre-training:** "over 12 billion K-line records from 45 global exchanges", 7 tần suất
lấy mẫu, cutoff dữ liệu pre-training tới **tháng 6/2024** (Paper Appendix D: "The pre-training data
for Kronos extends up to June 2024"). Table 13 liệt kê chi tiết từng sàn; tổng xấp xỉ 96,569
instrument và 12.11B bản ghi.

**Việt Nam không có trong danh sách.** Tôi đã grep toàn văn bản paper (đã strip HTML) cho
`Vietnam`, `Viet`, `Ho Chi`, `Hanoi`, `HOSE`, `HNX` — tất cả trả về **0 lần xuất hiện**. Các sàn
Đông Nam Á có mặt là Thailand, Indonesia (XIDX), Kuala Lumpur (XKLS), Philippine, Singapore không
xuất hiện tường minh. Vì vậy:

> **Kết luận (primary source):** VN150 là out-of-distribution ở cấp exchange đối với mọi
> checkpoint Kronos. Không có con số nào trong paper có thể được diễn giải như một dự báo
> về hiệu năng trên HOSE/HNX/UPCoM.

**Ghi chú về in/out-of-distribution:** paper chỉ định XIDX, XKLS, XTAI là "out-of-distribution
exchanges" cho phần đánh giá (Appendix D), trong khi Table 13 lại liệt kê Indonesia Stock Exchange
và Kuala Lumpur Stock Exchange trong dataset thu thập. Paper **không** giải thích rõ mâu thuẫn
biểu kiến này (nhiều khả năng các sàn OOD bị giữ lại khỏi pre-training nhưng vẫn nằm trong bảng
thống kê dữ liệu thu thập). *Đây là suy luận của tôi, paper không nói.*

### 1.2 Benchmark per-size: CÓ tồn tại, và đây là các con số

Trái với giả định "tác giả không công bố per-size benchmark", họ **có** — trong Appendix F.
Dưới đây là hàng `Average` (trung bình trên 11 nhóm tài sản, mỗi nhóm đã trung bình qua mọi tần suất).

**Table 14 — Price series forecasting** (cao hơn là tốt hơn):

| | Kronos_S | Kronos_B | Kronos_L |
|---|---:|---:|---:|
| IC (Average) | 0.0431 | 0.0435 | 0.0440 |
| RankIC (Average) | 0.0254 | 0.0258 | 0.0267 |
| `1st` Count (trên 11 nhóm × 2 metric) | 4 | 7 | 10 |

**Table 16 — Return forecasting:**

| | Kronos_S | Kronos_B | Kronos_L |
|---|---:|---:|---:|
| IC (Average) | 0.0665 | 0.0682 | 0.0702 |
| RankIC (Average) | 0.0622 | 0.0634 | 0.0675 |
| `1st` Count | 2 | 3 | 10 |

**Table 18 — Realized volatility forecasting** (MAE thấp hơn tốt hơn, R² cao hơn tốt hơn):

| | Kronos_S | Kronos_B | Kronos_L |
|---|---:|---:|---:|
| MAE (Average) | 0.0384 | 0.0372 | 0.0370 |
| R² (Average) | **0.2490** | 0.2470 | 0.2624 |
| `1st` Count | 4 | 2 | 11 |

**Table 10 — Investment simulation** (A-share, daily, L=90, H=10, min holding 5 ngày, cost 0.15%):

| | Kronos_S | Kronos_B | Kronos_L |
|---|---:|---:|---:|
| CSI300 AER / IR | 0.1805 / 1.2394 | 0.1911 / 1.3782 | 0.2193 / 1.4177 |
| CSI800 AER / IR | 0.1772 / 1.6050 | 0.1867 / 1.6652 | 0.1974 / 1.8805 |
| Average AER / IR | 0.1789 / 1.4222 | 0.1889 / 1.5217 | 0.2084 / 1.6491 |

**Trên ba sàn out-of-distribution** (Table 14, price forecasting, IC / RankIC):

| Sàn | Kronos_S | Kronos_B | Kronos_L |
|---|---|---|---|
| XIDX (Indonesia) | 0.0551 / 0.0214 | 0.0551 / 0.0216 | 0.0573 / 0.0223 |
| XKLS (Malaysia) | **0.0411 / 0.0215** | 0.0408 / 0.0149 | 0.0466 / 0.0167 |
| XTAI (Taiwan) | 0.0424 / 0.0301 | 0.0443 / 0.0320 | 0.0448 / 0.0342 |

### 1.3 Đọc các con số này một cách trung thực

1. **Khoảng cách small→base trên forecasting là rất nhỏ.** Price-series RankIC: +0.0004 tuyệt đối,
   +1.6% tương đối. Return RankIC: +0.0012, +1.9%. Đây là mức chênh mà **không thể** phân biệt với
   nhiễu nếu không có CI — và paper **không cung cấp CI nào**.
2. **Khoảng cách base→large lớn hơn nhiều** (price RankIC +3.5%, return RankIC +6.5%, và `1st Count`
   nhảy từ 7 lên 10). Nói cách khác, câu "performance consistently improves as model size scales up"
   (§4.2) được dữ liệu ủng hộ chủ yếu ở bước **base→large**, không phải small→base.
3. **Thứ hạng small/base bị đảo ở hai chỗ:** volatility R² (small 0.2490 > base 0.2470) và XKLS
   (small thắng cả IC lẫn RankIC, chênh RankIC 44% tương đối). Với 3 điểm scaling và 0 CI, không
   thể phân biệt "small ≈ base" với "small hơi kém base".
4. **Investment simulation là chỗ duy nhất base thắng small một cách nhất quán** (AER +5.6%,
   IR +7.0% tương đối trên Average) — và đó cũng là task **daily-only** duy nhất được tách per-size.
   Đây là bằng chứng bất lợi nhẹ cho small nếu mục tiêu là ranking-oriented radar trên daily bars.
   Nhưng nó chạy trên A-share (in-distribution) với L=90/H=10, không phải VN với L=126/H=5.

### 1.4 Bằng chứng "hành vi tác giả" ủng hộ small

`finetune/config.py` trong repo chính thức (https://github.com/shiyu-coder/Kronos, master):

```
self.pretrained_tokenizer_path = "path/to/your/Kronos-Tokenizer-base"   # line 101
self.pretrained_predictor_path = "path/to/your/Kronos-small"            # line 102
```

Reference fine-tuning pipeline của chính tác giả (ví dụ A-share/Qlib) mặc định adapt
**Kronos-small**, không phải base. Đây không phải là bằng chứng thống kê, nhưng nó là bằng chứng
"đây là con đường tác giả kỳ vọng người dùng đi", và nó ủng hộ trực tiếp lựa chọn tại
`SPEC.md:269`.

### 1.5 Những gì code trong repo xác lập (và một khoảng trống thực thi)

- Kiến trúc `Kronos` là decoder-only, RMSNorm pre-LN, SwiGLU FFN (`model/module.py:271-281`),
  causal self-attention với RoPE (`model/module.py:315-353`), `DependencyAwareLayer` cross-attention
  cho s2 (`model/module.py:446-462`), `DualHead` xuất `2^10` logits cho mỗi sub-token
  (`model/module.py:486-513`). Không có positional embedding tuyệt đối → **không có giới hạn độ dài
  cứng trong kiến trúc**.
- **Khoảng trống thực thi:** `pretrained/` hiện chỉ có `Kronos-base` và `Kronos-Tokenizer-base`.
  **Chưa có `Kronos-small` trong repo.** M2.3 muốn so sánh zero-shot small vs base thì phải tải
  `NeoQuasar/Kronos-small` trước — cả hai dùng chung `Kronos-Tokenizer-base` nên không cần tokenizer mới.
- Ước lượng chi phí (suy luận của tôi, tính từ Table 1 + `model/module.py`): FLOPs suy luận của base
  ≈ **4.3–4.5×** small ở cùng L (per-layer linear cost tỉ lệ `4d² + 3·d·d_ff`, nhân số layer;
  512→832 và 8→12 layers). Con số này gần với tỉ lệ tham số 102.3/24.7 = 4.14×.

### 1.6 Kết luận RQ1

- **Kronos-small là một research candidate hợp lệ và có nền tảng.** Bằng chứng: (a) khoảng cách
  small→base trên forecasting metric rất nhỏ; (b) small thắng base trên volatility R² và trên
  XKLS; (c) pipeline fine-tune chính thức mặc định small; (d) chi phí ~4.3× thấp hơn.
- **Nhưng "non-inferior" thì CHƯA được chứng minh ở bất kỳ đâu.** Không có CI công bố, không có
  kết quả daily-only tách per-size ngoài investment simulation (nơi base thắng), và không có dữ
  liệu VN. `SPEC.md:273-276` đã nói đúng điều này — nghiên cứu này xác nhận rằng cảnh báo đó
  không thể được gỡ bằng literature, chỉ bằng thí nghiệm của chính dự án.
- **Mâu thuẫn với SPEC cần ghi nhận:** `SPEC.md:268-271` gọi Kronos-base là "Frozen zero-shot
  reference" và small là "Primary development and deployment candidate". Bằng chứng công bố
  (Table 10, task daily gần với radar nhất) nghiêng nhẹ về **base**. Việc chọn small là quyết định
  **operational/cost**, không phải quyết định dựa trên bằng chứng hiệu năng — và SPEC nên nói
  thẳng như vậy.

---

## 2. RQ2 — Lookback nào là defensible?

### 2.1 Context length pre-training: 512, và đây là câu nguyên văn

> "Considering resource constraints and practical deployment scenarios, we limit the maximum
> context length to 512 tokens. Nevertheless, this design remains fully compatible with arbitrary
> forecasting horizons by leveraging K-line data at varying frequencies; for instance, using
> 1-minute data for short-term forecasting and daily data for weekly or monthly predictions."
> — Paper §"Model Training"

Model card HuggingFace và GitHub README lặp lại: "The `max_context` for `Kronos-small` and
`Kronos-base` is **512**. ... For optimal performance, it is recommended that your input data
length (i.e., `lookback`) does not exceed this limit. The `KronosPredictor` will automatically
handle truncation for longer contexts."
(`pretrained/Kronos-base/README.md:55`; https://huggingface.co/NeoQuasar/Kronos-base)

**Cả L=63 lẫn L=126 đều nằm an toàn dưới 512.** Không có ràng buộc kiến trúc nào bị vi phạm.

### 2.2 Code trong repo thực sự enforce cái gì

- `max_context` là **tham số mặc định của `KronosPredictor.__init__`, không phải thuộc tính của
  checkpoint**: `model/kronos.py:484` → `def __init__(self, model, tokenizer, device=None, max_context=512, clip=5)`.
  Nó không được đọc từ `config.json` (xem `pretrained/Kronos-base/config.json` — không có trường
  context length nào).
- Truncation là **im lặng và giữ phần gần nhất**: `model/kronos.py:410-414` lấy
  `start_idx = max(0, initial_seq_len - max_context)`, tức là drop phần lịch sử **cũ nhất**.
  `model/kronos.py:459-463` cũng chỉ decode `max_context` token cuối. Với L ≤ 512, không có gì bị cắt.
- RoPE trong repo cache theo `seq_len` động (`model/module.py:293-301`), **không có giới hạn cứng**.
  Nghĩa là chạy L > 512 sẽ không lỗi — nó chỉ bị `KronosPredictor` cắt xuống 512, hoặc nếu bỏ qua
  predictor thì sẽ chạy ngoài regime pre-training mà không có cảnh báo. *(Suy luận của tôi từ code.)*
- Repo đang đặt `lookback_window: 126`, `predict_window: 5`, `max_context: 512` tại
  `evaluation/configs/inference.yaml:3-5`; M2.1 khoá `lookbacks: [63, 126]`
  (`evaluation/configs/m2_1_origins.yaml:8`) và `evaluation/research/origins.py:98-99` raise nếu
  khác `(63, 126)`.

### 2.3 Điểm quan trọng nhất: L cũng là normalization window

Đây là phát hiện từ đọc code, **không** có trong SPEC.

- `data_pipeline/transforms.py:11-15`:
  ```
  lookback = values[:lookback_length]
  mean = lookback.mean(axis=0)
  raw_std = lookback.std(axis=0)
  normalized = np.clip((values - mean) / (scale + 1e-5), -clip, clip)
  ```
- `model/kronos.py:544-547`: `x_mean, x_std = np.mean(x, axis=0), np.std(x, axis=0)` trên **toàn bộ**
  input window, rồi clip `[-5, 5]`.
- Paper Appendix C xác nhận đây đúng là preprocessing của tác giả: "z-score normalization
  independently to each of the D feature dimensions ... clipped to the range [-5, 5]".

**Hệ quả:** so sánh L=63 vs L=126 không phải là ablation thuần về context length. Nó đồng thời thay
đổi (a) số bar mà attention nhìn thấy, (b) mean/std dùng để chuẩn hoá, (c) tỉ lệ giá trị bị clip.
Repo đã đo (b)/(c) một phần: clipping ảnh hưởng 0.0667% giá trị ở L=63 và 0.0942% ở L=126
(`.codex/skills/vn-stock-market-radar/references/project-context.md:52-53`). Khi báo cáo kết quả
ablation L, **phải** gọi nó là "lookback configuration" chứ không phải "context length", nếu không
kết luận sẽ bị attribute sai.

### 2.4 Chính tác giả Kronos dùng lookback nào cho daily?

Đây là bằng chứng trực tiếp nhất và nó khá dứt khoát.

| Nguồn | Tần suất | Look-back | Horizon |
|---|---|---:|---:|
| Paper Table 8 (forecasting benchmark) | Daily | **40** | 12 |
| Paper Appendix D (investment simulation, A-share) | Daily | **90** | 10 |
| Paper Appendix D (synthetic generation) | Daily | **96** | 35 |
| `finetune/config.py:20-21` (official finetune, CSI300 daily) | Daily | **90** | 10 |

Để đối chiếu, các setting intraday: 5min 480/96, 10min 240/48, 15min 160/32, 20min 120/24,
40min 90/24, 1h 80/12, 2h 60/12, 4h 90/18 (Paper Table 8).

> **Kết luận:** dải lookback daily đã công bố của tác giả là **[40, 96]**. `L=63` nằm **bên trong**
> dải này. `L=126` nằm **hoàn toàn bên ngoài** — cao hơn 31% so với giá trị daily lớn nhất họ từng
> dùng (96) và gấp 3.15× giá trị họ dùng cho chính benchmark forecasting (40).

Điều này không chứng minh L=126 tệ. Nó chỉ nói rằng **L=126 không có bất kỳ nguồn gốc nào từ tài
liệu Kronos**, trong khi L=63 thì có (nằm giữa 40 và 90). Trực giác hiện tại của repo đang ngược
với dữ liệu: SPEC coi 126 là "incumbent" và 63 là "cheaper candidate" (`SPEC.md:366`), nhưng theo
literature thì 63 mới là lựa chọn có nền tảng còn 126 mới là candidate mạo hiểm.

### 2.5 Literature về lựa chọn lookback trong time-series forecasting

**Zeng et al. (2023), "Are Transformers Effective for Time Series Forecasting?"** (arXiv 2205.13504,
AAAI 2023). Đây là primary source về câu hỏi "lookback dài có giúp không".

- Thiết kế: quét `L ∈ {24, 48, 72, 96, 120, 144, 168, 192, 336, 504, 672, 720}` với T=720 (§5.2).
- Kết quả chung: "existing Transformer-based models' performance deteriorates or stays stable when
  the look-back window size increases. In contrast, the performances of all LTSF-Linear are
  significantly boosted with the increase of look-back window size."
- **Và đặc biệt cho dữ liệu tài chính** (Appendix, thảo luận Figure 6): "the results of
  Exchange-Rate do not show improved results with a long look-back window ... and we attribute it
  to the **low information-to-noise ratio in such financial data**."

**Nie et al. (2023), PatchTST** (arXiv 2211.14730, ICLR 2023) là phản đề: với patching +
channel-independence, "our PatchTST consistently reduces the MSE scores as the receptive field
increases" (§ Varying Look-back Window; Table 9). Nhưng lưu ý: PatchTST **cố ý loại** dataset
Exchange-Rate khỏi benchmark, với lý do nêu nguyên văn: "if a market is efficient, the best
prediction for x_t will be just x_{t-1} (Fama 1970) ... Zeng et al. 2022 shows that by simply
repeating the last value in the look-back window, the MSE loss on exchange-rate dataset can
outperform or be comparable to the best results. Therefore, we are prudent in containing it into
our benchmark."

> **Đọc hai nguồn này cùng nhau:** bằng chứng "lookback dài giúp" đến từ các dataset có
> signal-to-noise cao (Electricity, Traffic, Weather). Trên dữ liệu tài chính, cả hai nhóm tác giả
> đều ghi nhận rằng lookback dài không giúp và rằng naive persistence là baseline rất mạnh. Đây
> chính xác là điều dự án đã tự quan sát ở M2.2 (`persistence` đạt DA 55.96 ở fold 2022,
> `SPEC.md:144-149`).

**Không có nguồn primary nào** ủng hộ một giá trị lookback cụ thể cho daily VN equities. Đó là câu
hỏi thực nghiệm thuần tuý.

### 2.6 Sample-count và compute trade-off: các con số thật của repo

`SPEC.md:383-388` liệt kê 4 chi phí của lookback dài. Kiểm chứng bằng số liệu repo:

1. **"reduces valid windows linearly"** — Repo đo được: 247,999 nominal `63/5` windows vs 229,734
   nominal `126/5` windows (`project-context.md:42`). Đó là giảm **7.4%**, không phải giảm lớn.
   Lý do: hầu hết segment dài hơn 126 rất nhiều. **Với dataset này, sample-count không phải là
   lý do mạnh để chọn L=63.**
   Quan trọng hơn: registry M2.1 đã lọc về các origin hỗ trợ **cả hai** L (133,937 origins,
   `project-context.md:57-60`), nên trong so sánh M2.x, sample count là **hoàn toàn bằng nhau**.
   Chi phí này đã bị vô hiệu hoá bởi thiết kế.
2. **"increases attention compute approximately as O(L^2)"** — đúng về tiệm cận nhưng **gây hiểu
   lầm ở quy mô này**. Tính từ `model/module.py` (*suy luận số học của tôi*), chi phí mỗi layer
   mỗi forward: phần tuyến tính `(4d² + 3·d·d_ff)·L`, phần bậc hai `2d·L²`.
   Với Kronos-small (d=512, d_ff=1024): L=63 → 165.1M + 4.1M; L=126 → 330.3M + 16.3M.
   Tỉ lệ tổng chi phí 126/63 = **2.05×**, không phải 4×. Phần bậc hai chỉ chiếm 2.4% (L=63) đến
   4.7% (L=126) tổng chi phí. Với base (d=832, d_ff=2048) tỉ lệ là 2.03×.
   → Nhân đôi L làm **nhân đôi** chi phí, không phải nhân bốn. Chi phí đổi model size
   (small→base ≈ 4.3×) lớn hơn nhiều so với chi phí đổi L (63→126 ≈ 2×).
3. **"mixes stale regimes with the current state"** — được literature ủng hộ gián tiếp (Zeng et al.
   về low SNR tài chính) nhưng không có nguồn định lượng. Với L=126 ≈ 6 tháng giao dịch và
   L=63 ≈ 3 tháng, đây là một khác biệt regime có thật trên thị trường VN 2022-2025 (VN-Index
   giảm mạnh 2022 rồi hồi phục) — nhưng đó là quan sát, không phải bằng chứng.
4. **"increases sensitivity to short listing histories"** — repo đã xác nhận: `TCX`, `VCK`, `VPX`
   không có origin hợp lệ nào vì lịch sử ngắn (`project-context.md:60-61`). Nhưng vì registry
   chung đã áp `max_lookback = 126` (`evaluation/research/origins.py:181-194`), chi phí này cũng
   đã bị "trả trước" — L=63 hiện KHÔNG được hưởng lợi từ universe rộng hơn trong registry M2.1.
   *Đây là một hạn chế của thiết kế M2.1 cần ghi nhận: nó đo L một cách công bằng nhưng cố tình
   che giấu một trong những lợi thế thật của L nhỏ.*

### 2.7 One-standard-error rule: nguồn gốc và một cảnh báo quan trọng

`SPEC.md:398-399` quy định: "Select `L` for that `H` using the one-standard-error rule: choose the
shortest context statistically indistinguishable from the best."

**Nguồn primary:** Breiman, Friedman, Olshen & Stone (1984), *Classification and Regression Trees*,
§3.4.3 — định nghĩa quy tắc chọn cây đơn giản nhất có lỗi nằm trong một standard error của lỗi tốt
nhất. Được phát biểu lại trong Hastie, Tibshirani & Friedman, *The Elements of Statistical Learning*
(2nd ed.), tr. 61 và 244 (§7.10 cross-validation).

**Cảnh báo (một phần là suy luận của tôi):** quy tắc 1-SE gốc dùng standard error **của từng
candidate riêng lẻ**, tức là ngầm giả định các ước lượng độc lập. Trong thiết kế của dự án, L=63 và
L=126 được chấm trên **cùng một tập 133,937 origins**, nên sai số của chúng tương quan rất cao.
Dùng SE riêng của từng arm sẽ **overestimate** độ bất định của hiệu số và có xu hướng underfit
(chọn L quá ngắn). Cách đúng là dựng CI cho **hiệu số cặp** (paired difference), rồi áp ngưỡng
non-inferiority lên CI đó — đúng như `SPEC.md:576-587` (§8.5) đã yêu cầu ở chỗ khác.

Nguồn primary cho cách tiếp cận paired: Diebold & Mariano (1995) "Comparing Predictive Accuracy",
*JBES* 13(3) — kiểm định trực tiếp trên chuỗi hiệu số loss, chấp nhận sai số tự tương quan và
tương quan chéo. Kết hợp với stationary bootstrap của Politis & Romano (1994) mà SPEC đã liệt kê
(`SPEC.md:863`), và Hansen SPA (`SPEC.md:865-866`) cho hiệu chỉnh multiple comparison.

> **Mâu thuẫn nội bộ trong SPEC cần sửa:** `SPEC.md:398-399` (1-SE rule trên từng arm) không nhất
> quán với `SPEC.md:576-587` (paired date-block bootstrap). Nên diễn đạt lại §6.4 bước 4 thành:
> "chọn L ngắn nhất mà paired date-block CI của hiệu số so với L tốt nhất không loại trừ ngưỡng
> non-inferiority đã pre-register".

### 2.8 Kết luận RQ2

| Câu hỏi | Trả lời |
|---|---|
| L=126 có được literature ủng hộ không? | **Không.** Vượt ngoài toàn bộ dải daily 40–96 mà tác giả Kronos từng dùng. Không có nguồn nào. |
| L=63 có được literature ủng hộ không? | **Một phần có.** Nằm trong dải [40, 96] của tác giả. Vẫn không có nguồn nào nói 63 là tối ưu. |
| Có ràng buộc kỹ thuật nào chặn cả hai không? | Không. Cả hai < 512. |
| Grid {63, 126} có hợp lý không? | Hợp lý nhưng **thiếu một điểm quan trọng**: 40 (chính benchmark daily của paper). Grid {40, 63, 126} sẽ bao được cả kết luận của tác giả lẫn incumbent. |
| Chi phí thật của L=126 so với L=63? | ~2.05× FLOPs (không phải 4×), −7.4% window, mất 0 origin trong registry M2.1. Chi phí thấp hơn SPEC ngụ ý. |

---

## 3. RQ3 — H=5 (năm phiên daily) có defensible không?

### 3.1 Kronos chưa bao giờ công bố H=5 daily

Rà toàn bộ nguồn Kronos:

| Nguồn | Horizon daily |
|---|---:|
| Paper Table 8 (forecasting benchmark) | 12 |
| Paper Appendix D (investment simulation, tín hiệu `R_{t→t+H}`) | **H = 10** |
| Paper Appendix D (synthetic generation) | 35 |
| `finetune/config.py:21` (`predict_window`) | 10 |

Số **5** xuất hiện đúng một lần trong ngữ cảnh daily, và **không phải** với tư cách forecast
horizon mà là **minimum holding period** của chiến lược: "a maximum of n stocks are bought or sold
daily, and a **minimum holding period of 5 days** is enforced for all positions" (Appendix D,
Investment Simulation Setup).

> **Kết luận:** H=5 không có tiền lệ nào trong tài liệu Kronos. Tuy nhiên, H=5 **ngắn hơn** mọi
> horizon đã công bố (10–35), và theo lập luận thông thường thì horizon ngắn hơn dễ hơn chứ không
> khó hơn — nên H=5 không mâu thuẫn với bất cứ điều gì tác giả công bố. Nó chỉ đơn giản là chưa
> được ai đo.

**Một chi tiết đáng học từ tác giả:** tín hiệu của họ không phải là return tại điểm cuối horizon,
mà là **trung bình toàn đường đi**:
`R_{t→t+H} = ((1/H)·Σ_{i=1..H} p̂_{t+i} − p_t) / p_t`, với lý do "mitigating the influence of
short-term prediction noise and capturing the underlying trend more effectively" (Appendix D, eq. 13).
Repo hiện định nghĩa `r̂_{i,t,H}` là cumulative return tới `t+H` (`SPEC.md:491-493`). Đây là một
lựa chọn khác với tác giả và có thể là một biến thể tín hiệu rẻ để thử ở M2.3. *(Quan sát của tôi;
paper không so sánh hai định nghĩa này.)*

### 3.2 Phương sai của cumulative return: phần toán học là đúng

`SPEC.md:376-380` viết: `Var(R_{t,h}) = h·σ²` dưới innovation độc lập, nên độ rộng bất định tăng
xấp xỉ `√h`. **Điều này đúng và là số học thuần tuý**, không cần citation ngoài định nghĩa
`R_{t,h} = Σ_{j=1..h} r_{t+j}`.

Phần cần citation là **mức độ vi phạm giả định độc lập**. Nguồn primary:

- **Lo & MacKinlay (1988)**, "Stock Market Prices Do Not Follow Random Walks: Evidence from a Simple
  Specification Test", *RFS* 1(1), 41–66. Giới thiệu **variance ratio test**:
  `VR(q) = Var(R_{t,q}) / (q·Var(r_t))`. Dưới random walk, `VR(q) = 1`. Họ **bác bỏ mạnh** random
  walk cho weekly returns 1962–1985, chủ yếu do small stocks — nghĩa là `Var(R_{t,h}) ≠ h·σ²` trên
  thực tế, và độ lệch phụ thuộc size/liquidity.
- **Ý nghĩa cho dự án (suy luận của tôi):** VR(5) trên VN150 là một **thống kê rẻ, tính được từ dữ
  liệu đã có, không cần GPU**, và nó trả lời trực tiếp câu "giả định `√h` trong SPEC §6.3 sai bao
  nhiêu trên thị trường này, và có khác nhau theo liquidity tier không". Đây có lẽ là thí nghiệm
  rẻ nhất trong toàn bộ tài liệu này.

### 3.3 Suy giảm khả năng dự báo theo horizon: cẩn thận với hướng của bằng chứng

Đây là chỗ dễ trích dẫn sai nhất. Literature tài chính về "long-horizon predictability" **không**
nói rằng horizon dài khó dự báo hơn — nó nói ngược lại về mặt R² biểu kiến, và rồi giải thích rằng
sự tăng đó phần lớn là **ảo**.

- **Fama & French (1988)**, "Dividend yields and expected stock returns", *JFE* 22(1) — R² của hồi
  quy dự báo tăng theo horizon (từ vài % ở 1 năm lên 25%+ ở 4 năm).
- **Boudoukh, Richardson & Whitelaw (2008)**, "The Myth of Long-Horizon Predictability", *RFS*
  21(4), 1577–1605 — chứng minh rằng với regressor dai dẳng, các estimator ở các horizon khác nhau
  **gần như tương quan hoàn hảo dưới null hypothesis không có predictability**: "the analytical
  correlation is 99% between the 1- and 2-year horizon estimators and 94% between the 1- and 5-year
  horizons". Tức là bằng chứng "horizon dài dự báo tốt hơn" phần lớn là artifact của overlapping
  observations, không phải thông tin thật.

> **Đọc đúng cho dự án:** literature này nói về horizon **năm**, không phải **phiên**. Nó **không**
> hỗ trợ trực tiếp H=5 hay bất kỳ H daily nào. Nhưng nó dạy một bài học vận hành trực tiếp: khi so
> sánh H khác nhau trên **cùng** origins với target chồng lấn, các metric ở H khác nhau sẽ tương
> quan rất cao dưới null. Do đó **không được** so H=5 với H=10 bằng cách nhìn con số điểm; phải
> dùng paired inference và phải tính đến overlapping.
> Đây chính xác là lý do `SPEC.md:548-551` gọi paired t-test hiện tại là "diagnostic only".

- **Hansen & Hodrick (1980)** (đã có trong `SPEC.md:862`) là nguồn primary cho standard error dưới
  overlapping forecast — bắt buộc nếu dự án từng so nhiều H.
- **Politis & Romano (1994)** stationary bootstrap (`SPEC.md:863`) và **Hansen (2005)** SPA
  (`SPEC.md:866`) là công cụ đúng khi quét nhiều candidate. Repo đã cấu hình stationary bootstrap
  với `mean_block_dates: 10` tại `evaluation/configs/m2_3_paired_inference.yaml:8-9` — hợp lý cho
  H=5 (block trung bình 10 ngày ≈ 2× horizon).

**Không có primary source nào** cho "độ suy giảm accuracy theo horizon cho daily equity returns"
dưới dạng một đường cong có thể trích dẫn. Nếu ai đó đưa ra một con số kiểu "DA giảm x% mỗi phiên",
đó là bịa. Đây là câu hỏi thực nghiệm.

### 3.4 Lập luận thật sự ủng hộ H=5

`SPEC.md:402-403` nói: "T+2 constrains feasible trading logic. It does not mathematically prove that
five sessions is the most predictable horizon." **Câu này chính xác và nên giữ nguyên.**

Bổ sung ba lập luận có nền tảng:

1. **Chi phí suy luận tăng tuyến tính theo H** trong `auto_regressive_inference`
   (`model/kronos.py:420-454`: vòng lặp `for i in range(pred_len)`, mỗi bước một forward pass đầy
   đủ). H=5 rẻ hơn H=10 đúng 2×. *(Đọc từ code.)*
2. **Sai số tích luỹ (error accumulation) trong autoregressive rollout**: mỗi bước feed lại token
   đã sample (`model/kronos.py:448-454`), nên phân phối input drift khỏi dữ liệu thật. H nhỏ hạn
   chế drift. *(Suy luận của tôi từ code; paper không đo điều này.)*
3. **Tác giả dùng min holding period = 5 ngày** cho A-share daily — nghĩa là 5 phiên là một
   holding period được coi là hợp lý trong thiết kế của chính họ, ngay cả khi signal horizon là 10.

### 3.5 Kết luận RQ3

- H=5 **không được literature ủng hộ và cũng không bị literature bác bỏ**. Nó là lựa chọn sản phẩm.
- Phần toán `Var(R_{t,h}) = h·σ²` → `√h` trong `SPEC.md:376-380` là **đúng** như một
  baseline; mức lệch thực tế đo được bằng variance ratio (Lo & MacKinlay 1988) và **chưa được đo**
  trên VN150.
- Chỉ có **một** so sánh horizon rẻ và đáng làm: H=5 vs H=10 (giá trị của chính tác giả). Nhưng
  registry M2.1 hiện khoá `horizon: 5` — mở rộng sang H=10 sẽ phá vỡ tính so-sánh-được của
  registry đã đóng băng. **Khuyến nghị: KHÔNG mở rộng H ở M2.** Ghi nhận H=5 là ràng buộc sản
  phẩm, và để lại H như câu hỏi mở cho M3/M5.

---

## 4. Nơi bằng chứng mâu thuẫn với SPEC (chỉ đích danh dòng)

| SPEC | Nội dung hiện tại | Bằng chứng nói gì |
|---|---|---|
| `SPEC.md:269` | Kronos-small = "Primary development and deployment candidate" | Có nền tảng (official finetune config dùng small; small ≈ base trên forecasting; small thắng ở XKLS và volatility R²), nhưng bằng chứng daily-only duy nhất (Table 10 investment simulation) nghiêng về base. Nên gán nhãn rõ: đây là lựa chọn **cost-driven**, chưa phải evidence-driven. |
| `SPEC.md:275` | "Pretraining can make a larger model more sample-efficient." | Không có scaling law định lượng nào trong paper Kronos. Chỉ có một câu định tính ở §4.2 trên 3 điểm, không CI. Nên đánh dấu là giả thuyết. |
| `SPEC.md:354-355` | "`L=126`, `H=5` là incumbent baseline" | L=126 **nằm ngoài** mọi cấu hình daily đã công bố của tác giả (dải 40–96). Đây không phải baseline có nguồn gốc; nó là một lựa chọn tuỳ ý cần được ghi nhận như vậy. |
| `SPEC.md:366` | "`L=63` là cheaper candidate và `L=126` là incumbent" | Theo literature, quan hệ nên đảo: 63 là giá trị **có nền tảng**, 126 là candidate mạo hiểm. Ngoài ra 63 chỉ rẻ hơn ~2×, không phải 4×. |
| `SPEC.md:385` | "reduces valid windows linearly" | Đo thực tế trên VN150: chỉ −7.4% (247,999 → 229,734). Và trong registry M2.1 thì bằng 0% vì đã lọc common origins. Chi phí này gần như không tồn tại. |
| `SPEC.md:386` | "increases attention compute approximately as `O(L^2)`" | Đúng tiệm cận, sai về thực tế ở L ≤ 126: phần bậc hai chỉ chiếm 2.4–4.7% chi phí. Tỉ lệ thật 126/63 ≈ 2.05×. |
| `SPEC.md:383-388` | Danh sách chi phí của lookback dài | **Thiếu một mục quan trọng:** L cũng là normalization window (`data_pipeline/transforms.py:11-15`, `model/kronos.py:544`). Ablation L không phải ablation context thuần. |
| `SPEC.md:398-399` | "one-standard-error rule" | Không nhất quán với `SPEC.md:576-587` (paired date-block bootstrap). Vì hai arm dùng chung origins, phải dùng CI của **hiệu số cặp**, không phải SE riêng từng arm. |
| `SPEC.md:402-403` | "T+2 ... does not prove five sessions is the most predictable horizon" | **Đúng, giữ nguyên.** Đây là một trong những câu chính xác nhất của SPEC. |
| `SPEC.md:491-493` | `r̂_{i,t,H}` = cumulative return tới `t+H` | Tác giả Kronos dùng **path-average** `R_{t→t+H}` (Appendix D, eq. 13) với lý do giảm nhiễu. Khác biệt này chưa được ghi nhận và là một biến thể tín hiệu rẻ. |
| `SPEC.md:822` | Gate "Keep `L=126`" | Gate đúng về hình thức, nhưng đang mặc định L=126 ở vị trí ưu tiên. Bằng chứng không ủng hộ mặc định đó. |

**Sai lệch nhỏ giữa paper và checkpoint (ghi nhận để tránh nhầm sau này):** Paper Appendix C ghi
"The quantization group size is set to 5", trong khi `pretrained/Kronos-Tokenizer-base/config.json`
khai báo `"group_size": 4`. Cả hai đều hợp lệ với `codebook_dim = 20` (`model/module.py:58` assert
chia hết). Nghĩa là **Appendix C không mô tả chính xác checkpoint đã release**. Không ảnh hưởng
inference, nhưng nếu sau này có ai fine-tune tokenizer (`SPEC.md:282-292`) thì phải lấy config từ
checkpoint chứ không từ paper.

---

## 5. Khuyến nghị cụ thể

### 5.1 Cái gì defensible ngay (giữ nguyên, chỉ cần đổi cách diễn đạt)

| Lựa chọn | Trạng thái | Việc cần làm |
|---|---|---|
| **Kronos-base là frozen zero-shot reference** | Defensible | Không đổi. |
| **Tokenizer frozen** (`SPEC.md:280`) | Defensible | Không đổi. Đây cũng là mặc định của official finetune pipeline. |
| **H=5** | Defensible như **ràng buộc sản phẩm**, không phải như tối ưu | Đổi diễn đạt trong SPEC: "H=5 được chọn từ product utility (T+2) và chi phí rollout; không có bằng chứng công bố nào ủng hộ hay bác bỏ." |
| **`Var(R_{t,h}) = h·σ²` → `√h`** | Defensible (số học) | Thêm một câu: đây là baseline dưới i.i.d.; độ lệch thực tế đo bằng variance ratio. |
| **Paired date-block bootstrap** (`SPEC.md:576-587`) | Defensible và đúng chuẩn | Áp cùng chuẩn này cho §6.4 bước 4 (thay 1-SE rule đơn lẻ). |
| **max_context = 512** | Defensible | Khớp chính xác model card và paper. |

### 5.2 Cái gì cần thí nghiệm trước khi tin

| Lựa chọn | Vì sao chưa tin được |
|---|---|
| **Kronos-small non-inferior với Kronos-base** | Không có CI công bố; chênh 1.6% RankIC không phân biệt được với nhiễu; kết quả daily-only duy nhất nghiêng về base; VN là OOD. |
| **L=126 là incumbent hợp lý** | Không có nguồn nào. Nằm ngoài dải daily 40–96 của tác giả. |
| **L=63 là "candidate rẻ hơn"** | Chỉ rẻ hơn ~2×, không 4×. Và trong registry M2.1 nó không tiết kiệm origin nào. |
| **Grid {63, 126} là đủ** | Thiếu 40 — giá trị daily lookback mà chính benchmark forecasting của paper dùng. |
| **`√h` mô tả đúng phương sai trên VN150** | Chưa đo variance ratio trên dữ liệu này. |
| **Ablation L đo được "context length"** | Sai attribution: L đồng thời là normalization window. |

### 5.3 Thí nghiệm rẻ nhất cho từng câu hỏi

Xếp theo chi phí tăng dần. Tất cả đều dùng registry M2.1 đã đóng băng (133,937 origins, 977 dates,
147 symbols, hỗ trợ sẵn cả L=63 và L=126 ở H=5) và metric đã khoá — **không cần training**.

**E0 — Variance ratio trên VN150. Chi phí: ~0 GPU, vài phút CPU.**
Tính `VR(q) = Var(R_{t,q}) / (q·Var(r_t))` cho `q ∈ {2, 5, 10}` trên curated bars của
`vn150_strict_v2`, tách theo liquidity tier và theo fold 2022/2023/2024/2025.
*Trả lời:* giả định `√h` ở `SPEC.md:376-380` lệch bao nhiêu; H=5 có nằm trong vùng mean-reverting
hay momentum không. Đây là thí nghiệm có tỉ lệ giá trị/chi phí cao nhất trong danh sách.

**E1 — Tách bạch confound normalization. Chi phí: ~0 GPU.**
Trên một subsample origins, so sánh ba biến thể input đã chuẩn hoá: (a) L=63 chuẩn hoá trên 63 bar;
(b) L=126 chuẩn hoá trên 126 bar; (c) L=63 nhưng chuẩn hoá bằng mean/std của 126 bar. Chỉ cần đo
thống kê phân phối token/clip-rate, chưa cần model.
*Trả lời:* liệu chênh lệch L=63 vs L=126 có thể do normalization scale hay không, trước khi tiêu
GPU. Nếu (a) và (c) khác nhau đáng kể ở clip-rate hoặc token distribution thì mọi kết luận về "L"
phải được diễn đạt lại.

**E2 — Zero-shot 2×2 screening: {small, base} × {L=63, L=126} tại H=5.
Chi phí: 4 arm trên subsample origins.**
Đây là thí nghiệm chính. Đề xuất pre-register:
- Subsample có cấu trúc: lấy mỗi ngày thứ 5 trong 977 dates → ~195 dates, giữ **toàn bộ**
  cross-section mỗi ngày (≈27,000 origins/arm). Giữ nguyên cross-section là bắt buộc vì RankIC là
  metric theo ngày (`SPEC.md:516-520`).
- `sample_count`: dùng **10** thay vì 20 (`evaluation/configs/inference.yaml:20`) cho vòng screening
  — đây đúng là giá trị tác giả dùng cho price-series forecasting (Paper Table 6, N=10). Giảm chi
  phí 2×. Paper §"Ablation" ghi nhận IC/RankIC tăng đơn điệu theo số sample, nên đây là đánh đổi
  có ý thức, không phải sai sót.
- Sampling: cân nhắc `T=0.6, top_p=0.90` (giá trị tác giả tune, Table 6) thay vì `T=0.7`
  hiện tại (`evaluation/configs/inference.yaml:21`). Chi phí thêm: 0.
- Inference: paired stationary block bootstrap theo date (đã cấu hình sẵn ở
  `evaluation/configs/m2_3_paired_inference.yaml`), primary metric MW-DA và RankIC
  (`SPEC.md:558-560`).
*Trả lời cùng lúc:* (i) small có non-inferior với base trên VN không; (ii) L=126 có thuộc confidence
set không; (iii) hai hiệu ứng có tương tác không (rất có thể có: model nhỏ hơn có thể chịu context
dài kém hơn).

**E3 — Thêm arm L=40. Chi phí: +1 arm (hoặc +2 nếu chạy cả hai size).**
Chỉ chạy nếu E2 cho thấy L=63 ≥ L=126. L=40 là giá trị daily lookback của chính benchmark
forecasting trong paper (Table 8) và là điểm duy nhất trong grid có nguồn gốc primary source.
**Lưu ý thiết kế:** registry M2.1 lọc theo `max_lookback = 126`
(`evaluation/research/origins.py:181`), nên L=40 chạy trên đúng tập origin đó vẫn so sánh được —
chỉ là nó không tận dụng được universe rộng hơn mà L=40 lẽ ra cho phép. Điều đó là **đúng** cho
mục đích so sánh và cần nói rõ trong report.

**E4 — Biến thể tín hiệu path-average. Chi phí: ~0 GPU thêm.**
Từ chính các forecast path đã sinh ở E2, tính thêm tín hiệu theo công thức của tác giả
`R_{t→t+H} = ((1/H)·Σ p̂_{t+i} − p_t)/p_t` (Paper Appendix D, eq. 13) song song với cumulative
return hiện tại. Chấm cùng bộ metric.
*Trả lời:* định nghĩa tín hiệu hiện tại của repo có đang bỏ phí thông tin trong đường đi không.
Đây là thí nghiệm gần như miễn phí vì paths đã có.

### 5.4 Việc chuẩn bị bắt buộc trước E2

`pretrained/` **chưa có Kronos-small**. Phải tải `NeoQuasar/Kronos-small` (dùng chung
`Kronos-Tokenizer-base` đã có sẵn) và ghi hash checkpoint vào manifest theo invariant traceability
(`SPEC.md:100-102`).

### 5.5 Kết luận một dòng cho từng con số của người dùng

- **Kronos-small làm development/deployment candidate:** hợp lý, có nền tảng gián tiếp
  (official finetune config + khoảng cách nhỏ trong Tables 14/16/18), **nhưng non-inferiority chưa
  được chứng minh ở bất cứ đâu** và bằng chứng daily-only duy nhất nghiêng về base. Cần E2.
- **L=126:** **không có nguồn primary nào.** Nằm ngoài dải daily 40–96 của tác giả. Cần E2 để giữ.
- **L=63:** có nền tảng gián tiếp (nằm trong dải tác giả). Vẫn cần E2 để chọn.
- **Grid {63, 126}:** thiếu điểm 40. Cân nhắc E3.
- **H=5:** không có nguồn ủng hộ hay bác bỏ. Defensible như **ràng buộc sản phẩm** (T+2 + chi phí
  rollout tuyến tính theo H). Giữ nguyên, đổi cách diễn đạt, đừng mở rộng grid H ở M2.

---

## 6. References (URL đầy đủ)

**Kronos (primary):**
- Shi, Y., Fu, Z., Chen, S., Zhao, B., Xu, W., Zhang, C., Li, J. (2025). *Kronos: A Foundation Model for the Language of Financial Markets.* arXiv:2508.02739. Accepted AAAI 2026.
  - Abstract: https://arxiv.org/abs/2508.02739
  - Full text (HTML v1, dùng cho mọi trích dẫn Table/Section ở trên): https://arxiv.org/html/2508.02739v1
- Official repository: https://github.com/shiyu-coder/Kronos
- Official finetune config (lookback_window=90, predict_window=10, max_context=512, predictor=Kronos-small): https://github.com/shiyu-coder/Kronos/blob/master/finetune/config.py
- HuggingFace model cards:
  - https://huggingface.co/NeoQuasar/Kronos-small
  - https://huggingface.co/NeoQuasar/Kronos-base
  - https://huggingface.co/NeoQuasar/Kronos-Tokenizer-base
  - https://huggingface.co/NeoQuasar/Kronos-mini (không có benchmark công bố)
  - https://huggingface.co/NeoQuasar/Kronos-Tokenizer-2k
- Live demo: https://shiyu-coder.github.io/Kronos-demo/

**Lookback / context length trong time-series forecasting:**
- Zeng, A., Chen, M., Zhang, L., Xu, Q. (2023). *Are Transformers Effective for Time Series Forecasting?* AAAI 2023. https://arxiv.org/abs/2205.13504 (full text: https://ar5iv.labs.arxiv.org/html/2205.13504)
- Nie, Y., Nguyen, N.H., Sinthong, P., Kalagnanam, J. (2023). *A Time Series is Worth 64 Words: Long-term Forecasting with Transformers.* ICLR 2023. https://arxiv.org/abs/2211.14730 (full text: https://ar5iv.labs.arxiv.org/html/2211.14730)
- Yao, Q., Yang, C.-H.H., Jiang, R., Liang, Y., Jin, M., Pan, S. (2024). *Towards Neural Scaling Laws for Time Series Foundation Models.* https://arxiv.org/abs/2410.12360 (nguồn mà Kronos §4.2 viện dẫn cho tuyên bố scaling; đã có ở `SPEC.md:860`)
- Kaplan, J. et al. (2020). *Scaling Laws for Neural Language Models.* https://arxiv.org/abs/2001.08361 (nguồn Kronos viện dẫn khi chọn 3 model size)

**Model selection / one-standard-error rule:**
- Breiman, L., Friedman, J., Olshen, R., Stone, C. (1984). *Classification and Regression Trees.* Wadsworth. §3.4.3 (định nghĩa gốc của one-standard-error rule). https://doi.org/10.1201/9781315139470
- Hastie, T., Tibshirani, R., Friedman, J. (2009). *The Elements of Statistical Learning*, 2nd ed., tr. 61 và 244 (§7.10). PDF chính thức miễn phí: https://hastie.su.domains/ElemStatLearn/

**Inference cho so sánh dự báo (overlapping / dependent):**
- Diebold, F.X., Mariano, R.S. (1995). *Comparing Predictive Accuracy.* JBES 13(3), 253–263. https://doi.org/10.1080/07350015.1995.10524599
- Hansen, L.P., Hodrick, R.J. (1980). *Forward Exchange Rates as Optimal Predictors of Future Spot Rates.* JPE 88(5). https://doi.org/10.1086/260910 (đã có ở `SPEC.md:862`)
- Politis, D.N., Romano, J.P. (1994). *The Stationary Bootstrap.* JASA 89(428). https://doi.org/10.1080/01621459.1994.10476870 (đã có ở `SPEC.md:863`)
- Hansen, P.R. (2005). *A Test for Superior Predictive Ability.* JBES 23(4). https://doi.org/10.1198/073500105000000063 (đã có ở `SPEC.md:866`)
- White, H. (2000). *A Reality Check for Data Snooping.* Econometrica 68(5). https://doi.org/10.1111/1468-0262.00152 (đã có ở `SPEC.md:865`)

**Horizon / phương sai cumulative return:**
- Lo, A.W., MacKinlay, A.C. (1988). *Stock Market Prices Do Not Follow Random Walks: Evidence from a Simple Specification Test.* RFS 1(1), 41–66. https://doi.org/10.1093/rfs/1.1.41 (bản MIT: https://web.mit.edu/Alo/www/Papers/lo-mackinlay-88.html)
- Boudoukh, J., Richardson, M., Whitelaw, R.F. (2008). *The Myth of Long-Horizon Predictability.* RFS 21(4), 1577–1605. https://doi.org/10.1093/rfs/hhn035 (bản tác giả: https://pages.stern.nyu.edu/~rwhitela/papers/mlhp%20rfs08.pdf)
- Fama, E.F., French, K.R. (1988). *Dividend yields and expected stock returns.* JFE 22(1), 3–25. https://doi.org/10.1016/0304-405X(88)90020-7

**Nguồn nội bộ repo được trích dẫn:**
- `SPEC.md` v2.5 (các dòng đã chỉ đích danh ở §4)
- `GEMINI.md:65` (khoá grid `L in {63, 126}` tại `H=5`)
- `.codex/skills/vn-stock-market-radar/references/project-context.md:42, 52-53, 57-61`
- `model/kronos.py:389-469` (autoregressive rollout, truncation), `:484` (max_context default), `:544-547` (normalization)
- `model/module.py:58` (group_size assert), `:271-281` (SwiGLU FFN), `:284-353` (RoPE + attention), `:446-462` (DependencyAwareLayer), `:486-513` (DualHead)
- `pretrained/Kronos-base/config.json`, `pretrained/Kronos-Tokenizer-base/config.json`, `pretrained/Kronos-base/README.md:44-55`
- `data_pipeline/transforms.py:4-16` (normalize_lookback_window)
- `evaluation/configs/inference.yaml:3-5, 20-23`, `evaluation/configs/m2_1_origins.yaml:8`, `evaluation/configs/m2_3_paired_inference.yaml:7-12`
- `evaluation/research/origins.py:98-99, 181-194`
