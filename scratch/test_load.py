import os
import sys
import time
import pandas as pd
import numpy as np
import torch

proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(proj_root)

from model import Kronos, KronosTokenizer, KronosPredictor
from model.kronos import calc_time_stamps, sample_from_logits

# Setup paths
tokenizer_path = os.path.join(proj_root, "finetune_csv", "finetuned", "tokenizer_v2", "tokenizer", "best_model")
predictor_path = os.path.join(proj_root, "finetune_csv", "finetuned", "basemodel_v2", "basemodel", "best_model")

# Load models
tokenizer_model = KronosTokenizer.from_pretrained(tokenizer_path).to("cpu")
predictor_model = Kronos.from_pretrained(predictor_path).to("cpu")
predictor = KronosPredictor(predictor_model, tokenizer_model, device="cpu", max_context=512, clip=5.0)

def auto_regressive_inference_paths(tokenizer, model, x, x_stamp, y_stamp, max_context, pred_len, clip=5.0, T=1.0, top_k=0, top_p=0.90, sample_count=50):
    with torch.no_grad():
        x = torch.clip(x, -clip, clip)
        curr_device = x.device
        
        # Repeat input for multiple sample paths
        x = x.unsqueeze(1).repeat(1, sample_count, 1, 1).reshape(-1, x.size(1), x.size(2)).to(curr_device)
        x_stamp = x_stamp.unsqueeze(1).repeat(1, sample_count, 1, 1).reshape(-1, x_stamp.size(1), x_stamp.size(2)).to(curr_device)
        y_stamp = y_stamp.unsqueeze(1).repeat(1, sample_count, 1, 1).reshape(-1, y_stamp.size(1), y_stamp.size(2)).to(curr_device)

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
            sample_pre = sample_from_logits(s1_logits, temperature=T, top_k=top_k, top_p=top_p, sample_logits=True)

            s2_logits = model.decode_s2(context, sample_pre)
            s2_logits = s2_logits[:, -1, :]
            sample_post = sample_from_logits(s2_logits, temperature=T, top_k=top_k, top_p=top_p, sample_logits=True)

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
        return z.cpu().numpy()

# Load ACB.csv
csv_path = os.path.join(proj_root, "data", "ACB.csv")
df = pd.read_csv(csv_path)
df['timestamps'] = pd.to_datetime(df['timestamps'])
df = df.sort_values('timestamps').reset_index(drop=True)
df['amount'] = df['volume'] * (df['open'] + df['high'] + df['low'] + df['close']) / 4.0

lookback = 126
pred_len = 5

x_df = df.iloc[-(lookback + 7):-7]
actual_df = df.iloc[-7:-7+pred_len]
x_timestamps = x_df['timestamps']
y_timestamps = actual_df['timestamps']

price_cols = ['open', 'high', 'low', 'close']
features = price_cols + ['volume', 'amount']
x_raw = x_df[features].values.astype(np.float64)

start_time = time.time()
x_mean = np.mean(x_raw, axis=0)
x_std = np.std(x_raw, axis=0)
x_std = np.where(x_std < 1e-6, 1.0, x_std)

x_norm = (x_raw - x_mean) / (x_std + 1e-5)
x_norm = np.clip(x_norm, -predictor.clip, predictor.clip)

x_tensor = torch.from_numpy(x_norm[np.newaxis, ...].astype(np.float32)).to("cpu")
x_stamp_df = calc_time_stamps(pd.Series(x_timestamps))
y_stamp_df = calc_time_stamps(pd.Series(y_timestamps))

x_stamp_tensor = torch.from_numpy(x_stamp_df.values[np.newaxis, ...].astype(np.float32)).to("cpu")
y_stamp_tensor = torch.from_numpy(y_stamp_df.values[np.newaxis, ...].astype(np.float32)).to("cpu")

paths_norm = auto_regressive_inference_paths(
    tokenizer_model, predictor_model, x_tensor, x_stamp_tensor, y_stamp_tensor,
    max_context=predictor.max_context, pred_len=pred_len, clip=predictor.clip,
    T=1.0, top_p=0.9, sample_count=50
)
paths_norm = paths_norm.squeeze(0)
pred_paths_norm = paths_norm[:, -pred_len:, :]
pred_paths_raw = pred_paths_norm * (x_std + 1e-5) + x_mean
mean_pred_raw = np.mean(pred_paths_raw, axis=0)

print(f"Inference time: {time.time() - start_time:.4f} seconds")
print("Prediction shape:", mean_pred_raw.shape)
print("ACB actual close:", actual_df['close'].values)
print("ACB predicted close:", mean_pred_raw[:, 3])
