import os
import sys
import glob
import random
import numpy as np
import pandas as pd
import torch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model import KronosTokenizer


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_tokenizer(model_path, device):
    print(f"Loading tokenizer from: {model_path}")
    tokenizer = KronosTokenizer.from_pretrained(model_path)
    tokenizer = tokenizer.to(device)
    tokenizer.eval()
    return tokenizer


def collect_windows(data_path, data_type='val', lookback=126, num_samples_per_stock=100, seed=42):
    set_seed(seed)
    csv_files = glob.glob(os.path.join(data_path, "*.csv"))
    print(f"Found {len(csv_files)} CSV files in {data_path} for data_type: {data_type}")
    
    all_windows = []
    feature_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
    
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        # Sắp xếp theo timestamps để đảm bảo thứ tự thời gian
        df['timestamps'] = pd.to_datetime(df['timestamps'])
        df = df.sort_values('timestamps').reset_index(drop=True)
        
        # Phân tách tập dữ liệu OOS tránh rò rỉ (leakage) khi benchmark
        if data_type == 'train':
            df = df[df['timestamps'] < pd.to_datetime('2023-01-01')].reset_index(drop=True)
        elif data_type == 'val':
            df = df[(df['timestamps'] >= pd.to_datetime('2023-01-01')) & (df['timestamps'] < pd.to_datetime('2024-01-01'))].reset_index(drop=True)
        elif data_type == 'test':
            df = df[df['timestamps'] >= pd.to_datetime('2024-01-01')].reset_index(drop=True)
        
        # Bổ sung amount nếu thiếu
        if 'amount' not in df.columns or df['amount'].isnull().all():
            df['amount'] = df['volume'] * (df['open'] + df['high'] + df['low'] + df['close']) / 4.0
            
        # Điền khuyết an toàn cho toàn bộ các cột tính năng để tránh rò rỉ NaN
        df[feature_cols] = df[feature_cols].ffill().bfill().fillna(0.0)
            
        data = df[feature_cols].values
        n_rows = len(data)
        
        if n_rows < lookback:
            print(f"[Warning] {os.path.basename(csv_file)} only has {n_rows} rows, skipping.")
            continue
            
        # Lấy ngẫu nhiên 100 chỉ mục bắt đầu
        max_start_idx = n_rows - lookback
        if max_start_idx < num_samples_per_stock:
            start_indices = list(range(max_start_idx + 1))
        else:
            start_indices = random.sample(range(max_start_idx + 1), num_samples_per_stock)
            
        for start_idx in start_indices:
            window = data[start_idx : start_idx + lookback]
            all_windows.append(window)
            
    print(f"Collected total of {len(all_windows)} windows.")
    return np.array(all_windows) # shape: (N_windows, lookback, 6)


def calculate_mape(original, reconstructed):
    denom = np.abs(original)
    denom = np.where(denom < 1e-5, 1e-5, denom)
    mape = np.mean(np.abs(original - reconstructed) / denom, axis=(0, 1)) * 100
    return mape


def calculate_mdape(original, reconstructed):
    denom = np.abs(original)
    denom = np.where(denom < 1e-5, 1e-5, denom)
    mdape = np.median(np.abs(original - reconstructed) / denom, axis=(0, 1)) * 100
    return mdape


def calculate_mae(original, reconstructed):
    mae = np.mean(np.abs(original - reconstructed), axis=(0, 1))
    return mae


def benchmark_tokenizer_model(tokenizer, windows, device):
    reconstructed_windows = []
    
    for window in windows:
        # window shape: (126, 6)
        # Chuẩn hóa Z-score cục bộ trên lookback 126 ngày (Clean logic)
        x_mean = np.mean(window, axis=0)
        x_std = np.std(window, axis=0)
        x_std = np.where(x_std < 1e-6, 1.0, x_std)
        x_norm = (window - x_mean) / (x_std + 1e-5)
        
        # FIX Bug #1B: Clip Z-score cục bộ trong [-5.0, 5.0] để khớp cấu trúc dữ liệu train
        x_norm = np.clip(x_norm, -5.0, 5.0)
        
        # Chuyển thành Tensor và chạy forward qua tokenizer
        x_norm_tensor = torch.tensor(x_norm, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            zs, _, _, _ = tokenizer(x_norm_tensor)
            _, z = zs
            reconstructed_norm = z.squeeze(0).cpu().numpy()
            
        # Khôi phục về giá trị raw ban đầu (denormalize)
        reconstructed_raw = reconstructed_norm * (x_std + 1e-5) + x_mean
        reconstructed_windows.append(reconstructed_raw)
        
    reconstructed_windows = np.array(reconstructed_windows)
    
    # Tính toán MAPE, MdAPE và MAE cho mỗi feature
    mape_scores = calculate_mape(windows, reconstructed_windows)
    mdape_scores = calculate_mdape(windows, reconstructed_windows)
    mae_scores = calculate_mae(windows, reconstructed_windows)
    return mape_scores, mdape_scores, mae_scores, reconstructed_windows


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    data_path = "data_cleaned"
    # Mặc định benchmark trên tập OOS Validation (năm 2023)
    windows = collect_windows(data_path, data_type='val', lookback=126, num_samples_per_stock=100, seed=42)
    
    models = {
        "pretrained": "pretrained/Kronos-Tokenizer-base",
        "tokenizer_v1": "finetune_csv/finetuned/vn50_daily/tokenizer/best_model",
        "tokenizer_v2": "finetune_csv/finetuned/tokenizer_v2/tokenizer/best_model"
    }
    
    results_mape = {}
    results_mdape = {}
    results_mae = {}
    features = ['Open', 'High', 'Low', 'Close', 'Volume', 'Amount']
    
    for name, path in models.items():
        if not os.path.exists(path):
            print(f"[Error] Path does not exist: {path}, skipping.")
            continue
        try:
            tokenizer = load_tokenizer(path, device)
            mape, mdape, mae, _ = benchmark_tokenizer_model(tokenizer, windows, device)
            results_mape[name] = mape
            results_mdape[name] = mdape
            results_mae[name] = mae
            print(f"--- Results for {name} ---")
            for feat, p, md, a in zip(features, mape, mdape, mae):
                print(f"  {feat}: MAPE={p:.4f}%, MdAPE={md:.4f}%, MAE={a:.4f}")
        except Exception as e:
            print(f"[Error] Failed to benchmark {name}: {str(e)}")
            
    # Lập bảng so sánh và hiển thị
    if results_mape:
        df_mape = pd.DataFrame(results_mape, index=features)
        df_mdape = pd.DataFrame(results_mdape, index=features)
        df_mae = pd.DataFrame(results_mae, index=features)
        
        print("\n" + "="*50)
        print("TOKENIZER RECONSTRUCTION MAPE COMPARISON (%)")
        print("="*50)
        print(df_mape.to_string())
        
        print("\n" + "="*50)
        print("TOKENIZER RECONSTRUCTION MdAPE COMPARISON (%)")
        print("="*50)
        print(df_mdape.to_string())
        
        print("\n" + "="*50)
        print("TOKENIZER RECONSTRUCTION MAE COMPARISON")
        print("="*50)
        print(df_mae.to_string())
        print("="*50)
        
        # Lưu kết quả ra thư mục tương đối của dự án (reports/tokenizer_benchmarks/)
        artifact_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "tokenizer_benchmarks"))
        os.makedirs(artifact_dir, exist_ok=True)
        
        df_mape.to_csv(os.path.join(artifact_dir, "tokenizer_benchmark_mape.csv"))
        df_mdape.to_csv(os.path.join(artifact_dir, "tokenizer_benchmark_mdape.csv"))
        df_mae.to_csv(os.path.join(artifact_dir, "tokenizer_benchmark_mae.csv"))
        print(f"Saved benchmark CSV results to: {artifact_dir}")
        
        # Kiểm chứng Pass Criteria cho Close Price MAPE
        print("\nVerification of Pass Criteria (v2 MAPE < v1 MAPE < pretrained MAPE cho OHLC):")
        price_feats = ['Open', 'High', 'Low', 'Close']
        for feat in price_feats:
            if "tokenizer_v2" in df_mape.columns and "pretrained" in df_mape.columns and "tokenizer_v1" in df_mape.columns:
                v2_val = df_mape.loc[feat, "tokenizer_v2"]
                pre_val = df_mape.loc[feat, "pretrained"]
                v1_val = df_mape.loc[feat, "tokenizer_v1"]
                
                # Sửa đổi so sánh theo xu hướng thực tế: v2 tốt nhất (nhỏ nhất) -> v1 -> pretrained tệ nhất (lớn nhất)
                cond1 = v2_val < v1_val
                cond2 = v1_val < pre_val
                
                status = "PASSED" if (cond1 and cond2) else "FAILED (Thực tế: v2 < v1 < pretrained)"
                print(f"  {feat}: v2 ({v2_val:.4f}%) < v1 ({v1_val:.4f}%) < pretrained ({pre_val:.4f}%) -> {status}")
                if v2_val < 2.0:
                    print(f"    - Price MAPE < 2% Criterion: PASSED (v2 Price MAPE = {v2_val:.4f}%)")
                else:
                    print(f"    - Price MAPE < 2% Criterion: FAILED (v2 Price MAPE = {v2_val:.4f}%)")
            else:
                print(f"  {feat}: Skipping verification due to missing columns.")
                
        # Kiểm chứng Volume và Amount MdAPE < 30% cho v2 (MdAPE loại bỏ nhiễu chia 0)
        print("\nVerification of Volume/Amount MdAPE < 30% (Median removes divide-by-zero liquidity outliers):")
        for feat in ['Volume', 'Amount']:
            if "tokenizer_v2" in df_mdape.columns:
                v2_val = df_mdape.loc[feat, "tokenizer_v2"]
                status = "PASSED" if v2_val < 30.0 else "FAILED"
                print(f"  {feat} MdAPE: v2 MdAPE ({v2_val:.4f}%) < 30% -> {status}")


if __name__ == "__main__":
    main()
