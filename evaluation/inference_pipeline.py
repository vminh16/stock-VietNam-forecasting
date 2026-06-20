import os
import sys
import yaml
import argparse
import random
import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
from datetime import datetime

# Add parent directory, finetune_csv and current directory to system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../finetune_csv')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from model import Kronos, KronosTokenizer
from finetune_base_model import CustomKlineDataset
from model.kronos import KronosPredictor


def generate_raw(tokenizer, model, x, x_stamp, y_stamp, pred_len, max_context, clip, T, top_k, top_p, sample_count, device):
    """
    Dự báo autoregressive sinh ra toàn bộ các đường đi mẫu ngẫu nhiên (sample paths).
    """
    with torch.no_grad():
        x = torch.from_numpy(np.array(x).astype(np.float32)).to(device)
        x_stamp = torch.from_numpy(np.array(x_stamp).astype(np.float32)).to(device)
        y_stamp = torch.from_numpy(np.array(y_stamp).astype(np.float32)).to(device)

        x = torch.clip(x, -clip, clip)
        x = x.unsqueeze(1).repeat(1, sample_count, 1, 1).reshape(-1, x.size(1), x.size(2))
        x_stamp = x_stamp.unsqueeze(1).repeat(1, sample_count, 1, 1).reshape(-1, x_stamp.size(1), x_stamp.size(2))
        y_stamp = y_stamp.unsqueeze(1).repeat(1, sample_count, 1, 1).reshape(-1, y_stamp.size(1), y_stamp.size(2))

        x_token = tokenizer.encode(x, half=True)
        
        initial_seq_len = x.size(1)
        batch_size = x_token[0].size(0)
        total_seq_len = initial_seq_len + pred_len
        full_stamp = torch.cat([x_stamp, y_stamp], dim=1)

        generated_pre = x_token[0].new_empty(batch_size, pred_len)
        generated_post = x_token[1].new_empty(batch_size, pred_len)

        pre_buffer = x_token[0].new_zeros(batch_size, max_context)
        post_buffer = x_token[1].new_zeros(batch_size, max_context)
        buffer_len = min(initial_seq_len, max_context)
        if buffer_len > 0:
            start_idx = max(0, initial_seq_len - max_context)
            pre_buffer[:, :buffer_len] = x_token[0][:, start_idx:start_idx + buffer_len]
            post_buffer[:, :buffer_len] = x_token[1][:, start_idx:start_idx + buffer_len]

        import model.kronos as kronos_mod
        for i in range(pred_len):
            current_seq_len = initial_seq_len + i
            window_len = min(current_seq_len, max_context)

            if current_seq_len <= max_context:
                input_tokens = [
                    pre_buffer[:, :window_len],
                    post_buffer[:, :window_len]
                ]
            else:
                input_tokens = [pre_buffer, post_buffer]

            context_end = current_seq_len
            context_start = max(0, context_end - max_context)
            current_stamp = full_stamp[:, context_start:context_end, :].contiguous()

            s1_logits, context = model.decode_s1(input_tokens[0], input_tokens[1], current_stamp)
            s1_logits = s1_logits[:, -1, :]
            sample_pre = kronos_mod.sample_from_logits(s1_logits, temperature=T, top_k=top_k, top_p=top_p, sample_logits=True)

            s2_logits = model.decode_s2(context, sample_pre)
            s2_logits = s2_logits[:, -1, :]
            sample_post = kronos_mod.sample_from_logits(s2_logits, temperature=T, top_k=top_k, top_p=top_p, sample_logits=True)

            generated_pre[:, i] = sample_pre.squeeze(-1)
            generated_post[:, i] = sample_post.squeeze(-1)

            if current_seq_len < max_context:
                pre_buffer[:, current_seq_len] = sample_pre.squeeze(-1)
                post_buffer[:, current_seq_len] = sample_post.squeeze(-1)
            else:
                pre_buffer.copy_(torch.roll(pre_buffer, shifts=-1, dims=1))
                post_buffer.copy_(torch.roll(post_buffer, shifts=-1, dims=1))
                pre_buffer[:, -1] = sample_pre.squeeze(-1)
                post_buffer[:, -1] = sample_post.squeeze(-1)

        full_pre = torch.cat([x_token[0], generated_pre], dim=1)
        full_post = torch.cat([x_token[1], generated_post], dim=1)

        context_start = max(0, total_seq_len - max_context)
        input_tokens = [
            full_pre[:, context_start:total_seq_len].contiguous(),
            full_post[:, context_start:total_seq_len].contiguous()
        ]
        z = tokenizer.decode(input_tokens, half=True)
        z = z.reshape(-1, sample_count, z.size(1), z.size(2))
        preds = z.cpu().numpy()
        preds = preds[:, :, -pred_len:, :]
        return preds


def predict_batch_mean(predictor, df_list, x_timestamp_list, y_timestamp_list, pred_len, sample_count, T, top_k, top_p, device):
    """
    Dự báo batch và lấy trung bình các đường đi mẫu.
    """
    num_series = len(df_list)
    x_list = []
    x_stamp_list = []
    y_stamp_list = []
    means = []
    stds = []

    import model.kronos as kronos_mod
    for i in range(num_series):
        df = df_list[i].copy()
        if predictor.vol_col not in df.columns:
            df[predictor.vol_col] = 0.0
            df[predictor.amt_vol] = 0.0
        if predictor.amt_vol not in df.columns and predictor.vol_col in df.columns:
            df[predictor.amt_vol] = df[predictor.vol_col] * df[predictor.price_cols].mean(axis=1)

        x_timestamp = x_timestamp_list[i]
        y_timestamp = y_timestamp_list[i]

        x_time_df = kronos_mod.calc_time_stamps(x_timestamp)
        y_time_df = kronos_mod.calc_time_stamps(y_timestamp)

        x = df[predictor.price_cols + [predictor.vol_col, predictor.amt_vol]].values.astype(np.float32)
        x_stamp = x_time_df.values.astype(np.float32)
        y_stamp = y_time_df.values.astype(np.float32)

        x_mean, x_std = np.mean(x, axis=0), np.std(x, axis=0)
        # Khắc phục Edge Case: Tránh chia cho std quá nhỏ (flat periods, suspended stocks)
        x_std = np.where(x_std < 1e-6, 1.0, x_std)
        x_norm = (x - x_mean) / (x_std + 1e-5)
        x_norm = np.clip(x_norm, -predictor.clip, predictor.clip)

        x_list.append(x_norm)
        x_stamp_list.append(x_stamp)
        y_stamp_list.append(y_stamp)
        means.append(x_mean)
        stds.append(x_std)

    x_batch = np.stack(x_list, axis=0).astype(np.float32)
    x_stamp_batch = np.stack(x_stamp_list, axis=0).astype(np.float32)
    y_stamp_batch = np.stack(y_stamp_list, axis=0).astype(np.float32)

    preds = generate_raw(
        predictor.tokenizer, predictor.model, x_batch, x_stamp_batch, y_stamp_batch,
        pred_len, predictor.max_context, predictor.clip, T, top_k, top_p, sample_count, device
    )

    preds_mean = np.mean(preds, axis=1)

    results = []
    for i in range(num_series):
        preds_i = preds_mean[i] * (stds[i] + 1e-5) + means[i]
        results.append(preds_i)
    return results


def get_evaluation_indices(dataset, limit=-1, seed=42):
    """
    Lấy danh sách các chỉ mục để đánh giá.
    Nếu limit > 0: Thực hiện Date-Aligned & Non-overlapping Sampling (các ngày cách nhau ít nhất 5 ngày giao dịch).
    Nếu limit <= 0: Lấy toàn bộ các chỉ mục.
    """
    # Gom nhóm chỉ mục theo ngày t_date (lookback end date)
    date_to_indices = {}
    for idx in range(len(dataset)):
        symbol, start_idx = dataset.global_index_map[idx]
        df = dataset.stock_data[symbol]
        date = df.loc[start_idx + dataset.lookback_window - 1, 'timestamps']
        date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
        if date_str not in date_to_indices:
            date_to_indices[date_str] = []
        date_to_indices[date_str].append(idx)
        
    sampled_indices = []
    if limit > 0:
        # Gom nhóm toàn bộ ngày giao dịch tăng dần
        all_dates = sorted(list(date_to_indices.keys()))
        n_dates_needed = max(1, limit // 50)  # Giả định trung bình 50 stocks/date
        
        # Đảm bảo khoảng cách tối thiểu giữa các ngày là 5 ngày giao dịch (non-overlapping)
        step = max(5, len(all_dates) // n_dates_needed)
        rng = random.Random(seed)
        start_idx = rng.randint(0, max(1, step - 1))
        sampled_dates = all_dates[start_idx::step][:n_dates_needed]
        
        # Thu thập toàn bộ các chỉ mục của các ngày đã chọn
        for date_str in sampled_dates:
            sampled_indices.extend(date_to_indices[date_str])
    else:
        for indices in date_to_indices.values():
            sampled_indices.extend(indices)
            
    # Sắp xếp thời gian tăng dần của lookback end date
    def get_lookback_end_time(idx):
        symbol, start_idx = dataset.global_index_map[idx]
        df = dataset.stock_data[symbol]
        return df.loc[start_idx + dataset.lookback_window - 1, 'timestamps']
        
    sampled_indices.sort(key=get_lookback_end_time)
    return sampled_indices


def evaluate_dataset(dataset, predictor, config, device, limit=500):
    """
    Chạy dự báo trên tập dữ liệu và tính toán toàn bộ metrics + backtest.
    """
    sampled_indices = get_evaluation_indices(dataset, limit=limit, seed=42)
    print(f"[*] Evaluated windows count: {len(sampled_indices)}")
    
    results_records = []
    eval_batch_size = config['inference']['eval_batch_size']
    
    for idx_start in range(0, len(sampled_indices), eval_batch_size):
        batch_indices = sampled_indices[idx_start : idx_start + eval_batch_size]
        
        batch_dfs = []
        batch_x_ts = []
        batch_y_ts = []
        batch_metadata = []
        
        for idx in batch_indices:
            symbol, start_idx = dataset.global_index_map[idx]
            df = dataset.stock_data[symbol]
            
            lookback_df = df.iloc[start_idx : start_idx + dataset.lookback_window].copy()
            future_df = df.iloc[start_idx + dataset.lookback_window : start_idx + dataset.lookback_window + dataset.predict_window].copy()
            
            t_date = lookback_df.iloc[-1]['timestamps']
            t5_date = future_df.iloc[-1]['timestamps']
            actual_close_t = lookback_df.iloc[-1]['close']
            actual_close_t5 = future_df.iloc[-1]['close']
            
            batch_dfs.append(lookback_df)
            batch_x_ts.append(lookback_df['timestamps'])
            batch_y_ts.append(future_df['timestamps'])
            batch_metadata.append({
                'symbol': symbol,
                't_date': t_date,
                't5_date': t5_date,
                'actual_close_t': actual_close_t,
                'actual_close_t5': actual_close_t5
            })
            
        batch_preds = predict_batch_mean(
            predictor, batch_dfs, batch_x_ts, batch_y_ts,
            pred_len=dataset.predict_window,
            sample_count=config['inference']['sample_count'],
            T=config['inference']['temperature'],
            top_k=config['inference']['top_k'],
            top_p=config['inference']['top_p'],
            device=device
        )
        
        for i, pred_val in enumerate(batch_preds):
            meta = batch_metadata[i]
            pred_close_t5 = pred_val[-1, 3] # close column index is 3
            
            actual_ret = (meta['actual_close_t5'] - meta['actual_close_t']) / meta['actual_close_t']
            pred_ret = (pred_close_t5 - meta['actual_close_t']) / meta['actual_close_t']
            # FIX Bug #9: Giới hạn pred_ret tránh nhiễu ngoại lai quá lớn (outlier clipping)
            pred_ret = np.clip(pred_ret, -0.5, 0.5)
            
            results_records.append({
                'symbol': meta['symbol'],
                't_date': meta['t_date'],
                't5_date': meta['t5_date'],
                'actual_close_t': meta['actual_close_t'],
                'actual_close_t5': meta['actual_close_t5'],
                'pred_close_t5': pred_close_t5,
                'actual_return_5d': actual_ret,
                'pred_return_5d': pred_ret
            })
            
    df_eval = pd.DataFrame(results_records)
    
    # --- 1. Directional Accuracy (DA) ---
    actual_sign = np.where(df_eval['actual_return_5d'] > 0, 1, -1)
    pred_sign = np.where(df_eval['pred_return_5d'] > 0, 1, -1)
    correct_dir = (actual_sign == pred_sign)
    da = np.mean(correct_dir) * 100
    
    # --- 2. Magnitude-Weighted DA (MW-DA) ---
    abs_actual_ret = np.abs(df_eval['actual_return_5d'])
    mw_da = np.sum(abs_actual_ret * correct_dir) / np.sum(abs_actual_ret) * 100
    
    # --- 3. RankIC và Hit Rate @ Top-20% ---
    rank_ics = []
    hit_rates = []
    
    # Nhóm theo ngày dự báo
    grouped = df_eval.groupby('t_date')
    dates_sorted = sorted(df_eval['t_date'].unique())
    
    # Vị thế Long/Short ở từng ngày để tính toán Backtest
    strategy_returns_long = []
    strategy_returns_ls = []
    benchmark_returns = []
    
    # Chiến lược Magnitude-Weighted
    strategy_returns_long_mag = []
    strategy_returns_ls_mag = []
    
    prev_long_portfolio = set()
    prev_short_portfolio = set()
    prev_long_portfolio_mag = set()
    prev_short_portfolio_mag = set()
    
    # Lọc các ngày rebalance không chồng lấp (Non-overlapping)
    # Mode final: Mỗi 5 ngày mới rebalance (dates_sorted[::5]) để tránh lạm phát do tự tương quan
    # Mode dev: Các ngày đã được Date-Aligned & Non-overlapping Sampling cách xa nhau sẵn, giữ nguyên
    if limit <= 0:
        rebalance_dates = dates_sorted[::5]
    else:
        rebalance_dates = dates_sorted
        
    # Danh sách thu thập chỉ số từng ngày để chạy paired t-test và logging
    per_date_da_list = []
    per_date_ic_list = []
    per_date_long_symbols = []
    actual_rebalance_dates = []
    
    MIN_STOCKS_PER_DATE = 45  # Đảm bảo đủ số mã so sánh chuẩn
    
    for t in rebalance_dates:
        group = grouped.get_group(t)
        
        # B3b: Lọc các ngày thiếu mã cổ phiếu để tránh lệch so sánh
        if len(group) < MIN_STOCKS_PER_DATE:
            continue
            
        actual_rebalance_dates.append(t)
            
        # 1. Tính DA cho riêng ngày (sử dụng cho paired t-test)
        actual_sign_t = np.where(group['actual_return_5d'] > 0, 1, -1)
        pred_sign_t = np.where(group['pred_return_5d'] > 0, 1, -1)
        correct_dir_t = (actual_sign_t == pred_sign_t)
        da_t = np.mean(correct_dir_t) * 100
        per_date_da_list.append(da_t)
        
        # 2. RankIC (Spearman correlation) cho riêng ngày
        ic = group['pred_return_5d'].corr(group['actual_return_5d'], method='spearman')
        if np.isnan(ic):
            ic = 0.0
        per_date_ic_list.append(ic)
        
        # Thống kê IC chung
        if len(group) >= 3:
            rank_ics.append(ic)
            
        # Top 10 stocks (Long), Bottom 10 stocks (Short)
        long_stocks = group.nlargest(10, 'pred_return_5d')
        short_stocks = group.nsmallest(10, 'pred_return_5d')
        
        per_date_long_symbols.append(long_stocks['symbol'].tolist())
        
        # B6: Logging Diagnostic cho mỗi ngày
        t_str = t.strftime('%Y-%m-%d') if hasattr(t, 'strftime') else str(t)
        print(f"Date {t_str}: Long={long_stocks['symbol'].tolist()[:5]}..., "
              f"Top-1 Pred={long_stocks['pred_return_5d'].iloc[0]:.4f}, "
              f"Actual={long_stocks['actual_return_5d'].iloc[0]:.4f}")
        
        # Hit Rate @ Top-20%
        if len(long_stocks) > 0:
            hit_rate = np.mean(long_stocks['actual_return_5d'] > 0) * 100
            hit_rates.append(hit_rate)
            
        # --- Backtest Portfolio Math ---
        # 3a. Equal-Weighted Portfolio
        actual_ret_long_5d = np.mean(long_stocks['actual_return_5d'])
        actual_ret_short_5d = np.mean(short_stocks['actual_return_5d'])
        actual_ret_bench_5d = np.mean(group['actual_return_5d'])
        
        log_ret_long = np.log(1.0 + actual_ret_long_5d)
        log_ret_short = np.log(1.0 + actual_ret_short_5d)
        log_ret_bench = np.log(1.0 + actual_ret_bench_5d)
        
        # Phí giao dịch Equal-Weight
        curr_long_portfolio = set(long_stocks['symbol'])
        curr_short_portfolio = set(short_stocks['symbol'])
        
        if len(prev_long_portfolio) == 0:
            turnover_long = 1.0
            turnover_short = 1.0
        else:
            turnover_long = 1.0 - (len(curr_long_portfolio.intersection(prev_long_portfolio)) / 10.0)
            turnover_short = 1.0 - (len(curr_short_portfolio.intersection(prev_short_portfolio)) / 10.0)
            
        fee_long = turnover_long * 0.15 / 100
        fee_short = turnover_short * 0.15 / 100
        
        log_ret_long_net = log_ret_long - fee_long
        log_ret_ls_net = log_ret_long - log_ret_short - (fee_long + fee_short)
        
        strategy_returns_long.append(log_ret_long_net)
        strategy_returns_ls.append(log_ret_ls_net)
        benchmark_returns.append(log_ret_bench)
        
        prev_long_portfolio = curr_long_portfolio
        prev_short_portfolio = curr_short_portfolio
        
        # 3b. Magnitude-Weighted Portfolio
        # Long: Chỉ dùng mã có pred_return_5d > 0. Nếu không có, fallback về equal-weight
        long_positive = long_stocks[long_stocks['pred_return_5d'] > 0]
        if len(long_positive) == 0:
            ret_long_mag = actual_ret_long_5d
            curr_long_portfolio_mag = set(long_stocks['symbol'])
            turnover_long_mag = 1.0 if len(prev_long_portfolio_mag) == 0 else 1.0 - (len(curr_long_portfolio_mag.intersection(prev_long_portfolio_mag)) / 10.0)
        else:
            weights_long = long_positive['pred_return_5d'] / long_positive['pred_return_5d'].sum()
            ret_long_mag = np.sum(weights_long * long_positive['actual_return_5d'])
            curr_long_portfolio_mag = set(long_positive['symbol'])
            turnover_long_mag = 1.0 if len(prev_long_portfolio_mag) == 0 else 1.0 - (len(curr_long_portfolio_mag.intersection(prev_long_portfolio_mag)) / len(curr_long_portfolio_mag))
            
        # Short: Chỉ dùng mã có pred_return_5d < 0. Nếu không có, fallback về equal-weight
        short_negative = short_stocks[short_stocks['pred_return_5d'] < 0]
        if len(short_negative) == 0:
            ret_short_mag = actual_ret_short_5d
            curr_short_portfolio_mag = set(short_stocks['symbol'])
            turnover_short_mag = 1.0 if len(prev_short_portfolio_mag) == 0 else 1.0 - (len(curr_short_portfolio_mag.intersection(prev_short_portfolio_mag)) / 10.0)
        else:
            mags = -short_negative['pred_return_5d']
            weights_short = mags / mags.sum()
            ret_short_mag = np.sum(weights_short * short_negative['actual_return_5d'])
            curr_short_portfolio_mag = set(short_negative['symbol'])
            turnover_short_mag = 1.0 if len(prev_short_portfolio_mag) == 0 else 1.0 - (len(curr_short_portfolio_mag.intersection(prev_short_portfolio_mag)) / len(curr_short_portfolio_mag))
            
        log_ret_long_mag = np.log(1.0 + ret_long_mag)
        log_ret_short_mag = np.log(1.0 + ret_short_mag)
        
        fee_long_mag = turnover_long_mag * 0.15 / 100
        fee_short_mag = turnover_short_mag * 0.15 / 100
        
        log_ret_long_mag_net = log_ret_long_mag - fee_long_mag
        log_ret_ls_mag_net = log_ret_long_mag - log_ret_short_mag - (fee_long_mag + fee_short_mag)
        
        strategy_returns_long_mag.append(log_ret_long_mag_net)
        strategy_returns_ls_mag.append(log_ret_ls_mag_net)
        
        prev_long_portfolio_mag = curr_long_portfolio_mag
        prev_short_portfolio_mag = curr_short_portfolio_mag
        
    avg_rank_ic = np.mean(rank_ics) if len(rank_ics) > 0 else 0.0
    avg_hit_rate = np.mean(hit_rates) if len(hit_rates) > 0 else 0.0
    
    # Thống kê Backtest lũy kế
    cum_returns_long = np.cumsum(strategy_returns_long)
    cum_returns_ls = np.cumsum(strategy_returns_ls)
    cum_returns_bench = np.cumsum(benchmark_returns)
    
    cum_returns_long_mag = np.cumsum(strategy_returns_long_mag)
    cum_returns_ls_mag = np.cumsum(strategy_returns_ls_mag)
    
    # Tính Annualized Sharpe (5-day periods -> annualizing factor = 252 / 5 = 50.4)
    ann_factor = 50.4
    r_f_period = 0.04 / ann_factor # daily 4% risk free rate
    
    def calc_sharpe(returns):
        mean_ret = np.mean(returns)
        std_ret = np.std(returns)
        if std_ret < 1e-6:
            return 0.0
        return (mean_ret - r_f_period) / std_ret * np.sqrt(ann_factor)
        
    def calc_max_drawdown(cum_returns):
        if len(cum_returns) == 0:
            return 0.0
        equity = np.exp(cum_returns)
        cum_max = np.maximum.accumulate(equity)
        drawdown = (cum_max - equity) / cum_max
        return np.max(drawdown) * 100
        
    sharpe_long = calc_sharpe(strategy_returns_long)
    sharpe_ls = calc_sharpe(strategy_returns_ls)
    sharpe_bench = calc_sharpe(benchmark_returns)
    
    sharpe_long_mag = calc_sharpe(strategy_returns_long_mag)
    sharpe_ls_mag = calc_sharpe(strategy_returns_ls_mag)
    
    mdd_long = calc_max_drawdown(cum_returns_long)
    mdd_ls = calc_max_drawdown(cum_returns_ls)
    mdd_bench = calc_max_drawdown(cum_returns_bench)
    
    mdd_long_mag = calc_max_drawdown(cum_returns_long_mag)
    mdd_ls_mag = calc_max_drawdown(cum_returns_ls_mag)
    
    ann_return_long = np.mean(strategy_returns_long) * ann_factor * 100 if len(strategy_returns_long) > 0 else 0.0
    ann_return_ls = np.mean(strategy_returns_ls) * ann_factor * 100 if len(strategy_returns_ls) > 0 else 0.0
    ann_return_bench = np.mean(benchmark_returns) * ann_factor * 100 if len(benchmark_returns) > 0 else 0.0
    
    ann_return_long_mag = np.mean(strategy_returns_long_mag) * ann_factor * 100 if len(strategy_returns_long_mag) > 0 else 0.0
    ann_return_ls_mag = np.mean(strategy_returns_ls_mag) * ann_factor * 100 if len(strategy_returns_ls_mag) > 0 else 0.0
    
    calmar_long = ann_return_long / mdd_long if mdd_long > 1e-4 else 0.0
    calmar_ls = ann_return_ls / mdd_ls if mdd_ls > 1e-4 else 0.0
    
    win_rate_long = np.mean(np.array(strategy_returns_long) > 0) * 100 if len(strategy_returns_long) > 0 else 0.0
    win_rate_ls = np.mean(np.array(strategy_returns_ls) > 0) * 100 if len(strategy_returns_ls) > 0 else 0.0
    
    metrics = {
        'da': da,
        'mw_da': mw_da,
        'rank_ic': avg_rank_ic,
        'hit_rate': avg_hit_rate,
        'ann_return_long': ann_return_long,
        'ann_return_ls': ann_return_ls,
        'ann_return_bench': ann_return_bench,
        'sharpe_long': sharpe_long,
        'sharpe_ls': sharpe_ls,
        'sharpe_bench': sharpe_bench,
        'mdd_long': mdd_long,
        'mdd_ls': mdd_ls,
        'mdd_bench': mdd_bench,
        'calmar_long': calmar_long,
        'calmar_ls': calmar_ls,
        'win_rate_long': win_rate_long,
        'win_rate_ls': win_rate_ls,
        
        # Magnitude Weighted Metrics
        'ann_return_long_mag': ann_return_long_mag,
        'ann_return_ls_mag': ann_return_ls_mag,
        'sharpe_long_mag': sharpe_long_mag,
        'sharpe_ls_mag': sharpe_ls_mag,
        'mdd_long_mag': mdd_long_mag,
        'mdd_ls_mag': mdd_ls_mag
    }
    
    history = {
        'dates': [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in actual_rebalance_dates],
        'cum_returns_long': cum_returns_long.tolist(),
        'cum_returns_ls': cum_returns_ls.tolist(),
        'cum_returns_bench': cum_returns_bench.tolist(),
        'cum_returns_long_mag': cum_returns_long_mag.tolist(),
        'cum_returns_ls_mag': cum_returns_ls_mag.tolist(),
        'per_date_da': per_date_da_list,
        'per_date_ic': per_date_ic_list,
        'per_date_long_symbols': per_date_long_symbols
    }
    
    return metrics, history


def main():
    parser = argparse.ArgumentParser(description='Kronos Baseline Inference and Quant Evaluation')
    parser.add_argument('--config', type=str, default='finetune_csv/configs/inference.yaml',
                        help='Path to the inference yaml config file')
    parser.add_argument('--mode', type=str, default='dev', choices=['dev', 'final'],
                        help='Evaluation mode: dev (500 samples) or final (all samples)')
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Using device: {device} | Evaluation Mode: {args.mode.upper()}")
    
    # Fix random seed for reproducibility
    seed = config['data'].get('seed', 42)
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    
    # Load models
    tokenizer = KronosTokenizer.from_pretrained(config['inference']['tokenizer_path']).to(device)
    print(f"[*] Loaded tokenizer from {config['inference']['tokenizer_path']}")
    
    model = Kronos.from_pretrained(config['inference']['predictor_path'])
    if config['inference'].get('use_lora', False):
        from peft import PeftModel
        adapter_path = config['inference']['adapter_path']
        print(f"[*] Wrapping base model with LoRA adapter from {adapter_path}")
        model = PeftModel.from_pretrained(model, adapter_path)
    model = model.to(device)
    print(f"[*] Loaded predictor from {config['inference']['predictor_path']}")
    
    model.eval()
    tokenizer.eval()
    
    predictor = KronosPredictor(
        model, tokenizer, device=device,
        max_context=config['data']['max_context'],
        clip=config['data']['clip']
    )
    
    # Load validation and test datasets
    train_end_date = config['data']['train_end_date']
    val_end_date = config['data']['val_end_date']
    
    print("[*] Preparing datasets...")
    val_dataset = CustomKlineDataset(
        data_path=config['data']['data_path'],
        data_type='val',
        lookback_window=config['data']['lookback_window'],
        predict_window=config['data']['predict_window'],
        clip=config['data']['clip'],
        seed=seed,
        train_end_date=train_end_date,
        val_end_date=val_end_date
    )
    
    test_dataset = CustomKlineDataset(
        data_path=config['data']['data_path'],
        data_type='test',
        lookback_window=config['data']['lookback_window'],
        predict_window=config['data']['predict_window'],
        clip=config['data']['clip'],
        seed=seed,
        train_end_date=train_end_date,
        val_end_date=val_end_date
    )
    
    # Set limit based on mode
    limit = config['inference'].get('eval_samples_limit', 2500) if args.mode == 'dev' else -1
    
    print("\n" + "="*50)
    print("RUNNING EVALUATION ON VALIDATION SET (OOS 2023)")
    print("="*50)
    val_metrics, val_hist = evaluate_dataset(val_dataset, predictor, config, device, limit=limit)
    
    print("\n" + "="*50)
    print("RUNNING EVALUATION ON TEST SET (OOS 2024+)")
    print("="*50)
    test_metrics, test_hist = evaluate_dataset(test_dataset, predictor, config, device, limit=limit)
    
    # Print metrics report
    print("\n" + "="*60)
    print("EVALUATION METRICS SUMMARY REPORT")
    print("="*60)
    print(f"{'Metric':<30} | {'Validation':<12} | {'Test':<12}")
    print("-"*60)
    for k in val_metrics.keys():
        print(f"{k:<30} | {val_metrics[k]:<12.4f} | {test_metrics[k]:<12.4f}")
    print("="*60)
    
    # Save output reports
    output_dir = config['inference']['output_dir']
    os.makedirs(output_dir, exist_ok=True)
    
    # B6: Lưu per_date_metrics.csv của đợt chạy hiện tại
    per_date_df = pd.DataFrame({
        'date': test_hist['dates'],
        'da': test_hist['per_date_da'],
        'rank_ic': test_hist['per_date_ic'],
        'long_symbols': [",".join(syms) for syms in test_hist['per_date_long_symbols']]
    })
    per_date_path = os.path.join(output_dir, 'per_date_metrics.csv')
    per_date_df.to_csv(per_date_path, index=False)
    print(f"[*] Exported per-date diagnostics to: {per_date_path}")
    
    # B5 & B6: Thực hiện Paired T-test và tính overlap ratio nếu tìm thấy Baseline
    if "finetuned" in output_dir:
        baseline_path = os.path.join("reports/baseline_model_evaluation", "per_date_metrics.csv")
        if os.path.exists(baseline_path):
            baseline_df = pd.read_csv(baseline_path)
            merged = pd.merge(baseline_df, per_date_df, on='date', suffixes=('_base', '_ft'))
            if len(merged) >= 2:
                from scipy.stats import ttest_rel
                t_da, p_da = ttest_rel(merged['da_ft'], merged['da_base'])
                t_ic, p_ic = ttest_rel(merged['rank_ic_ft'], merged['rank_ic_base'], nan_policy='omit')
                
                # Tính trung bình trùng lặp top-10 long
                overlaps = []
                for _, row in merged.iterrows():
                    base_syms = set(row['long_symbols_base'].split(","))
                    ft_syms = set(row['long_symbols_ft'].split(","))
                    overlap = len(base_syms.intersection(ft_syms)) / len(base_syms)
                    overlaps.append(overlap)
                avg_overlap = np.mean(overlaps)
                
                print("\n" + "="*60)
                print("COMPARATIVE STATISTICAL SIGNIFICANCE (VS BASELINE)")
                print("="*60)
                print(f"Average Top-10 Long Overlap Ratio: {avg_overlap * 100:.1f}%")
                print(f"Paired t-test for per-date DA:      t = {t_da:.4f}, p = {p_da:.4f}")
                print(f"Paired t-test for per-date RankIC:  t = {t_ic:.4f}, p = {p_ic:.4f}")
                print("="*60)
            else:
                print("[*] Too few overlapping dates to run comparative tests.")
                
    # Xuất metrics CSV tùy biến theo tên mô hình
    metrics_file_name = 'finetuned_metrics.csv' if 'finetuned' in output_dir else 'baseline_metrics.csv'
    metrics_csv_path = os.path.join(output_dir, metrics_file_name)
    metrics_df = pd.DataFrame([val_metrics, test_metrics], index=['Validation', 'Test']).T
    metrics_df.index.name = 'Metric'
    metrics_df.to_csv(metrics_csv_path)
    print(f"[*] Exported metrics report to: {metrics_csv_path}")
    
    # Plot Backtest Cumulative returns
    plt.figure(figsize=(14, 7))
    
    # Val Plot
    plt.subplot(1, 2, 1)
    dates_val = [datetime.strptime(d, '%Y-%m-%d') for d in val_hist['dates']]
    plt.plot(dates_val, val_hist['cum_returns_long'], label='Long (EW)', color='darkblue')
    plt.plot(dates_val, val_hist['cum_returns_long_mag'], label='Long (Mag-W)', color='teal', linestyle='-.')
    plt.plot(dates_val, val_hist['cum_returns_ls'], label='Long-Short (EW)', color='crimson')
    plt.plot(dates_val, val_hist['cum_returns_ls_mag'], label='Long-Short (Mag-W)', color='purple', linestyle='-.')
    plt.plot(dates_val, val_hist['cum_returns_bench'], label='Benchmark (VN50 EW)', color='gray', linestyle='--')
    plt.title('Validation Period (OOS 2023) Backtest')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Log Return')
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.xticks(rotation=30)
    
    # Test Plot
    plt.subplot(1, 2, 2)
    dates_test = [datetime.strptime(d, '%Y-%m-%d') for d in test_hist['dates']]
    plt.plot(dates_test, test_hist['cum_returns_long'], label='Long (EW)', color='darkblue')
    plt.plot(dates_test, test_hist['cum_returns_long_mag'], label='Long (Mag-W)', color='teal', linestyle='-.')
    plt.plot(dates_test, test_hist['cum_returns_ls'], label='Long-Short (EW)', color='crimson')
    plt.plot(dates_test, test_hist['cum_returns_ls_mag'], label='Long-Short (Mag-W)', color='purple', linestyle='-.')
    plt.plot(dates_test, test_hist['cum_returns_bench'], label='Benchmark (VN50 EW)', color='gray', linestyle='--')
    plt.title('Test Period (OOS 2024+) Backtest')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Log Return')
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.xticks(rotation=30)
    
    plt.tight_layout()
    plot_file_name = 'finetuned_backtest_performance.png' if 'finetuned' in output_dir else 'backtest_performance.png'
    plot_path = os.path.join(output_dir, plot_file_name)
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"[*] Exported backtest performance plot to: {plot_path}")


if __name__ == '__main__':
    main()
