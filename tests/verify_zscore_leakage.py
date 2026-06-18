import os
import glob
import pandas as pd
import numpy as np

def verify_leakage(data_path):
    csv_files = glob.glob(os.path.join(data_path, "*.csv"))
    fpath = csv_files[0] # Take the first file, e.g., ACB.csv
    symbol = os.path.splitext(os.path.basename(fpath))[0]
    
    df = pd.read_csv(fpath)
    df['timestamps'] = pd.to_datetime(df['timestamps'])
    df = df.sort_values('timestamps').reset_index(drop=True)
    
    lookback = 126
    predict = 5
    window = lookback + predict + 1 # 132
    
    feature_list = ['open', 'high', 'low', 'close', 'volume', 'amount']
    if 'amount' not in df.columns:
        df['amount'] = df['volume'] * (df['open'] + df['high'] + df['low'] + df['close']) / 4.0
        
    # Take a window where a large price change happens in the predict window
    # Let's slide and find a window where future price changes significantly
    max_diff = 0
    best_idx = 0
    for i in range(len(df) - window + 1):
        window_df = df.iloc[i : i + window]
        lookback_prices = window_df['close'].iloc[:lookback].values
        future_prices = window_df['close'].iloc[lookback:].values
        
        diff = np.abs(np.mean(future_prices) - np.mean(lookback_prices))
        if diff > max_diff:
            max_diff = diff
            best_idx = i
            
    # Load that window
    window_df = df.iloc[best_idx : best_idx + window]
    x_double = window_df[feature_list].values.astype(np.float64)
    
    # Method 1: Leakage (Whole window)
    mean_leak = np.mean(x_double, axis=0)
    std_leak = np.std(x_double, axis=0)
    x_norm_leak = (x_double - mean_leak) / (std_leak + 1e-5)
    
    # Method 2: No Leakage (Lookback only)
    x_lookback = x_double[:lookback]
    mean_no_leak = np.mean(x_lookback, axis=0)
    std_no_leak = np.std(x_lookback, axis=0)
    x_norm_no_leak = (x_double - mean_no_leak) / (std_no_leak + 1e-5)
    
    # Compare historical parts (first 126 days)
    mae = np.mean(np.abs(x_norm_leak[:lookback] - x_norm_no_leak[:lookback]))
    max_err = np.max(np.abs(x_norm_leak[:lookback] - x_norm_no_leak[:lookback]))
    
    print("="*60)
    print(f"LEAKAGE DIAGNOSIS FOR {symbol} AT INDEX {best_idx}")
    print("="*60)
    print(f"Mean (with leak): {mean_leak[3]:.2f} | Std: {std_leak[3]:.2f}")
    print(f"Mean (no leak):   {mean_no_leak[3]:.2f} | Std: {std_no_leak[3]:.2f}")
    print(f"Mean Absolute Error in normalized history: {mae:.6f}")
    print(f"Maximum Error in normalized history:       {max_err:.6f}")
    print("-"*60)
    print("First 5 days comparison of normalized close price:")
    for t in range(5):
        print(f"t={t}: Norm with leak={x_norm_leak[t, 3]:.4f} | Norm no leak={x_norm_no_leak[t, 3]:.4f} | Diff={x_norm_leak[t, 3]-x_norm_no_leak[t, 3]:.4f}")
    print("="*60)

if __name__ == "__main__":
    verify_leakage("data_cleaned")
