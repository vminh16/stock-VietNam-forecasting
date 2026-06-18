import os
import sys
import random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

# Add parent directory to path to import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../finetune_csv')))

from model import Kronos, KronosTokenizer
from config_loader import CustomFinetuneConfig
from finetune_base_model import CustomKlineDataset
from training_utils import get_ddp_unwrapped_model

def generate_raw(tokenizer, model, x, x_stamp, y_stamp, pred_len, max_context, clip, T, top_k, top_p, sample_count, device):
    """
    Generate raw autoregressive predictions returning all individual stochastic samples,
    rather than averaging them internally. This allows mathematical analysis of individual signs (Majority Voting).
    """
    with torch.no_grad():
        # Convert numpy arrays to tensors on the correct device
        x = torch.from_numpy(np.array(x).astype(np.float32)).to(device)
        x_stamp = torch.from_numpy(np.array(x_stamp).astype(np.float32)).to(device)
        y_stamp = torch.from_numpy(np.array(y_stamp).astype(np.float32)).to(device)

        x = torch.clip(x, -clip, clip)
        # Repeat samples to generate parallel stochastic paths in the batch dimension
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
        preds = preds[:, :, -pred_len:, :]  # Extract predicted window only
        return preds

def predict_batch_raw(predictor, df_list, x_timestamp_list, y_timestamp_list, pred_len, sample_count=5, T=1.0, top_k=0, top_p=0.9):
    """
    Predict batch of time series and return raw un-averaged sample paths.
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

    # Call custom generate returning raw samples shape: (B, sample_count, pred_len, feat)
    preds = generate_raw(
        predictor.tokenizer, predictor.model, x_batch, x_stamp_batch, y_stamp_batch,
        pred_len, predictor.max_context, predictor.clip, T, top_k, top_p, sample_count, predictor.device
    )

    # Denormalize each series and its sample paths
    results = []
    for i in range(num_series):
        # preds[i] has shape (sample_count, pred_len, feat)
        preds_i = preds[i] * (stds[i] + 1e-5) + means[i]
        results.append(preds_i)
    return results

def evaluate_mathematical_paradigms(config_path, sample_count=5):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Running evaluation on device: {device} with sample_count={sample_count}")
    
    config = CustomFinetuneConfig(config_path)
    
    # Load tokenizer and model
    tokenizer = KronosTokenizer.from_pretrained(config.finetuned_tokenizer_path).to(device)
    
    # Load base model first, then wrap with LoRA adapter if enabled
    print(f"[*] Loading base model from {config.pretrained_predictor_path}")
    model = Kronos.from_pretrained(config.pretrained_predictor_path)
    if getattr(config, 'use_lora', False):
        from peft import PeftModel
        adapter_path = os.path.join(config.basemodel_save_path, "best_lora")
        print(f"[*] Wrapping base model with LoRA adapter from {adapter_path}")
        model = PeftModel.from_pretrained(model, adapter_path)
    model = model.to(device)
    
    model.eval()
    tokenizer.eval()
    
    from model.kronos import KronosPredictor
    predictor = KronosPredictor(model, tokenizer, device=device, max_context=config.max_context, clip=config.clip)
    
    # Load Validation Dataset
    train_end_date = config.loader.get('data.train_end_date', '2023-01-01')
    val_end_date = config.loader.get('data.val_end_date', '2024-01-01')
    
    val_dataset = CustomKlineDataset(
        data_path=config.data_path,
        data_type='val',
        lookback_window=config.lookback_window,
        predict_window=config.predict_window,
        clip=config.clip,
        seed=config.seed + 1,
        train_end_date=train_end_date,
        val_end_date=val_end_date
    )
    
    total_val_windows = len(val_dataset)
    if total_val_windows == 0:
        print("[!] No validation windows found.")
        return
        
    sample_indices = list(range(total_val_windows))
    if len(sample_indices) > 200:
        rng = random.Random(42)
        sample_indices = rng.sample(sample_indices, 200)
        
    df_list = []
    x_ts_list = []
    y_ts_list = []
    actual_changes = []
    
    for idx in sample_indices:
        symbol, start_idx = val_dataset.global_index_map[idx]
        df = val_dataset.stock_data[symbol]
        
        lookback_df = df.iloc[start_idx : start_idx + config.lookback_window].copy()
        future_df = df.iloc[start_idx + config.lookback_window : start_idx + config.lookback_window + config.predict_window].copy()
        
        if len(future_df) < config.predict_window:
            continue
            
        current_close = lookback_df.iloc[-1]['close']
        actual_close_5d = future_df.iloc[-1]['close']
        
        df_list.append(lookback_df)
        x_ts_list.append(lookback_df['timestamps'])
        y_ts_list.append(future_df['timestamps'])
        actual_changes.append(actual_close_5d - current_close)
        
    print(f"[*] Total evaluated windows: {len(df_list)}")
    
    # Run batch predictions to retrieve raw sample paths
    eval_batch_size = 16
    raw_preds_list = [] # List of shape (sample_count, pred_len, feat)
    for i in range(0, len(df_list), eval_batch_size):
        batch_dfs = df_list[i : i + eval_batch_size]
        batch_x_ts = x_ts_list[i : i + eval_batch_size]
        batch_y_ts = y_ts_list[i : i + eval_batch_size]
        
        batch_raw = predict_batch_raw(
            predictor, batch_dfs, batch_x_ts, batch_y_ts,
            pred_len=config.predict_window, sample_count=sample_count, T=1.0
        )
        raw_preds_list.extend(batch_raw)
        
    # --- MATH PARADIGMS EVALUATION ---
    correct_mean = 0
    correct_vote = 0
    total_individual_correct = 0
    total_samples_evaluated = 0
    
    for i, raw_pred in enumerate(raw_preds_list):
        current_close = df_list[i].iloc[-1]['close']
        actual_change = actual_changes[i]
        actual_sign = 1 if actual_change > 0 else -1
        
        # close index is 3 (open=0, high=1, low=2, close=3)
        # raw_pred shape: (sample_count, pred_len, feat)
        # Extractpredicted T+5 close price for all samples
        pred_close_5d_s = raw_pred[:, -1, 3] # shape: (sample_count,)
        predicted_changes_s = pred_close_5d_s - current_close # shape: (sample_count,)
        
        # 1. PARADIGM 1: Mean Price Prediction (Baseline)
        # We average paths first: E[Y] - Y_T, then calculate sign.
        # This is where Jensen's inequality plays a role as sign(E[X]) != E[sign(X)].
        mean_predicted_change = np.mean(predicted_changes_s)
        pred_sign_mean = 1 if mean_predicted_change > 0 else -1
        if pred_sign_mean == actual_sign:
            correct_mean += 1
            
        # 2. PARADIGM 2: Majority Voting
        # We calculate sign(x^(s)) for each sample, and vote.
        # This is robust against outlier paths.
        signs_s = np.where(predicted_changes_s > 0, 1, -1)
        vote_score = np.sum(signs_s)
        pred_sign_vote = 1 if vote_score > 0 else -1
        if pred_sign_vote == actual_sign:
            correct_vote += 1
            
        # 3. PARADIGM 3: Average of Individual DAs
        # E[DA] = Mean accuracy of individual paths.
        individual_corrects = np.sum(signs_s == actual_sign)
        total_individual_correct += individual_corrects
        total_samples_evaluated += sample_count
        
    total_eval = len(df_list)
    da_mean = (correct_mean / total_eval) * 100
    da_vote = (correct_vote / total_eval) * 100
    da_avg_indiv = (total_individual_correct / total_samples_evaluated) * 100
    
    print("\n" + "="*50)
    print(f"RESULTS FOR sample_count = {sample_count}")
    print("="*50)
    print(f"Method 1: Mean Price Prediction (Current Baseline): {da_mean:.2f}%")
    print(f"Method 2: Majority Voting (Proposed):               {da_vote:.2f}%")
    print(f"Method 3: Average of Individual DAs:                 {da_avg_indiv:.2f}%")
    print("="*50 + "\n")
    
    return da_mean, da_vote, da_avg_indiv

if __name__ == "__main__":
    config_path = "finetune_csv/configs/vn50.yaml"
    # Run evaluation with S=5 (standard validation size)
    evaluate_mathematical_paradigms(config_path, sample_count=5)
    # Run evaluation with S=20 (larger sample size to enhance Condorcet majority effect)
    evaluate_mathematical_paradigms(config_path, sample_count=20)
